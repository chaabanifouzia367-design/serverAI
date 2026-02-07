from flask import Flask
from flask_cors import CORS
import logging
import os
from app.config import Config
from supabase import create_client

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=["*"])

    # Configure logging only if not already configured (prevent duplicate handlers)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler('medical_processor.log'),
                logging.StreamHandler()
            ]
        )

    # Ensure directories exist
    for directory in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER']]:
        os.makedirs(directory, exist_ok=True)
    for view in ['axial', 'coronal', 'sagittal']:
        os.makedirs(os.path.join(app.config['BASE_PATH'], view), exist_ok=True)

    # Supabase client
    try:
        app.extensions = getattr(app, 'extensions', {})
        app.extensions['supabase'] = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])
        print('')
    except Exception:
        app.extensions['supabase'] = None

    # Register blueprints
    from app.api.upload import upload_bp
    from app.api.status import status_bp
    from app.api.health import health_bp
    from app.api.models import models_bp

    app.register_blueprint(upload_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(models_bp)
    logger.info("✅ Blueprints registered successfully")

    # Error handlers
    @app.errorhandler(413)
    def file_too_large(e):
        from flask import jsonify
        return jsonify({
            'error': 'File too large',
            'max_size_mb': app.config['MAX_FILE_SIZE'] / (1024*1024)
        }), 413

    @app.errorhandler(500)
    def internal_error(e):
        from flask import jsonify
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({'error': 'Endpoint not found'}), 404

    return app


