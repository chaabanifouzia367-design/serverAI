"""
Custom Exceptions

Application-wide custom exception classes.
"""


class FileUploadError(Exception):
    """Exception raised for file upload errors."""
    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class ProcessingError(Exception):
    """Exception raised during file processing."""
    pass
