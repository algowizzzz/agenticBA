import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from langchain_tools.tool_factory import create_transcript_agent_tool, create_llm

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Test the Transcript Search/Summary Agent Tool.")
    parser.add_argument("-q", "--query", type=str, required=True, help="The query to send to the transcript agent tool.")
    args = parser.parse_args()

    logger.info(f"Testing Transcript Agent Tool with query: {args.query}")

    # Load environment variables (especially ANTHROPIC_API_KEY)
    load_dotenv(os.path.join(project_root, '.env'))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in .env file.")
        sys.exit(1)

    try:
        # Initialize the LLM
        llm = create_llm(api_key=api_key)
        logger.info("LLM initialized successfully.")

        # Create the transcript agent tool
        # Note: This creates the Tool object which wraps the sub-agent executor.
        transcript_tool = create_transcript_agent_tool(llm=llm, api_key=api_key)
        logger.info("Transcript Agent Tool created successfully.")

        # Check if the tool creation resulted in an error tool
        if transcript_tool.name.endswith("_error"):
             logger.error(f"Failed to create transcript tool: {transcript_tool.description}")
             # Attempt to run the error tool to see the message
             error_result = transcript_tool.func(args.query)
             logger.error(f"Error tool output: {error_result}")
             sys.exit(1)


        # Directly call the function associated with the tool (the wrapper)
        # The Tool object's `func` attribute holds the callable function.
        logger.info("Invoking the transcript tool function...")
        result = transcript_tool.func(args.query)

        logger.info("Transcript Agent Tool execution finished.")
        print("\n--- Transcript Agent Tool Result ---")
        print(result)
        print("------------------------------------\n")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 