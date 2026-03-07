import logging
import sys
from typing import NoReturn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main() -> NoReturn:
    """
    Main application entry point.
    """
    logging.info("Application started")
    
    try:
        # Application logic goes here
        logging.info("Application running")
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        sys.exit(1)
    finally:
        logging.info("Application stopped")

if __name__ == "__main__":
    main()