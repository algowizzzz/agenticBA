#!/usr/bin/env python3
"""
Script to create a .env file for testing
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_env_file():
    """Create a .env file with the necessary environment variables"""
    # Check if .env file already exists
    if os.path.exists(".env"):
        logger.info(".env file already exists. Will not overwrite.")
        return
    
    # Ask for API key
    api_key = input("Enter your Anthropic API key: ")
    
    # Write to .env file
    with open(".env", "w") as f:
        f.write(f"ANTHROPIC_API_KEY={api_key}\n")
    
    logger.info(".env file created successfully.")

if __name__ == "__main__":
    create_env_file() 