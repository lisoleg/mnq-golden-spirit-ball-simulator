"""
实验管理 API

路由:
- GET  /api/experiment/list           获取所有可用实验
- POST /api/experiment/run            运行实验
- GET  /api/experiment/status/<id>    查询任务状态
- GET  /api/experiment/progress/<id>  SSE 进度流
- GET  /api/experiment/history        获取历史列表
- GET  /api/experiment/history/<id>   获取历史详情
- DELETE /api/experiment/history/<id> 删除历史
"""

import json
from flask import Blueprint, jsonify, request, Response
from services.experiment_runner import (
    get_experiment_list, run_experiment, get_task_status,
)
from services.sse_manager import generate_sse_stream
from models.experiment_history import (
    get_history_list, get_history_entry, delete_history_entry, add_history_entry,
)

experiment_bp = Blueprint('experiment', __name__)


@experiment_bp.route('/list', methods=['GET'])
def list_experiments():
    """获取所有可用实验的列表。"""
    try:
        experiments = get_experiment_list()
        return jsonify({'experiments': experiments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/run', methods=['POST'])
def run_experiment_endpoint():
    """
    运行指定实验。

    请求体: {experiment_id: str, params: dict (可选)}
    响应: {task_id: str, status: str, message: str}
    """
    try:
        data = request.get_json(force=True)
        if not data or 'experiment_id' not in data:
            return jsonify({'error': 'Missing experiment_id'}), 400

        experiment_id = data['experiment_id']
        params = data.get('params', {})

        result = run_experiment(experiment_id, params)

        # 如果有 error 字段，返回 400
        if 'error' in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/status/<task_id>', methods=['GET'])
def experiment_status(task_id: str):
    """
    查询实验任务状态。

    响应: {task_id, experiment_id, status, progress, result, log}
    """
    try:
        status = get_task_status(task_id)
        if status is None:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/progress/<task_id>', methods=['GET'])
def experiment_progress(task_id: str):
    """
    SSE 流式进度推送。

    Content-Type: text/event-stream
    流事件格式: data: {progress, log, status, result}
    """
    try:
        return Response(
            generate_sse_stream(task_id),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            },
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/history', methods=['GET'])
def history_list():
    """
    获取实验历史列表。

    响应: {history: [{id, experiment_id, timestamp, status}, ...]}
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = get_history_list(limit=limit)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/history/<entry_id>', methods=['GET'])
def history_detail(entry_id: str):
    """
    获取指定历史记录详情。

    响应: {id, experiment_id, params, result, timestamp}
    """
    try:
        entry = get_history_entry(entry_id)
        if entry is None:
            return jsonify({'error': 'History entry not found'}), 404
        return jsonify(entry)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@experiment_bp.route('/history/<entry_id>', methods=['DELETE'])
def history_delete(entry_id: str):
    """
    删除指定历史记录。

    响应: {success: bool}
    """
    try:
        success = delete_history_entry(entry_id)
        if not success:
            return jsonify({'error': 'History entry not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
