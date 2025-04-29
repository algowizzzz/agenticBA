"""
Implements the Execution stage of the agent using AgentExecutor.
"""
import logging
import os
from typing import List, Dict, Any

from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain import hub # To pull prompts like react

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "claude-3-5-sonnet-20240620"
REACT_PROMPT_HUB_REF = "hwchase17/react" # Standard ReAct prompt

def create_execution_agent(tools: List[Tool], model_name: str = DEFAULT_MODEL, temperature: float = 0.0, verbose: bool = True) -> AgentExecutor:
    """
    Creates and returns an AgentExecutor for the execution stage.

    Uses the ReAct (Reasoning and Acting) framework.

    Args:
        tools (List[Tool]): The list of available tools for the agent.
        model_name (str): The name of the Claude model to use.
        temperature (float): The temperature setting for the LLM.
        verbose (bool): Whether to run the agent in verbose mode.

    Returns:
        AgentExecutor: The configured LangChain AgentExecutor.

    Raises:
        KeyError: If the ANTHROPIC_API_KEY environment variable is not set.
        Exception: If the ReAct prompt cannot be pulled from the hub.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Execution Stage Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        # Pull the standard ReAct prompt
        prompt = hub.pull(REACT_PROMPT_HUB_REF)
    except Exception as e:
        logger.error(f"Execution Stage Error: Failed to pull ReAct prompt '{REACT_PROMPT_HUB_REF}' from Langchain Hub - {e}")
        raise

    execution_llm = ChatAnthropic(
        model=model_name,
        temperature=temperature,
        # max_tokens might need adjustment based on complexity
    )

    # Construct the ReAct agent
    agent = create_react_agent(execution_llm, tools, prompt)

    # Create an agent executor by passing in the agent and tools
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True, # Gracefully handle LLM output parsing errors
        max_iterations=10 # Limit the number of steps to prevent loops
    )

    logger.info(f"Execution AgentExecutor created with model {model_name} and {len(tools)} tools.")
    return agent_executor

def run_execution(agent_executor: AgentExecutor, confirmed_plan: str, query: str) -> Dict[str, Any]:
    """
    Runs the execution stage using the AgentExecutor.

    Args:
        agent_executor (AgentExecutor): The pre-configured agent executor.
        confirmed_plan (str): The user-confirmed plan text.
        query (str): The original user query.

    Returns:
        Dict[str, Any]: A dictionary containing the execution results.
                      Expected keys: 'output' (final answer or summary from agent),
                                     'intermediate_steps' (tool calls and observations).
                      Returns {'error': message} on failure.
    """
    # Prepare the input for the agent, including the plan for guidance
    # Prepending the plan to the query is a simple way to guide the ReAct agent.
    agent_input = (
        f"You have the following plan to execute:\n--- PLAN START ---\n{confirmed_plan}\n--- PLAN END ---" 
        f"\n\nNow, execute this plan step-by-step to answer the original user query: \"{query}\"."
        f"\nProvide the final answer once the plan is complete."
    )

    logger.info(f"Running execution agent for query: {query[:50]}...")
    logger.debug(f"Agent Input:\n{agent_input}")

    try:
        # Use invoke for more structured output including intermediate steps
        result = agent_executor.invoke({"input": agent_input})
        logger.info("Execution agent finished.")
        logger.debug(f"Agent Result: {result}")

        # Check if the result contains the expected keys
        if isinstance(result, dict) and 'output' in result:
            # Intermediate steps might be useful for the reasoning stage later
            return {
                "output": result.get('output', "Agent did not produce final output."),
                "intermediate_steps": result.get('intermediate_steps', [])
            }
        else:
            logger.warning(f"Execution agent returned unexpected result format: {result}")
            return {"error": "Agent execution finished with unexpected result format.", "raw_result": result}

    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        return {"error": f"Agent execution failed due to an internal error: {e}"}

# Example Usage (for testing this file directly)
if __name__ == '__main__':
    import os
    # Basic logging setup for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load .env for testing
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(".env file loaded.")
    else:
        logger.warning(".env file not found, ensure ANTHROPIC_API_KEY is set.")

    # Create dummy tools for testing
    def dummy_sql(query: str) -> str:
        logger.info(f"DummySQL called with: {query}")
        if "revenue" in query.lower() and "company x" in query.lower():
            return "Result: Company X revenue was $5 million."
        return "Result: Dummy SQL query executed."

    def dummy_news(query: str) -> str:
        logger.info(f"DummyNews called with: {query}")
        if "company x" in query.lower():
            return "Result: Found 2 news articles about Company X. 1) Investment round closed. 2) New product launch."
        return "Result: Dummy news search executed."

    dummy_tools = [
        Tool(name="FinancialSQL", func=dummy_sql, description="Query financial database for metrics like revenue."),
        Tool(name="NewsSearch", func=dummy_news, description="Search recent financial news.")
    ]

    # Define a sample plan and query
    test_query = "What was the revenue for Company X last quarter and find recent news about them?"
    test_plan = (
        "1. Use the FinancialSQL tool to find the revenue for Company X last quarter.\n"
        "2. Use the NewsSearch tool to find recent news about Company X.\n"
        "3. Summarize the findings."
    )

    print("\n--- Testing Execution Stage --- Kicking this off ---\n")

    try:
        execution_agent = create_execution_agent(dummy_tools, verbose=True)
        execution_result = run_execution(execution_agent, test_plan, test_query)

        print("\n--- Execution Result ---")
        print(execution_result)

    except (KeyError, FileNotFoundError) as e:
        print(f"Setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}", exc_info=True) 