"""
Base Configuration

Main application configuration from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    PORT = int(os.getenv('PORT', 5030))
    
    # File Storage
    # File Storage
    BASE_PATH = os.getenv('BASE_PATH', './storage/cache_slices')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './storage/uploads')
    PROCESSED_FOLDER = os.getenv('PROCESSED_FOLDER', './storage/processed')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 1073741824))  # 1GB default
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE  # Flask limit matched to custom limit
    MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', 100))  # Max pending tasks
    
    # File Types
    ALLOWED_EXTENSIONS = {'.nii', '.nii.gz', '.dcm', '.dicom', '.ima'}
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    ALLOWED_REPORT_TYPES = {'cbct', 'panoramic', 'cephalometric', 'intraoral'}
    
    # Redis & Celery
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Supabase (from environment ONLY - no hardcoded keys!)
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './jobs.db')
    
    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment variables")
        return True
