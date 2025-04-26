import os
import sys
import argparse
import logging
from dotenv import load_dotenv
import datetime # Added to potentially format default dates if needed

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Now import from langchain_tools
# Import the specific CCR tool creator and the LLM creator
from langchain_tools.tool_factory import create_ccr_sql_tool, create_llm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load environment variables (especially ANTHROPIC_API_KEY)
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables.")
        sys.exit(1)

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Test the CCR SQL Query Tool directly.")
    parser.add_argument("-q", "--query", required=True, help="The natural language query for the CCR SQL tool.")
    args = parser.parse_args()

    logger.info(f"Testing CCR SQL Tool with query: {args.query}")

    # Define database path (relative to project root) - POINT TO CCR DB
    db_path_relative = "ccr_reporting.db" # Use the new CCR database file
    db_path_absolute = os.path.join(project_root, db_path_relative)
    logger.info(f"Using database at: {db_path_absolute}")

    # Check if DB file exists
    if not os.path.exists(db_path_absolute):
        logger.error(f"Database file not found: {db_path_absolute}")
        logger.error("Please ensure you have run the script to create and populate 'ccr_reporting.db'.")
        sys.exit(1)

    # Create the LLM instance
    try:
        llm = create_llm(api_key=api_key)
        logger.info("LLM created successfully.")
    except Exception as e:
        logger.error(f"Failed to create LLM: {e}")
        sys.exit(1)

    # Create the CCR SQL tool
    # Use the specific factory function for the CCR tool
    sql_tool = create_ccr_sql_tool(db_path=db_path_absolute, llm=llm)

    # Check if the tool creation resulted in an error tool
    if sql_tool.name.endswith("_error"):
        logger.error(f"Failed to create CCR SQL tool: {sql_tool.description}")
        sys.exit(1)

    logger.info(f"CCR SQL Tool ({sql_tool.name}) created successfully.")

    # Run the tool
    try:
        logger.info("Running the CCR SQL tool...")
        # The tool's func returns a dictionary {"status": "...", "result": "..."}
        result_dict = sql_tool.func(args.query)
        logger.info("CCR SQL Tool execution finished.")

        print("\n--- CCR SQL Tool Result ---")
        if isinstance(result_dict, dict) and 'status' in result_dict and 'result' in result_dict:
            print(f"Status: {result_dict['status']}")
            print(f"Result: {result_dict['result']}")
        else:
            # Fallback for unexpected output format
            logger.warning(f"Unexpected result format from CCR SQL tool: {result_dict}")
            print(f"Raw Output: {result_dict}")
        print("---------------------------")

    except Exception as e:
        logger.error(f"Error running CCR SQL tool test script: {e}", exc_info=True)
        # Print the error in a similar format if the script itself fails
        print("\n--- CCR SQL Tool Execution Error ---")
        print(f"Status: script_error")
        print(f"Result: {type(e).__name__} - {str(e)}")
        print("--------------------------------")
        sys.exit(1)

if __name__ == "__main__":
    main() 