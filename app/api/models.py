from flask import Blueprint, request, jsonify
from app.services.model_manager import ModelManager
import logging

models_bp = Blueprint('models', __name__)
logger = logging.getLogger(__name__)

@models_bp.route('/api/models', methods=['POST'])
def register_model():
    """Register a new AI model (supports JSON or multipart/form-data with file upload)."""
    try:
        # Determine data source (JSON or Form)
        if request.is_json:
            data = request.json
        else:
            data = request.form

        name = data.get('name')
        model_type = data.get('type', 'pano_detection') # Default to pano_detection
        threshold = data.get('threshold', 0.5)
        path = data.get('path')
        
        # Handle File Upload
        file = request.files.get('file')
        if file and file.filename:
            from werkzeug.utils import secure_filename
            import os
            
            filename = secure_filename(file.filename)
            filename = secure_filename(file.filename)
            
            # [NEW] Organize by type
            if 'cbct' in model_type:
                save_dir = "models/cbct"
            else:
                save_dir = "models/pano"
            
            # Ensure safe directory existence
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # Save file
            file_path = os.path.join(save_dir, filename)
            file.save(file_path)
            
            # Use the saved relative path
            path = file_path.replace("\\", "/")
            logger.info(f"📁 Uploaded model file saved to: {path}")

        if not name or not path:
            return jsonify({'error': 'Name and path (or file) required'}), 400
            
        model = ModelManager.register_model(name, path, model_type, threshold)
        return jsonify(model), 201
    except Exception as e:
        logger.error(f"Error registering model: {e}")
        return jsonify({'error': str(e)}), 500

@models_bp.route('/api/models', methods=['GET'])
def list_models():
    """List all registered models."""
    try:
        models = ModelManager.get_all_models()
        active_models = ModelManager.get_active_model()
        return jsonify({
            'models': models,
            'active_models': active_models
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@models_bp.route('/api/models/active', methods=['POST'])
def set_active_model():
    """Set the active model to use."""
    try:
        data = request.json
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'error': 'model_id required'}), 400
            
        ModelManager.set_active_model(model_id)
        return jsonify({'status': 'success', 'active_model_id': model_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@models_bp.route('/api/models/deactivate', methods=['POST'])
def deactivate_model():
    """Deactivate (unset) the active model for a specific type."""
    try:
        data = request.json
        model_type = data.get('type')
        
        if not model_type:
            return jsonify({'error': 'type required'}), 400
            
        ModelManager.deactivate_model_type(model_type)
        return jsonify({'status': 'success', 'message': f'Model type {model_type} deactivated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@models_bp.route('/api/models/<model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete a model."""
    try:
        success = ModelManager.delete_model(model_id)
        if success:
            return jsonify({'status': 'success', 'message': f'Model {model_id} deleted'}), 200
        else:
            return jsonify({'error': 'Model not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
