import argparse
from langchain_tools.agent import HierarchicalRetrievalAgent
import os
import logging
from langchain_tools.tool2_category import get_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Added argument parsing setup
parser = argparse.ArgumentParser(description="Run Hierarchical Retrieval Agent with a query.")
parser.add_argument("-q", "--query", required=True, help="The query to run through the agent.")

def main(query: str):
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # First try the category tool directly
    category_tool = get_tool(api_key)
    logger.info("\nTrying category tool directly:")
    logger.info("(Skipping direct category tool call for this test)")
    
    # Then try through the agent
    agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
    logger.info(f"\nRunning through agent: {query}")
    
    try:
        response = agent.query(query)
        print("\nAgent response:", response)
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    args = parser.parse_args()
    main(args.query) 