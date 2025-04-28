#!/usr/bin/env python3
"""
Test script to directly test the Anthropic API key
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_anthropic_api_direct(api_key):
    """Test the Anthropic API key directly with a simple request"""
    if not api_key:
        logger.error("No API key provided for testing")
        return False
    
    logger.info(f"Using provided API key: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test direct API call
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Say hello"
            }
        ]
    }
    
    try:
        logger.info("Making direct API call to Anthropic")
        response = requests.post(url, headers=headers, json=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ API call successful: {result}")
            return True
        else:
            logger.error(f"❌ API call failed with status code {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API call failed with error: {e}")
        return False

if __name__ == "__main__":
    # Hardcode the new key for this specific test run
    test_key = "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"
    logger.info(f"--- Testing specific API key: {test_key[:5]}...{test_key[-5:]} ---")
    if test_anthropic_api_direct(test_key):
        print("\n✅ The provided API key is valid!")
        sys.exit(0)
    else:
        print("\n❌ The provided API key is INVALID!")
        sys.exit(1) 
"""
Test script to directly test the Anthropic API key
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_anthropic_api_direct(api_key):
    """Test the Anthropic API key directly with a simple request"""
    if not api_key:
        logger.error("No API key provided for testing")
        return False
    
    logger.info(f"Using provided API key: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test direct API call
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Say hello"
            }
        ]
    }
    
    try:
        logger.info("Making direct API call to Anthropic")
        response = requests.post(url, headers=headers, json=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ API call successful: {result}")
            return True
        else:
            logger.error(f"❌ API call failed with status code {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API call failed with error: {e}")
        return False

if __name__ == "__main__":
    # Hardcode the new key for this specific test run
    test_key = "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"
    logger.info(f"--- Testing specific API key: {test_key[:5]}...{test_key[-5:]} ---")
    if test_anthropic_api_direct(test_key):
        print("\n✅ The provided API key is valid!")
        sys.exit(0)
    else:
        print("\n❌ The provided API key is INVALID!")
        sys.exit(1) 
 
 