"""
Main entry point for the Enterprise Internal Agent.
"""
import logging
import os
import sys
from dotenv import load_dotenv
from typing import Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Add project root to sys.path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agents.internal_agent import run_agent_loop
from langchain_tools.tool_factory import (
    create_financial_sql_tool,
    create_ccr_sql_tool,
    create_financial_news_search_tool,
    create_transcript_agent_tool
)
from stages.guardrails import create_guardrails_chain
from stages.planning import create_planning_chain
from stages.execution import create_execution_agent
from stages.reasoning import create_reasoning_chain
from stages.final_output import create_final_output_chain
from langchain_anthropic import ChatAnthropic
# Import other necessary components as they are built

# --- Configuration ---
# Load environment variables from .env file
# dotenv_path = os.path.join(project_root, '.env') # Removed explicit path calculation
# if os.path.exists(dotenv_path):
#     load_dotenv(dotenv_path)
#     print("Loaded .env file.")
# else:
#     print("Warning: .env file not found. Ensure API keys are set in environment.")

# Try loading .env directly - dotenv should find it in the current/parent dir
loaded_env = load_dotenv() 
if loaded_env:
    print("Loaded .env file successfully.")
else:
    print("Warning: .env file not found or empty. Ensure API keys are set in environment.")

# Basic Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout # Log to console
)
logger = logging.getLogger(__name__)

# --- Constants for DB Paths (Assuming env vars) ---
# Update default paths to the likely populated DBs in scripts/data/
FINANCIAL_DB_PATH = os.getenv("FINANCIAL_DB_PATH", "scripts/data/financial_data.db") # Updated default path
CCR_DB_PATH = os.getenv("CCR_DB_PATH", "scripts/data/ccr_reporting.db") # Updated default path

# --- DB Availability Check ---
if not os.path.exists(FINANCIAL_DB_PATH):
    logger.warning(f"Financial DB file not found at specified path: {FINANCIAL_DB_PATH}. FinancialSQL tool may fail.")
    # Optionally exit: sys.exit(f"Error: Financial DB not found at {FINANCIAL_DB_PATH}")
if not os.path.exists(CCR_DB_PATH):
    logger.warning(f"CCR DB file not found at specified path: {CCR_DB_PATH}. CCRSQL tool may fail.")
    # Optionally exit: sys.exit(f"Error: CCR DB not found at {CCR_DB_PATH}")
# ---------------------------

# --- Add function to create confirmation chain --- >
CONFIRMATION_PROMPT_PATH = "prompts/confirmation_prompt.txt"
CONFIRMATION_MODEL = "claude-3-haiku-20240307" # Use fast model

def create_confirmation_classification_chain(model_name: str = CONFIRMATION_MODEL, temperature: float = 0.0) -> LLMChain:
    """Creates an LLMChain to classify user confirmation responses."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Confirmation Chain Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        with open(CONFIRMATION_PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        prompt = PromptTemplate(template=prompt_content, input_variables=["user_response"])
    except Exception as e:
        logger.error(f"Failed to load confirmation prompt: {e}")
        raise RuntimeError(f"Failed to load confirmation prompt: {e}")

    llm = ChatAnthropic(model=model_name, temperature=temperature, max_tokens=10)
    chain = LLMChain(llm=llm, prompt=prompt)
    logger.info(f"Confirmation classification chain created with model {model_name}")
    return chain
# <---------------------------------------------

# --- Initialization ---
def initialize_agent_components():
    """Initializes and returns all necessary components for the agent."""
    logger.info("Initializing agent components...")

    # Create LLM instance needed by some tools first
    try:
        llm_for_tools = create_llm()
        logger.info("LLM for tools initialized.")
    except Exception as e:
         logger.error(f"Fatal Error: Failed to initialize LLM for tools - {e}", exc_info=True)
         sys.exit(1)

    # 1. Load Tools (Using existing factory functions)
    try:
        financial_sql_tool = create_financial_sql_tool(db_path=FINANCIAL_DB_PATH, llm=llm_for_tools)
        ccr_sql_tool = create_ccr_sql_tool(db_path=CCR_DB_PATH, llm=llm_for_tools)
        news_tool = create_financial_news_search_tool()
        transcript_tool = create_transcript_agent_tool(llm=llm_for_tools)
        tools = [financial_sql_tool, ccr_sql_tool, news_tool, transcript_tool]
        logger.info(f"Loaded {len(tools)} tools.")
    # except NameError as ne: # This specific handler might not be needed anymore
    #     logger.error(f"Fatal Error: Missing LLM initialization dependency for tools - {ne}", exc_info=True)
    #     sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize tools - {e}", exc_info=True)
        sys.exit(1)

    # 2. Create Guardrails Chain
    try:
        guardrails_chain = create_guardrails_chain()
        logger.info("Guardrails chain created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize guardrails chain - {e}", exc_info=True)
        sys.exit(1)

    # 3. Create Planning Chain
    try:
        planning_chain = create_planning_chain(tools=tools)
        logger.info("Planning chain created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize planning chain - {e}", exc_info=True)
        sys.exit(1)

    # 4. Create Execution Agent/Chain
    try:
        # Using verbose=True for development/debugging
        execution_agent = create_execution_agent(tools=tools, verbose=True)
        logger.info("Execution agent created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize execution agent - {e}", exc_info=True)
        sys.exit(1)

    # 5. Create Reasoning Chain
    try:
        reasoning_chain = create_reasoning_chain()
        logger.info("Reasoning chain created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize reasoning chain - {e}", exc_info=True)
        sys.exit(1)

    # 6. Create Final Output Chain
    try:
        final_output_chain = create_final_output_chain()
        logger.info("Final output chain created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize final output chain - {e}", exc_info=True)
        sys.exit(1)

    # --- Add Confirmation Chain Init --->
    try:
        confirmation_chain = create_confirmation_classification_chain()
        logger.info("Confirmation classification chain created.")
    except Exception as e:
        logger.error(f"Fatal Error: Failed to initialize confirmation chain - {e}", exc_info=True)
        sys.exit(1)
    # <----------------------------------

    components = {
        "tools": tools,
        "guardrails_chain": guardrails_chain,
        "planning_chain": planning_chain,
        "execution_component": execution_agent,
        "reasoning_chain": reasoning_chain,
        "final_output_chain": final_output_chain,
        "confirmation_chain": confirmation_chain,
        "llm_for_tools": llm_for_tools, # Add LLM instance if needed elsewhere
    }
    logger.info("Agent components initialized.")
    return components

# --- Add create_llm function if not already present ---
def create_llm(
    api_key: Optional[str] = None,
    model: str = "claude-3-5-sonnet-20240620",
    temperature: float = 0,
) -> ChatAnthropic:
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not provided or found.")
    return ChatAnthropic(
        model=model, temperature=temperature, anthropic_api_key=api_key
    )

# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Enterprise Agent...")
    agent_components = initialize_agent_components()

    # Start the main agent loop
    try:
        run_agent_loop(agent_components)
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred in the agent loop: {e}", exc_info=True)
    finally:
        logger.info("Enterprise Agent shutting down.") 