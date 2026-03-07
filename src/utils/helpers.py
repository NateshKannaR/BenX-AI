import logging
import os
import re
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_email(email):
    """
    Validate email address.
    
    Args:
    email (str): Email address to validate.
    
    Returns:
    bool: True if email is valid, False otherwise.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if re.match(email_regex, email):
        return True
    return False

def get_current_datetime():
    """
    Get current date and time.
    
    Returns:
    datetime: Current date and time.
    """
    return datetime.now()

def get_file_extension(filename):
    """
    Get file extension from filename.
    
    Args:
    filename (str): Filename to get extension from.
    
    Returns:
    str: File extension.
    """
    return os.path.splitext(filename)[1]

def is_directory(path):
    """
    Check if path is a directory.
    
    Args:
    path (str): Path to check.
    
    Returns:
    bool: True if path is a directory, False otherwise.
    """
    return os.path.isdir(path)

def is_file(path):
    """
    Check if path is a file.
    
    Args:
    path (str): Path to check.
    
    Returns:
    bool: True if path is a file, False otherwise.
    """
    return os.path.isfile(path)

def log_error(message):
    """
    Log error message.
    
    Args:
    message (str): Error message to log.
    """
    logging.error(message)

def log_info(message):
    """
    Log info message.
    
    Args:
    message (str): Info message to log.
    """
    logging.info(message)

def log_warning(message):
    """
    Log warning message.
    
    Args:
    message (str): Warning message to log.
    """
    logging.warning(message)