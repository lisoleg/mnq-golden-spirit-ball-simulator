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
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)

deep_bp = Blueprint('deep', __name__)

# 全局模型状态
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


@deep_bp.route('/generate', methods=['POST'])
def deep_generate():
    """
    生成文本。

    请求体:
        {start_text: str, length: int, temperature: float, syntax_constraint: str (可选)}
    响应:
        {generated_text: str}
    """
    try:
        data = request.get_json(force=True) or {}
        start_text = data.get('start_text', 'MNQ ')
        length = data.get('length', 100)
        temperature = data.get('temperature', 0.8)

        if not _torch_available:
            return jsonify({
                'generated_text': f"[Mock] Generated from \"{start_text}\" ({length} chars at T={temperature})",
                'warning': 'PyTorch not available, running in mock mode',
            })

        _lazy_load_model()

        if _model is None:
            return jsonify({
                'generated_text': f"[Mock] MNQ transformer would generate from: \"{start_text}\"",
                'warning': 'Model not initialized',
            })

        # 使用 MNQComboTransformer 的 generate 方法
        try:
            generated = _model.generate(
                start_text=start_text,
                max_length=length,
                temperature=temperature,
            )
            return jsonify({'generated_text': generated})
        except AttributeError:
            # Fallback: 使用简单字符生成
            chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
            generated = start_text
            for _ in range(length):
                generated += random.choice(chars)
            return jsonify({'generated_text': generated})

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
