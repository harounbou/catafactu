"""
Error handling module for the POS system.
Provides consistent error handling and logging functionality.
"""
import logging
import os
import traceback
import streamlit as st
from datetime import datetime
from functools import wraps

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"pos_system_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("pos_system")

class DatabaseError(Exception):
    """Exception raised for database-related errors."""
    pass

class ValidationError(Exception):
    """Exception raised for data validation errors."""
    pass

class FileOperationError(Exception):
    """Exception raised for file operation errors."""
    pass

def log_error(error, context=None):
    """Log an error with optional context information."""
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    if context:
        logger.error(f"Error in {context}: {error_message}\n{error_traceback}")
    else:
        logger.error(f"Error: {error_message}\n{error_traceback}")

def handle_error(func):
    """Decorator to handle exceptions in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_error(e, func.__name__)
            st.error(f"Validation Error: {str(e)}")
            return None
        except DatabaseError as e:
            log_error(e, func.__name__)
            st.error(f"Database Error: {str(e)}")
            return None
        except FileOperationError as e:
            log_error(e, func.__name__)
            st.error(f"File Operation Error: {str(e)}")
            return None
        except Exception as e:
            log_error(e, func.__name__)
            st.error(f"An unexpected error occurred: {str(e)}")
            return None
    return wrapper

def validate_required_fields(data, required_fields):
    """Validate that all required fields are present and not empty."""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return True

def validate_numeric_field(value, field_name, min_value=None, max_value=None):
    """Validate that a field is numeric and within specified range."""
    try:
        numeric_value = float(value)
        
        if min_value is not None and numeric_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            raise ValidationError(f"{field_name} must be at most {max_value}")
            
        return numeric_value
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number")