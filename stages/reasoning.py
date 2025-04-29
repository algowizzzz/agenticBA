"""
Implements the Reasoning stage of the agent.
"""
import logging
import os
from typing import Dict, Any, List

from langchain_core.agents import AgentStep
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

# Constants
PROMPT_PATH = "prompts/reasoning_prompt.txt"
DEFAULT_MODEL = "claude-3-5-sonnet-20240620"

def format_execution_summary(agent_output: str, intermediate_steps: List[AgentStep]) -> str:
    """
    Formats the agent's output and intermediate steps into a string for the reasoning prompt.
    Handles different observation types (string vs dictionary).
    """
    summary_lines = []
    if intermediate_steps:
        summary_lines.append("Intermediate Tool Steps:")
        for i, step in enumerate(intermediate_steps):
            tool = step.action.tool
            tool_input = step.action.tool_input
            observation = step.observation
            summary_lines.append(f"\nStep {i+1}: Tool={tool}, Input='{tool_input}'")

            # Format observation based on type
            if isinstance(observation, dict):
                summary_lines.append("  Observation (Structured):")
                # Check for common keys from our SQL tools
                if 'sql_query' in observation:
                    summary_lines.append(f"    - SQL Generated: {observation['sql_query']}")
                if 'sql_result' in observation:
                    res_str = str(observation['sql_result'])
                    res_preview = (res_str[:200] + '...') if len(res_str) > 200 else res_str
                    summary_lines.append(f"    - SQL Result: {res_preview}")
                if 'error' in observation and observation['error']:
                    summary_lines.append(f"    - Error: {observation['error']}")
                # Optionally include other keys if needed
                # for key, value in observation.items():
                #     if key not in ['sql_query', 'sql_result', 'error']:
                #         summary_lines.append(f"    - {key}: {str(value)[:100]}...") # Truncate other values
            elif isinstance(observation, str):
                summary_lines.append("  Observation (Text):")
                obs_preview = (observation[:300] + '...') if len(observation) > 300 else observation
                summary_lines.append(f"    {obs_preview.strip()}")
            else:
                # Fallback for other types
                summary_lines.append("  Observation (Other Type):")
                obs_preview = (str(observation)[:300] + '...') if len(str(observation)) > 300 else str(observation)
                summary_lines.append(f"    {obs_preview.strip()}")

        summary_lines.append("\nFinal Output from Execution Agent:")
        summary_lines.append(agent_output)
    else:
        summary_lines.append("Execution Agent Output (No intermediate steps available):")
        summary_lines.append(agent_output)

    return "\n".join(summary_lines)

def create_reasoning_chain(model_name: str = DEFAULT_MODEL, temperature: float = 0.0) -> LLMChain:
    """
    Creates and returns an LLMChain for the reasoning stage.

    Args:
        model_name (str): The name of the Claude model to use.
        temperature (float): The temperature setting for the LLM.

    Returns:
        LLMChain: The configured LangChain LLMChain for reasoning.

    Raises:
        FileNotFoundError: If the prompt file cannot be found.
        KeyError: If the ANTHROPIC_API_KEY environment variable is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Reasoning Stage Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        # Read the prompt content from the .txt file
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        # Input variables expected by the prompt template
        input_vars = ["query", "execution_summary"]
        reasoning_prompt_template = PromptTemplate(template=prompt_content, input_variables=input_vars)
    except FileNotFoundError:
        logger.error(f"Reasoning Stage Error: Prompt file not found at {PROMPT_PATH}")
        raise
    except Exception as e:
        logger.error(f"Reasoning Stage Error: Failed to read or parse prompt file {PROMPT_PATH} - {e}")
        raise RuntimeError(f"Failed to load reasoning prompt: {e}")

    reasoning_llm = ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_tokens=1000 # Allow for detailed reasoning
    )

    reasoning_chain = LLMChain(llm=reasoning_llm, prompt=reasoning_prompt_template)
    logger.info(f"Reasoning chain created with model {model_name}")
    return reasoning_chain

def run_reasoning(reasoning_chain: LLMChain, query: str, execution_results: Dict[str, Any]) -> str:
    """
    Runs the reasoning stage using the results from the execution stage.

    Args:
        reasoning_chain (LLMChain): The pre-configured reasoning LLMChain.
        query (str): The original user query.
        execution_results (Dict[str, Any]): The dictionary returned by run_execution.
                                            Expected keys: 'output', 'intermediate_steps'.

    Returns:
        str: The reasoning text generated by the LLM, or an error message.
    """
    agent_output = execution_results.get('output', "No output received from execution agent.")
    intermediate_steps = execution_results.get('intermediate_steps', [])

    execution_summary = format_execution_summary(agent_output, intermediate_steps)

    logger.info(f"Running reasoning for query: {query[:50]}...")
    logger.debug(f"Reasoning Input Summary:\n{execution_summary}")

    try:
        reasoning_text = reasoning_chain.run({
            "query": query,
            "execution_summary": execution_summary
        })
        logger.info("Reasoning stage finished.")
        logger.debug(f"Reasoning Text:\n{reasoning_text}")

        if not reasoning_text:
             logger.warning("Reasoning chain returned empty output.")
             return "ERROR: Reasoning process failed to produce output."

        return reasoning_text.strip()

    except Exception as e:
        logger.error(f"Error during reasoning stage: {e}", exc_info=True)
        return "ERROR: Reasoning stage failed due to an internal error."

# Example Usage (for testing this file directly)
if __name__ == '__main__':
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

    # Dummy execution results for testing
    test_query = "What was the revenue for Company X last quarter and find recent news about them?"
    dummy_execution_results = {
        'output': 'Company X had a revenue of $5 million last quarter. Recent news includes an investment round and a new product launch.',
        'intermediate_steps': [
            AgentStep(action=type('obj', (object,), {'tool': 'FinancialSQL', 'tool_input': 'SELECT revenue FROM financials WHERE company = "Company X" AND quarter = "last"', 'log': '...'})(), observation='Result: Company X revenue was $5 million.'),
            AgentStep(action=type('obj', (object,), {'tool': 'NewsSearch', 'tool_input': 'Company X recent news', 'log': '...'})(), observation='Result: Found 2 news articles about Company X. 1) Investment round closed. 2) New product launch.')
        ]
    }

    print("\n--- Testing Reasoning Stage --- Kicking this off ---\n")

    try:
        test_reasoning_chain = create_reasoning_chain()
        reasoning_output = run_reasoning(test_reasoning_chain, test_query, dummy_execution_results)

        print("\n--- Reasoning Output ---")
        print(reasoning_output)

    except (KeyError, FileNotFoundError) as e:
        print(f"Setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}", exc_info=True) 