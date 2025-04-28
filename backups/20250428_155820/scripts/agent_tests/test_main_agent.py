import argparse
# Adjust import based on new location
import sys
import os
import time
from pathlib import Path
import datetime
import uuid
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))) 
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))
from langchain_tools.agent import HierarchicalRetrievalAgent
# Remove direct tool import if not needed for direct call
# from langchain_tools.tool2_category import get_tool 
import logging

# Define base directory for test results relative to this script
SCRIPT_DIR = Path(__file__).parent
RESULTS_BASE_DIR = SCRIPT_DIR / "../.." / "test_results" # Place it at project root

# Configure logging (initial console setup)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Get root logger to add handlers
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) # Set desired level for all logs
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__) # Logger for this script's messages

# Added argument parsing setup
parser = argparse.ArgumentParser(description="Run Hierarchical Retrieval Agent with a query.")
parser.add_argument("-q", "--query", required=True, help="The query to run through the agent.")
parser.add_argument("-k", "--api_key", help="Anthropic API key. If not provided, will use environment variable.")

def check_api_key(api_key=None):
    """Verify API key is present and properly formatted"""
    if api_key:
        logger.info("Using API key provided as command-line argument")
        if not api_key.startswith("sk-ant-"):
            logger.warning("API key format warning: Key should start with 'sk-ant-'")
    else:
        # Check environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not found!")
            logger.error("Please set the API key using one of these methods:")
            logger.error("1. Run with: -k YOUR_API_KEY")
            logger.error("2. Set environment variable: export ANTHROPIC_API_KEY=YOUR_API_KEY")
            logger.error("3. Add to .env file in project root")
            logger.error("4. Run scripts/setup_api_key.py to interactively set up your key")
            return None
        else:
            logger.info(f"Using API key from environment variable (length: {len(api_key)})")
            if not api_key.startswith("sk-ant-"):
                logger.warning("API key format warning: Key should start with 'sk-ant-'")
    
    # Simple format check 
    if len(api_key) < 20:
        logger.warning("API key appears too short")
        
    return api_key

def main(query: str, api_key=None):
    # --- Create unique output directory ---
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_uuid = str(uuid.uuid4())[:8] # Short UUID
    run_dir_name = f"run_{run_timestamp}_{run_uuid}"
    run_output_dir = RESULTS_BASE_DIR / run_dir_name
    try:
        run_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created results directory: {run_output_dir}")
    except OSError as e:
        logger.error(f"Failed to create results directory {run_output_dir}: {e}")
        # Optionally exit or continue without file logging/saving
        return # Exit if directory creation fails

    # --- Configure file logging ---
    log_file_path = run_output_dir / "log.txt"
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler) # Add file handler to root logger
    logger.info(f"Logging detailed output to: {log_file_path}")

    # --- Start Agent Execution --- 
    logger.info(f"Starting agent test run for query: '{query}'")

    # Verify API key
    logger.info("--- Checking API key... ---")
    api_key = check_api_key(api_key)
    if not api_key:
        # Remove file handler before exiting? 
        root_logger.removeHandler(file_handler)
        raise ValueError("ANTHROPIC_API_KEY not set or invalid")
    
    # Log key length for debugging
    logger.info(f"API key OK (length: {len(api_key)}, first5: {api_key[:5]}..., last5: ...{api_key[-5:]})")

    # Initialize with debug=True to potentially see more logs
    agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True) 
    logger.info(f"\nRunning through agent: {query}")

    agent_response = None # Initialize response variable
    try:
        agent_response = agent.query(query)
        print("\nAgent response (raw):", agent_response) # Keep console output for raw response
        logger.info(f"Agent execution completed.")

    except Exception as e:
        logger.error(f"Error during agent execution: {e}")
        # Print traceback for debugging
        import traceback
        logger.error(traceback.format_exc()) # Log traceback to file

    # --- Save Agent Response --- 
    if agent_response is not None:
        response_file_path = run_output_dir / "response.txt"
        try:
            with open(response_file_path, 'w') as f:
                json.dump(agent_response, f, indent=2)
            logger.info(f"Saved agent response to: {response_file_path}")
        except IOError as e:
            logger.error(f"Failed to save agent response to {response_file_path}: {e}")
    else:
        logger.warning("Agent response was None, skipping saving response file.")

    # --- Cleanup --- 
    # Remove file handler so subsequent runs don't log to the same file 
    # (if script were long-running, but good practice)
    root_logger.removeHandler(file_handler)
    file_handler.close()
    logger.info("Test run finished.")

if __name__ == "__main__":
    args = parser.parse_args()
    main(args.query, args.api_key) 