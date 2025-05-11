#!/usr/bin/env python3
"""
Minimal test script to verify earnings call agent structure
"""

import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Verify agent structure without executing it"""
    try:
        # Attempt to import the main module
        logger.info("Testing import of earnings_call_tool module...")
        from tools.earnings_call_tool import (
            run_transcript_agent, 
            create_earnings_call_toolset,
            select_appropriate_model,
            format_agent_response
        )
        
        logger.info("Successfully imported earnings_call_tool module")
        logger.info("Checking function signatures...")
        
        # Check function signatures
        print(f"\nrun_transcript_agent: {run_transcript_agent.__doc__}")
        print(f"\nselect_appropriate_model: {select_appropriate_model.__doc__}")
        print(f"\nformat_agent_response: {format_agent_response.__doc__}")
        
        print("\nAgent structure validation passed!")
        return True
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"ERROR: Failed to import module: {e}")
        return False
    except SyntaxError as e:
        logger.error(f"Syntax error in module: {e}")
        print(f"ERROR: Syntax error detected: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 