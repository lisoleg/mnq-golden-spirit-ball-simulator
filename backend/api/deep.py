"""
MNQ-Deep Transformer API

路由:
- POST /api/deep/generate 生成文本
- POST /api/deep/train    训练模型
- GET  /api/deep/status   获取模型状态
"""

import sys
import os
import logging
import random
import re
import hashlib
import math as _math
import time
import requests
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)

deep_bp = Blueprint('deep', __name__)

# --- DeepSeek API 配置 ---
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 全局模型状态（保留给 /train 等本地训练用）
_model = None
_dataset = None
_model_loaded = False

try:
    import torch
    from mnq_deep import MNQComboTransformer, CharDataset, train, DEVICE
    _torch_available = True
except ImportError:
    _torch_available = False
    DEVICE = 'cpu'
    logger.warning("PyTorch not available. MNQ-Deep API will operate in mock mode.")


def _lazy_load_model():
    """懒加载 MNQ-Deep 模型。"""
    global _model, _dataset, _model_loaded
    if _model_loaded:
        return

    if not _torch_available:
        return

    try:
        from mnq_deep import MNQComboTransformer, CharDataset, DEVICE
        # 创建基础模型实例
        _model = MNQComboTransformer(
            vocab_size=128,
            d_model=64,
            n_heads=4,
            n_layers=2,
            block_size=32,
        )
        _model.eval()
        _model_loaded = True
        logger.info(f"MNQ-Deep model loaded on {DEVICE}")
    except Exception as e:
        logger.error(f"Failed to load MNQ-Deep model: {e}")
        _model_loaded = False


@deep_bp.route('/status', methods=['GET'])
def deep_status():
    """获取模型状态。"""
    try:
        _lazy_load_model()
        return jsonify({
            'device': DEVICE,
            'model_loaded': _model_loaded,
            'torch_available': _torch_available,
            'vocab_size': getattr(_model, 'vocab_size', 128) if _model else 0,
        })
    except Exception as e:
        logger.error(f"deep/status error: {e}")
        return jsonify({'error': str(e)}), 500


_LEFT_PAIRS = {'(', '[', '{', '\u201c', '\u2018'}  # " '
_RIGHT_PAIRS = {')', ']', '}', '\u201d', '\u2019'}  # " '
_PAIR_MAP = {'(': ')', '[': ']', '{': '}', '\u201c': '\u201d', '\u2018': '\u2019'}


def _check_syntax(text):
    """简单的语法有效性检查。中英文混合，检查是否有成对符号和合理结构。"""
    if not text or len(text) < 4:
        return False
    stack = []
    for ch in text:
        if ch in _LEFT_PAIRS:
            stack.append(ch)
        elif ch in _RIGHT_PAIRS:
            if stack and _PAIR_MAP.get(stack[-1]) == ch:
                stack.pop()
    brackets_ok = len(stack) == 0
    # 至少包含可读字符
    readable = sum(1 for c in text if c.isalnum() or c in '.!?;:,。！？；：、') > len(text) * 0.3
    return brackets_ok and readable


def _calc_entropy(text):
    """计算文本的字符级香农熵。"""
    if not text:
        return 0.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(text)
    entropy = 0.0
    for count in freq.values():
        p = count / n
        if p > 0:
            entropy -= p * _math.log2(p)
    return round(entropy, 6)


def _kappa_signature(text):
    """生成 κ 签名字符串 — 基于 MNQ 理论的信息指纹。"""
    if not text:
        return 'UNDEFINED'
    h = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    return f'MNQ-{h}'


@deep_bp.route('/generate', methods=['POST'])
def deep_generate():
    """
    生成文本 — 通过 DeepSeek API。

    请求体:
        {start_text: str, length: int, temperature: float}
    响应:
        {text: str, syntax_valid: bool, entropy: float, kappa_signature: str}
    """
    try:
        data = request.get_json(force=True) or {}
        start_text = data.get('start_text', '你好，请用中文介绍你自己。')
        length = data.get('length', 200)
        temperature = data.get('temperature', 0.8)

        # 构建 MNQ 理论上下文的 system prompt
        system_prompt = (
            "你是基于 MNQ（金灵球网络）理论的 AI 助手。"
            "MNQ 框架融合了金符学、阴龙积、八卦算子、冻结核（Frozen Kernel）、"
            "三层信息波（SCF）、D4 协变观测者、刘机制调度器等概念。"
            "请用中文回答用户问题，风格学术但不晦涩，适当提及 MNQ 理论相关概念。"
        )

        # 调用 DeepSeek API
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': DEEPSEEK_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': start_text},
            ],
            'temperature': temperature,
            'max_tokens': min(length, 4096),
        }

        logger.info(f"Calling DeepSeek API: model={DEEPSEEK_MODEL}, "
                    f"start_text={start_text[:50]}..., length={length}, T={temperature}")

        t0 = time.time()
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=120)
        elapsed = time.time() - t0

        if resp.status_code != 200:
            error_detail = resp.text[:300]
            logger.error(f"DeepSeek API error {resp.status_code}: {error_detail}")
            return jsonify({
                'error': f'DeepSeek API 返回错误 ({resp.status_code})',
                'detail': error_detail,
            }), 502

        result = resp.json()
        generated = result['choices'][0]['message']['content']

        # 首字大写下标去掉
        usage = result.get('usage', {})
        logger.info(f"DeepSeek API OK: {len(generated)} chars, "
                    f"{usage.get('total_tokens', '?')} tokens, {elapsed:.2f}s")

        # MNQ 后处理
        syntax_valid = _check_syntax(generated)
        entropy = _calc_entropy(generated)
        kappa_sig = _kappa_signature(generated)

        return jsonify({
            'text': generated,
            'syntax_valid': syntax_valid,
            'entropy': entropy,
            'kappa_signature': kappa_sig,
        })

    except requests.exceptions.Timeout:
        logger.error("DeepSeek API timeout")
        return jsonify({'error': 'DeepSeek API 请求超时，请稍后重试'}), 504
    except requests.exceptions.ConnectionError as e:
        logger.error(f"DeepSeek API connection error: {e}")
        return jsonify({'error': '无法连接 DeepSeek API，请检查网络'}), 502
    except Exception as e:
        logger.error(f"deep/generate error: {e}")
        return jsonify({'error': str(e)}), 500


@deep_bp.route('/train', methods=['POST'])
def deep_train():
    """
    训练模型。

    请求体:
        {dataset_text: str, epochs: int, batch_size: int, lr: float}
    响应:
        {losses: list}
    """
    try:
        data = request.get_json(force=True) or {}
        dataset_text = data.get('dataset_text', '')
        epochs = data.get('epochs', 10)
        batch_size = data.get('batch_size', 16)
        lr = data.get('lr', 0.001)

        if not _torch_available:
            return jsonify({
                'losses': [],
                'warning': 'PyTorch not available, cannot train',
            })

        _lazy_load_model()

        if _model is None or not dataset_text:
            return jsonify({
                'losses': [],
                'warning': 'Model not initialized or empty dataset',
            })

        try:
            from mnq_deep import CharDataset, train
            dataset = CharDataset(dataset_text, seq_len=32)
            losses = train(_model, dataset, epochs=epochs,
                          batch_size=batch_size, lr=lr, device=DEVICE)
            return jsonify({'losses': losses})
        except Exception as e:
            logger.error(f"Training failed: {e}")
            # 返回模拟结果
            return jsonify({
                'losses': [1.0 - 0.1 * i for i in range(epochs)],
                'warning': f'Training simulated (error: {e})',
            })

    except Exception as e:
        logger.error(f"deep/train error: {e}")
        return jsonify({'error': str(e)}), 500
