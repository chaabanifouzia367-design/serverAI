import json
import logging
from app.celery_app import redis_client
import uuid

logger = logging.getLogger(__name__)

class ModelManager:
    """Manage AI models using Redis."""
    
    MODELS_KEY = "ai_models_registry"
    ACTIVE_MODELS_HASH = "active_ai_models"  # Stores { type: model_id }

    VALID_TYPES = {
        'pano_segmentation',
        'pano_detection',
        'cbct_segmentation',
        'cbct_detection'
    }

    @classmethod
    def register_model(cls, name, path, model_type='pano_detection', threshold=0.5):
        """Register a new AI model."""
        if not redis_client:
            logger.error("Redis not available")
            return None
        
        if model_type not in cls.VALID_TYPES:
            # Fallback for backward compatibility or default assignment usually not needed if robust
            # But let's enforce types for clarity now
            # Actually, to make migration smoother, let's map 'detection' -> 'pano_detection'
            if model_type == 'detection':
                model_type = 'pano_detection'
            elif model_type not in cls.VALID_TYPES:
                raise ValueError(f"Invalid model_type. Must be one of: {cls.VALID_TYPES}")
            
        model_id = str(uuid.uuid4())
        model_data = {
            'id': model_id,
            'name': name,
            'path': path,
            'type': model_type,
            'threshold': float(threshold),
            'created_at': str(uuid.uuid1().time)
        }
        
        try:
            # Store in hash map
            redis_client.hset(cls.MODELS_KEY, model_id, json.dumps(model_data))
            logger.info(f"Registered model: {name} ({model_id}) - Type: {model_type}")
            return model_data
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            raise e

    @classmethod
    def get_local_default_models(cls):
        """Get default models from local config files."""
        try:
            from app.domains.pano.config import MULTIPROBLEM_DETECTION_CONFIG, SEGMENTATION_CONFIG
            from app.domains.cbct.config import CBCT_DETECTION_CONFIG, CBCT_SEGMENTATION_CONFIG
            
            local_models = []
            
            # Helper to format
            def fmt(cfg, m_type, default_name):
                return {
                    'id': f"local_{cfg.get('name', default_name)}",
                    'name': cfg.get('name', default_name),
                    'path': cfg.get('path'),
                    'type': m_type,
                    'threshold': cfg.get('threshold', 0.5),
                    'source': 'local_default'
                }

            # 1. Pano
            for cfg in MULTIPROBLEM_DETECTION_CONFIG:
                local_models.append(fmt(cfg, 'pano_detection', 'default_pano_det'))
            
            if SEGMENTATION_CONFIG:
                local_models.append(fmt(SEGMENTATION_CONFIG, 'pano_segmentation', 'default_pano_seg'))
                
            # 2. CBCT
            for cfg in CBCT_DETECTION_CONFIG:
                local_models.append(fmt(cfg, 'cbct_detection', 'default_cbct_det'))
                
            if CBCT_SEGMENTATION_CONFIG:
                local_models.append(fmt(CBCT_SEGMENTATION_CONFIG, 'cbct_segmentation', 'default_cbct_seg'))
                
            return local_models
        except Exception as e:
            logger.error(f"Error loading local default models: {e}")
            return []

    @classmethod
    def get_all_models(cls):
        """Get all registered models (Redis + Local Fallback)."""
        models = []
        
        # 1. Try Redis
        if redis_client:
            try:
                models_raw = redis_client.hgetall(cls.MODELS_KEY)
                for mid, data in models_raw.items():
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    m = json.loads(data)
                    m['source'] = 'redis'
                    models.append(m)
            except Exception as e:
                logger.error(f"Error listing models from Redis: {e}")
        
        # 2. If no Redis models (or Redis down), use Local Defaults
        if not models:
            logger.info("No models in Redis (or Redis unavail), using Local Defaults.")
            models = cls.get_local_default_models()
            
        return models

    @classmethod
    def set_active_model(cls, model_id):
        """Set the active model ID."""
        if not redis_client:
            return False
            
        try:
            # Verify model exists
            model_json = redis_client.hget(cls.MODELS_KEY, model_id)
            if not model_json:
                raise ValueError(f"Model {model_id} not found")
            
            if isinstance(model_json, bytes):
                model_json = model_json.decode('utf-8')
            
            model = json.loads(model_json)
            model_type = model.get('type')
            
            if not model_type or model_type not in cls.VALID_TYPES:
                 # Legacy fix if needed
                 model_type = 'pano_detection'

            # Set in HASH under correct type
            redis_client.hset(cls.ACTIVE_MODELS_HASH, model_type, model_id)
            logger.info(f"Active model set for [{model_type}]: {model_id} ({model['name']})")
            return True
        except Exception as e:
            logger.error(f"Error setting active model: {e}")
            raise e

    @classmethod
    def get_active_model(cls, model_type=None):
        """
        Get the currently active model configuration.
        """
        active_models = {}
        
        # 1. Try Redis for active selections
        if redis_client:
            try:
                all_active = redis_client.hgetall(cls.ACTIVE_MODELS_HASH)
                for m_type, m_id in all_active.items():
                    if isinstance(m_type, bytes): m_type = m_type.decode('utf-8')
                    if isinstance(m_id, bytes): m_id = m_id.decode('utf-8')
                    
                    # Fetch model data
                    m_data = cls._get_model_by_id(m_id)
                    if m_data:
                        m_data['source'] = 'redis'
                        active_models[m_type] = m_data
            except Exception as e:
                logger.error(f"Error fetching active models from Redis: {e}")
        
        # 2. If specific type requested
        if model_type:
            # Check if we have it from Redis
            if model_type in active_models:
                return active_models[model_type]
            
            # Fallback: Find first local model of this type
            local_defaults = cls.get_local_default_models()
            for m in local_defaults:
                if m['type'] == model_type:
                    return m
            return None
            
        # 3. If no specific type, return all (Layout: merge Redis with missing defaults)
        # Populate missing types from local defaults
        local_defaults = cls.get_local_default_models()
        for m in local_defaults:
            if m['type'] not in active_models:
                active_models[m['type']] = m
                
        return active_models

    @classmethod
    def _get_model_by_id(cls, model_id):
        raw = redis_client.hget(cls.MODELS_KEY, model_id)
        if raw:
            if isinstance(raw, bytes): raw = raw.decode('utf-8')
            return json.loads(raw)
        return None

    @classmethod
    def delete_model(cls, model_id):
        """Delete a model by ID."""
        if not redis_client:
            return False
            
        try:
            if not redis_client.hexists(cls.MODELS_KEY, model_id):
                return False
            
            # Get model type before deleting to remove from active list if needed
            model = cls._get_model_by_id(model_id)
            
            redis_client.hdel(cls.MODELS_KEY, model_id)
            
            if model and model.get('type'):
                # Check if it was active
                active_id = redis_client.hget(cls.ACTIVE_MODELS_HASH, model['type'])
                if active_id and active_id.decode('utf-8') == model_id:
                    redis_client.hdel(cls.ACTIVE_MODELS_HASH, model['type'])
            
            # [NEW] Delete file from disk if passing simple checks
            try:
                import os
                path = model.get('path')
                # Basic safety check: only delete if in 'models/' directory or specific allowed paths
                # to avoid deleting system files if path is absolute logic is weird
                if path and 'models' in path and os.path.exists(path):
                    os.remove(path)
                    logger.info(f"🗑️ Deleted model file: {path}")
            except Exception as e:
                logger.error(f"Error deleting model file: {e}")

            logger.info(f"Deleted model: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            raise e

    @classmethod
    def deactivate_model_type(cls, model_type):
        """Deactivate (unset) the active model for a specific type."""
        if not redis_client:
            return False
        
        try:
            if model_type not in cls.VALID_TYPES:
                # Allow flexible types if needed, but warning
                pass
                
            redis_client.hdel(cls.ACTIVE_MODELS_HASH, model_type)
            logger.info(f"🚫 Deactivated model type: {model_type}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating model type: {e}")
            raise e

    @classmethod
    def init_default_models(cls):
        """Initialize default models from config if Redis is empty."""
        if not redis_client:
            return
            
        try:
            # Check if models already exist
            if redis_client.hlen(cls.MODELS_KEY) > 0:
                logger.info("Models already exist in Redis, skipping default init")
                return

            logger.info("Initializing default models in Redis...")
            
            # Import configs to load defaults
            from app.domains.pano.config import MULTIPROBLEM_DETECTION_CONFIG, SEGMENTATION_CONFIG
            from app.domains.cbct.config import CBCT_DETECTION_CONFIG, CBCT_SEGMENTATION_CONFIG
            
            # 1. Pano Detection
            for cfg in MULTIPROBLEM_DETECTION_CONFIG:
                model = cls.register_model(
                    name=cfg.get('name', 'default_pano_det'),
                    path=cfg.get('path'),
                    model_type='pano_detection',
                    threshold=cfg.get('threshold', 0.5)
                )
                cls.set_active_model(model['id'])
            
            # 2. Pano Segmentation (Single)
            if SEGMENTATION_CONFIG:
                 model = cls.register_model(
                    name='default_pano_seg',
                    path=SEGMENTATION_CONFIG.get('path'),
                    model_type='pano_segmentation',
                    threshold=SEGMENTATION_CONFIG.get('threshold', 0.2)
                )
                 cls.set_active_model(model['id'])

            # 3. CBCT Detection
            for cfg in CBCT_DETECTION_CONFIG:
                model = cls.register_model(
                    name=cfg.get('name', 'default_cbct_det'),
                    path=cfg.get('path'),
                    model_type='cbct_detection',
                    threshold=cfg.get('threshold', 0.5)
                )
                cls.set_active_model(model['id'])

            # 4. CBCT Segmentation (Single)
            if CBCT_SEGMENTATION_CONFIG:
                 model = cls.register_model(
                    name='default_cbct_seg',
                    path=CBCT_SEGMENTATION_CONFIG.get('path'),
                    model_type='cbct_segmentation',
                    threshold=CBCT_SEGMENTATION_CONFIG.get('threshold', 0.1)
                )
                 cls.set_active_model(model['id'])
                
            logger.info("✅ Default models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default models: {e}")
