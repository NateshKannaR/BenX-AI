import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_current_timestamp() -> str:
    """
    Returns the current timestamp in the format YYYY-MM-DD HH:MM:SS.
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_environment_variable(var_name: str) -> Optional[str]:
    """
    Retrieves the value of an environment variable.
    
    Args:
        var_name (str): The name of the environment variable.
    
    Returns:
        Optional[str]: The value of the environment variable, or None if it does not exist.
    """
    return os.environ.get(var_name)

def is_valid_email(email: str) -> bool:
    """
    Checks if the provided email address is valid.
    
    Args:
        email (str): The email address to validate.
    
    Returns:
        bool: True if the email address is valid, False otherwise.
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))

def flatten_list(nested_list: List[Any]) -> List[Any]:
    """
    Flattens a nested list into a single-level list.
    
    Args:
        nested_list (List[Any]): The nested list to flatten.
    
    Returns:
        List[Any]: The flattened list.
    """
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges two dictionaries into a single dictionary.
    
    Args:
        dict1 (Dict[str, Any]): The first dictionary.
        dict2 (Dict[str, Any]): The second dictionary.
    
    Returns:
        Dict[str, Any]: The merged dictionary.
    """
    merged_dict = dict1.copy()
    merged_dict.update(dict2)
    return merged_dict

def log_error(message: str, exception: Exception) -> None:
    """
    Logs an error message with the provided exception.
    
    Args:
        message (str): The error message.
        exception (Exception): The exception to log.
    """
    logging.error(message, exc_info=exception)