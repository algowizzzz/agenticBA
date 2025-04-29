"""
Implements the Planning stage of the agent.
"""
import logging
import os
from typing import List

from langchain.agents import Tool
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Configure logging
logger = logging.getLogger(__name__)

# Constants
PROMPT_PATH = "prompts/planning_prompt.txt"
DEFAULT_MODEL = "claude-3-5-sonnet-20240620" # Use Sonnet for planning

def format_tool_descriptions(tools: List[Tool]) -> str:
    """Formats the list of tools into a string description for the prompt."""
    if not tools:
        return "No tools available."
    descriptions = []
    for tool in tools:
        descriptions.append(f"- {tool.name}: {tool.description}")
    return "\n".join(descriptions)

def create_planning_chain(tools: List[Tool], model_name: str = DEFAULT_MODEL, temperature: float = 0.0) -> LLMChain:
    """
    Creates and returns an LLMChain for the planning stage.

    Args:
        tools (List[Tool]): The list of available tools for the agent.
        model_name (str): The name of the Claude model to use.
        temperature (float): The temperature setting for the LLM.

    Returns:
        LLMChain: The configured LangChain LLMChain for planning.

    Raises:
        FileNotFoundError: If the prompt file cannot be found.
        KeyError: If the ANTHROPIC_API_KEY environment variable is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Planning Stage Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        # Read the prompt content from the .txt file
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        # Input variables expected by the prompt template
        input_vars = ["query", "tool_descriptions"]
        planning_prompt_template = PromptTemplate(template=prompt_content, input_variables=input_vars)
    except FileNotFoundError:
        logger.error(f"Planning Stage Error: Prompt file not found at {PROMPT_PATH}")
        raise
    except Exception as e:
        logger.error(f"Planning Stage Error: Failed to read or parse prompt file {PROMPT_PATH} - {e}")
        raise RuntimeError(f"Failed to load planning prompt: {e}")

    planning_llm = ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_tokens=500 # Allow for moderately complex plans
    )

    # Prepare the full prompt with tool descriptions included
    tool_descriptions = format_tool_descriptions(tools)

    # Note: The prompt template loaded from file already has placeholders.
    # We will provide the variables when running the chain.
    planning_chain = LLMChain(llm=planning_llm, prompt=planning_prompt_template)
    logger.info(f"Planning chain created with model {model_name}")
    return planning_chain

def generate_plan(planning_chain: LLMChain, tools: List[Tool], query: str) -> str:
    """
    Generates a plan for the given query using the planning chain.

    Args:
        planning_chain (LLMChain): The pre-configured planning LLMChain.
        tools (List[Tool]): The list of available tools (needed for description).
        query (str): The user query.

    Returns:
        str: The generated plan as text.
    """
    try:
        tool_descriptions = format_tool_descriptions(tools)
        logger.info(f"Generating plan for query: {query[:50]}...")
        plan_text = planning_chain.run({
            "query": query,
            "tool_descriptions": tool_descriptions
        })
        logger.info(f"Generated plan:\n{plan_text}")
        # Basic validation: check if plan is empty or indicates failure
        if not plan_text or "cannot be answered" in plan_text.lower():
            logger.warning("Plan generation resulted in empty plan or failure message.")
            # Return the message as is, let the confirmation stage handle it
            return plan_text if plan_text else "ERROR: Failed to generate a plan."

        return plan_text.strip()

    except Exception as e:
        logger.error(f"Error during plan generation: {e}", exc_info=True)
        return "ERROR: Plan generation failed due to an internal error."

# Example Usage (for testing this file directly)
if __name__ == '__main__':
    # Basic logging setup for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load .env for testing
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(".env file loaded.")
    else:
        logger.warning(".env file not found, ensure ANTHROPIC_API_KEY is set.")

    # Create dummy tools for testing
    dummy_tools = [
        Tool(name="FinancialSQL", func=lambda x: x, description="Query financial database."),
        Tool(name="NewsSearch", func=lambda x: x, description="Search financial news.")
    ]

    try:
        test_planning_chain = create_planning_chain(dummy_tools)
        test_query = "What was the revenue for Company X last quarter and find recent news about them?"

        print("\n--- Testing Planning --- Kicking this off ---\n")

        generated_plan = generate_plan(test_planning_chain, dummy_tools, test_query)
        print(f"Query: '{test_query}'")
        print(f"Generated Plan:\n{generated_plan}\n")

        test_query_fail = "Tell me about the weather tomorrow."
        generated_plan_fail = generate_plan(test_planning_chain, dummy_tools, test_query_fail)
        print(f"Query: '{test_query_fail}'")
        print(f"Generated Plan:\n{generated_plan_fail}\n")

    except (KeyError, FileNotFoundError) as e:
        print(f"Setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}") 