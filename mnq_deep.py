"""
MNQ-Deep Transformer — MNQ-Combo + 跨层Ω传递 + 语法约束解码
集成自 mnq_next.py / mnq_combo.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import random
import json


DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'


# ============================================
# 数据集
# ============================================

class CharDataset:
    def __init__(self, text, seq_len):
        self.chars = sorted(list(set(text)))
        self.char2idx = {ch: i for i, ch in enumerate(self.chars)}
        self.idx2char = {i: ch for i, ch in enumerate(self.chars)}
        self.vocab_size = len(self.chars)
        self.seq_len = seq_len
        self.data = text

    def get_batch(self, batch_size):
        starts = [random.randint(0, len(self.data) - self.seq_len - 1) for _ in range(batch_size)]
        x = torch.tensor([[self.char2idx[self.data[i+j]] for j in range(self.seq_len)] for i in starts])
        y = torch.tensor([[self.char2idx[self.data[i+j+1]] for j in range(self.seq_len)] for i in starts])
        return x, y


# ============================================
# 训练函数
# ============================================

def train(model, dataset, epochs, batch_size, lr, device):
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()
    losses = []
    for epoch in range(epochs):
        model.train()
        x, y = dataset.get_batch(batch_size)
        x, y = x.to(device), y.to(device)
        logits = model(x)
        loss = criterion(logits.reshape(-1, dataset.vocab_size), y.reshape(-1))
        if torch.isnan(loss):
            return losses + [float('nan')]
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        losses.append(loss.item())
        if epoch % 100 == 0:
            print(f"  Epoch {epoch}: {loss:.4f}")
    return losses


# ============================================
# 生成函数 (含语法约束解码)
# ============================================

@torch.no_grad()
def generate(model, dataset, start_text, length=120, temperature=0.8, syntax_constraint=False):
    """
    syntax_constraint=True: 在生成时施加简单的语法约束
    - 禁止连续两个换行
    - 括号匹配（尽量）
    - 缩进一致性（如果上一个字符是换行，下一个大概率是空格）
    """
    model.eval()
    device = next(model.parameters()).device
    idxs = [dataset.char2idx[c] for c in start_text if c in dataset.char2idx]
    x = torch.tensor([idxs], device=device)

    for _ in range(length):
        x_crop = x[:, -dataset.seq_len:]
        logits = model(x_crop)[:, -1, :]
        logits = torch.clamp(logits, min=-50, max=50) / temperature
        probs = F.softmax(logits, dim=-1)
        probs = torch.clamp(probs, min=1e-8)
        probs = probs / probs.sum()

        if syntax_constraint and len(idxs) > 0:
            last_char = dataset.idx2char[idxs[-1]]
            # 禁止连续换行
            if last_char == '\n':
                newline_idx = dataset.char2idx.get('\n', -1)
                if newline_idx >= 0:
                    probs[0, newline_idx] *= 0.1
                # 增加缩进概率
                space_idx = dataset.char2idx.get(' ', -1)
                if space_idx >= 0:
                    probs[0, space_idx] *= 2.0
                # 增加def/class概率（函数定义）
                for c in 'def class':
                    ci = dataset.char2idx.get(c, -1)
                    if ci >= 0:
                        probs[0, ci] *= 1.5
            # 括号匹配：如果上一个字符是'('，下一个大概率不是')'
            if last_char == '(':
                close_idx = dataset.char2idx.get(')', -1)
                if close_idx >= 0:
                    probs[0, close_idx] *= 0.3
            # 如果上一个字符是':'，下一个大概率是换行
            if last_char == ':':
                newline_idx = dataset.char2idx.get('\n', -1)
                if newline_idx >= 0:
                    probs[0, newline_idx] *= 3.0

            probs = probs / probs.sum()

        next_idx = torch.multinomial(probs, 1).item()
        idxs.append(next_idx)
        x = torch.tensor([idxs], device=device)
    return ''.join([dataset.idx2char[i] for i in idxs])


# ============================================
# MNQ-Combo: 三驱动力 + 层间衰减 + Ω-φ动力学
# ============================================

class MNQComboAttention(nn.Module):
    """
    三驱动力注意力：
    - 保护头(1/4): 局部模式，只关注近邻（短程相干）
    - 服务头(1/2): 全局依赖（长程连接）
    - 稳定头(1/4): 平滑输出，抑制极端（阻尼）
    """
    def __init__(self, d_model, n_heads, dropout=0.1):
        super().__init__()
        assert n_heads >= 4
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # 三驱动力能量（可学习）
        self.protect_energy = nn.Parameter(torch.tensor(0.5))
        self.serve_energy = nn.Parameter(torch.tensor(0.5))
        self.stable_energy = nn.Parameter(torch.tensor(0.5))

        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        B, T, D = x.shape
        q = self.q_proj(x).reshape(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).reshape(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).reshape(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        if mask is not None:
            scores = scores + mask.unsqueeze(0).unsqueeze(0)

        # 分三组
        n_prot = max(1, self.n_heads // 4)
        n_serv = max(2, self.n_heads // 2)

        # 保护头：局部mask
        local_mask = torch.full((1, 1, T, T), float('-inf'), device=x.device)
        for i in range(T):
            start = max(0, i - 5)
            local_mask[..., i, start:i+1] = 0
        prot_scores = scores[:, :n_prot, :, :] + local_mask

        # 稳定头：温度软化
        serv_scores = scores[:, n_prot:n_prot+n_serv, :, :]
        stab_scores = scores[:, n_prot+n_serv:, :, :] / 2.0

        scores = torch.cat([prot_scores, serv_scores, stab_scores], dim=1)

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)

        # 三驱动力能量加权
        energies = torch.sigmoid(torch.stack([self.protect_energy, self.serve_energy, self.stable_energy]))
        energy_w = F.softmax(energies, dim=0)

        out_prot = out[:, :n_prot] * energy_w[0]
        out_serv = out[:, n_prot:n_prot+n_serv] * energy_w[1]
        out_stab = out[:, n_prot+n_serv:] * energy_w[2]
        out = torch.cat([out_prot, out_serv, out_stab], dim=1)

        out = out.transpose(1, 2).reshape(B, T, D)
        return self.out_proj(out)


class MNQComboLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1, layer_idx=0, n_layers=4):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = MNQComboAttention(d_model, n_heads, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_ff, d_model), nn.Dropout(dropout)
        )

        # 层间衰减残差（物极必反）
        init_w = 1.0 - 0.15 * layer_idx / max(1, n_layers - 1)
        self.residual_weight = nn.Parameter(torch.tensor(init_w))

        # Ω-φ: 层内状态累积
        self.omega_accum = nn.Parameter(torch.zeros(d_model))
        self.gamma_gate = nn.Linear(d_model, 1)

    def forward(self, x, mask=None):
        B, T, D = x.shape

        # 注意力
        attn_out = self.attn(self.ln1(x), mask)

        # Ω-φ动力学
        local_state = x.mean(dim=1)  # [B, D]
        gamma = torch.sigmoid(self.gamma_gate(local_state)).view(B, 1, 1)  # [B, 1, 1]
        omega = torch.tanh(self.omega_accum).view(1, 1, D)

        # 混合: gamma * 新信息 + (1-gamma) * Ω累积
        mixed = gamma * attn_out + (1 - gamma) * omega

        # 残差连接（带衰减）
        w = torch.sigmoid(self.residual_weight)
        x = w * x + mixed

        # FFN
        x = w * x + self.ffn(self.ln2(x))

        return x


class MNQComboTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, n_layers, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_enc = nn.Parameter(torch.randn(1, 1024, d_model) * 0.02)
        self.layers = nn.ModuleList([
            MNQComboLayer(d_model, n_heads, d_ff, dropout, i, n_layers)
            for i in range(n_layers)
        ])
        self.ln_final = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)
        self.d_model = d_model

    def forward(self, x):
        B, T = x.shape
        x = self.embedding(x) * math.sqrt(self.d_model)
        x = x + self.pos_enc[:, :T, :]
        mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
        mask = mask.float().masked_fill(mask, float('-inf'))
        for layer in self.layers:
            x = layer(x, mask)
        return self.head(self.ln_final(x))


# ============================================
# MNQ-Deep: 跨层Ω传递
# ============================================

class MNQCrossLayer(nn.Module):
    """
    MNQ-Combo + 跨层Ω传递
    每层接收上一层的omega_out，而不是独立的omega_accum
    """
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1, layer_idx=0, n_layers=6):
        super().__init__()
        self.d_model = d_model
        self.layer_idx = layer_idx
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = MNQComboAttention(d_model, n_heads, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_ff, d_model), nn.Dropout(dropout)
        )
        init_w = 1.0 - 0.15 * layer_idx / max(1, n_layers - 1)
        self.residual_weight = nn.Parameter(torch.tensor(init_w))
        self.omega_transform = nn.Linear(d_model, d_model)  # 跨层omega转换
        self.gamma_gate = nn.Linear(d_model * 2, 1)  # 接收当前x和跨层omega
        self.omega_scale = nn.Parameter(torch.tensor(0.1))

    def forward(self, x, omega_in, mask=None):
        B, T, D = x.shape
        attn_out = self.attn(self.ln1(x), mask)

        # 跨层Ω-φ动力学
        local_state = x.mean(dim=1)  # [B, D]
        if omega_in.dim() == 1:
            omega_in = omega_in.unsqueeze(0).expand(B, -1)
        combined = torch.cat([local_state, omega_in], dim=-1)  # [B, 2D]
        gamma = torch.sigmoid(self.gamma_gate(combined)).view(B, 1, 1)

        omega = torch.tanh(self.omega_transform(omega_in)).view(B, 1, D)
        phi = attn_out  # 新信息作为φ

        # Ω-φ混合: gamma * φ + (1-gamma) * Ω
        mixed = gamma * phi + (1 - gamma) * omega

        # 残差
        w = torch.sigmoid(self.residual_weight)
        x = w * x + mixed
        x = w * x + self.ffn(self.ln2(x))

        # 更新omega供下一层使用
        omega_update = self.omega_scale * phi.mean(dim=1)  # [B, D]
        omega_out = omega_in + omega_update
        omega_out = torch.tanh(omega_out)

        return x, omega_out


class MNQCrossTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, n_layers, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_enc = nn.Parameter(torch.randn(1, 1024, d_model) * 0.02)
        self.layers = nn.ModuleList([
            MNQCrossLayer(d_model, n_heads, d_ff, dropout, i, n_layers)
            for i in range(n_layers)
        ])
        self.ln_final = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)
        self.d_model = d_model
        self.global_omega = nn.Parameter(torch.zeros(d_model))

    def forward(self, x):
        B, T = x.shape
        x = self.embedding(x) * math.sqrt(self.d_model)
        x = x + self.pos_enc[:, :T, :]
        mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
        mask = mask.float().masked_fill(mask, float('-inf'))

        omega = self.global_omega.unsqueeze(0).expand(B, -1)  # [B, D]
        for layer in self.layers:
            x, omega = layer(x, omega, mask)
        return self.head(self.ln_final(x))


# ============================================
# 标准Transformer（作为基线对比）
# ============================================

class StandardLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(d_ff, d_model), nn.Dropout(dropout)
        )
    def forward(self, x, mask=None):
        attn_out, _ = self.attn(self.ln1(x), self.ln1(x), self.ln1(x), attn_mask=mask)
        x = x + attn_out
        x = x + self.ffn(self.ln2(x))
        return x


class StandardTransformer(nn.Module):
    def __init__(self, vocab_size, d_model, n_layers, n_heads, d_ff, dropout=0.1):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_enc = nn.Parameter(torch.randn(1, 1024, d_model) * 0.02)
        self.layers = nn.ModuleList([StandardLayer(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        self.ln_final = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)
        self.d_model = d_model
    def forward(self, x):
        B, T = x.shape
        x = self.embedding(x) * math.sqrt(self.d_model)
        x = x + self.pos_enc[:, :T, :]
        mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
        mask = mask.float().masked_fill(mask, float('-inf'))
        for layer in self.layers:
            x = layer(x, mask)
        return self.head(self.ln_final(x))


# ============================================
# 主实验入口
# ============================================

if __name__ == "__main__":
    torch.manual_seed(42)
    random.seed(42)

    code_text = """def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
    dataset = CharDataset(code_text, seq_len=64)
    print(f"代码数据集: 词汇={dataset.vocab_size}, 长度={len(code_text)}")

    config = {'d_model': 128, 'n_layers': 4, 'n_heads': 8, 'd_ff': 512, 'batch_size': 32, 'lr': 1e-3, 'epochs': 500, 'dropout': 0.1}

    results = {}

    # 标准Transformer
    print(f"\n{'='*60}\n标准Transformer\n{'='*60}")
    model = StandardTransformer(dataset.vocab_size, **{k: config[k] for k in ['d_model', 'n_layers', 'n_heads', 'd_ff', 'dropout']})
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")
    losses = train(model, dataset, config['epochs'], config['batch_size'], config['lr'], DEVICE)
    gen = generate(model, dataset, 'def ', length=150, temperature=0.8)
    results['standard'] = {'final_loss': losses[-1], 'gen': gen}
    print(f"Final Loss: {losses[-1]:.4f}")
    print(f"生成:\n{gen[:200]}")

    # MNQ-Combo
    print(f"\n{'='*60}\nMNQ-Combo (三驱动力 + 层间衰减 + Ω-φ)\n{'='*60}")
    model = MNQComboTransformer(dataset.vocab_size, **{k: config[k] for k in ['d_model', 'n_layers', 'n_heads', 'd_ff', 'dropout']})
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")
    losses = train(model, dataset, config['epochs'], config['batch_size'], config['lr'], DEVICE)
    gen = generate(model, dataset, 'def ', length=150, temperature=0.8)
    results['mnq_combo'] = {'final_loss': losses[-1], 'gen': gen}
    print(f"Final Loss: {losses[-1]:.4f}")
    print(f"生成:\n{gen[:200]}")

    # 保存
    with open('./mnq_deep_results.json', 'w') as f:
        json.dump({k: {'final_loss': v['final_loss'], 'gen': v['gen']} for k, v in results.items()}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}\n汇总")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"{name}: Loss={r['final_loss']:.4f}")
    print(f"\n结果已保存到 mnq_deep_results.json")
