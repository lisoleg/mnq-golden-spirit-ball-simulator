"""
MNQ Web Dashboard - Flask 后端入口

启动 Flask REST API 服务器，注册所有 Blueprint 路由，
配置 CORS 和静态文件服务。
"""

import sys
import os
import logging

# 确保 mnq_windows 根目录在 sys.path 中
_base = os.path.join(os.path.dirname(__file__), '..')
if _base not in sys.path:
    sys.path.insert(0, _base)

from flask import Flask, jsonify
from flask_cors import CORS

from config import PORT, DEBUG, CORS_ORIGINS, FRONTEND_DIST

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    创建并配置 Flask 应用。

    Returns:
        Flask: 配置好的 Flask 应用实例
    """
    app = Flask(__name__, static_folder=None)

    # CORS 配置 (允许前端开发服务器跨域访问)
    CORS(app, origins=CORS_ORIGINS, supports_credentials=True)

    # 注册 API Blueprints
    from api.experiment import experiment_bp
    from api.kernel import kernel_bp
    from api.massface import massface_bp
    from api.scf import scf_bp
    from api.cgd import cgd_bp
    from api.mnq9 import mnq9_bp
    from api.deep import deep_bp
    from api.kappa import kappa_bp
    from api.mesh import mesh_bp
    from api.liu import liu_bp
    from api.cloud import cloud_bp

    app.register_blueprint(experiment_bp, url_prefix='/api/experiment')
    app.register_blueprint(kernel_bp, url_prefix='/api/kernel')
    app.register_blueprint(massface_bp, url_prefix='/api/massface')
    app.register_blueprint(scf_bp, url_prefix='/api/scf')
    app.register_blueprint(cgd_bp, url_prefix='/api/cgd')
    app.register_blueprint(mnq9_bp, url_prefix='/api/mnq9')
    app.register_blueprint(deep_bp, url_prefix='/api/deep')
    app.register_blueprint(kappa_bp, url_prefix='/api/kappa')
    app.register_blueprint(mesh_bp, url_prefix='/api/mesh')
    app.register_blueprint(liu_bp, url_prefix='/api/liu')
    app.register_blueprint(cloud_bp, url_prefix='/api/cloud')

    # 健康检查端点
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查端点。"""
        return jsonify({
            'status': 'ok',
            'service': 'MNQ Web Dashboard API',
            'version': '3.1',
        })

    # 生产环境：服务前端静态文件
    if os.path.exists(FRONTEND_DIST):
        from flask import send_from_directory

        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path: str):
            """服务 Vue/Vite 前端构建产物。"""
            if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
                return send_from_directory(FRONTEND_DIST, path)
            return send_from_directory(FRONTEND_DIST, 'index.html')

        logger.info(f"Serving frontend from: {FRONTEND_DIST}")

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app


# 应用实例
app = create_app()


def main():
    """启动 Flask 开发服务器。"""
    logger.info(f"Starting MNQ Web Dashboard API on port {PORT}...")
    logger.info(f"CORS origins: {CORS_ORIGINS}")
    logger.info(f"Health check: http://localhost:{PORT}/api/health")

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG,
        threaded=True,
    )


if __name__ == '__main__':
    main()
