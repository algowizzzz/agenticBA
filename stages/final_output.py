"""
Implements the Final Output stage of the agent.
"""
import logging
import os

from langchain_anthropic import ChatAnthropic
# from langchain.prompts import load_prompt # Remove load_prompt
from langchain.prompts import PromptTemplate # Keep PromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

# Constants
PROMPT_PATH = "prompts/final_output_prompt.txt"
DEFAULT_MODEL = "claude-3-5-sonnet-20240620"

def create_final_output_chain(model_name: str = DEFAULT_MODEL, temperature: float = 0.0) -> LLMChain:
    """
    Creates and returns an LLMChain for the final output stage.

    Args:
        model_name (str): The name of the Claude model to use.
        temperature (float): The temperature setting for the LLM.

    Returns:
        LLMChain: The configured LangChain LLMChain for final output generation.

    Raises:
        FileNotFoundError: If the prompt file cannot be found.
        KeyError: If the ANTHROPIC_API_KEY environment variable is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Final Output Stage Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        # Read the prompt content from the .txt file
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        # Input variables expected by the prompt template
        input_vars = ["query", "reasoning_text"]
        final_output_prompt_template = PromptTemplate(template=prompt_content, input_variables=input_vars)
    except FileNotFoundError:
        logger.error(f"Final Output Stage Error: Prompt file not found at {PROMPT_PATH}")
        raise
    except Exception as e:
        logger.error(f"Final Output Stage Error: Failed to read or parse prompt file {PROMPT_PATH} - {e}")
        raise RuntimeError(f"Failed to load final output prompt: {e}")

    final_output_llm = ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_tokens=1500 # Allow ample space for comprehensive answers
    )

    final_output_chain = LLMChain(llm=final_output_llm, prompt=final_output_prompt_template)
    logger.info(f"Final output chain created with model {model_name}")
    return final_output_chain

def generate_final_answer(final_output_chain: LLMChain, query: str, reasoning_text: str) -> str:
    """
    Generates the final user-facing answer.

    Args:
        final_output_chain (LLMChain): The pre-configured final output LLMChain.
        query (str): The original user query.
        reasoning_text (str): The reasoning text from the previous stage.

    Returns:
        str: The generated final answer, or an error message.
    """
    # Check if reasoning stage produced an error
    if reasoning_text.startswith("ERROR:"):
        logger.error("Cannot generate final answer because reasoning stage failed.")
        return "I encountered an error during the reasoning process and cannot provide a final answer."

    logger.info(f"Generating final answer for query: {query[:50]}...")
    logger.debug(f"Final Answer Input Reasoning:\n{reasoning_text}")

    try:
        final_answer = final_output_chain.run({
            "query": query,
            "reasoning_text": reasoning_text
        })
        logger.info("Final answer generated.")
        logger.debug(f"Final Answer Text:\n{final_answer}")

        if not final_answer:
             logger.warning("Final output chain returned empty output.")
             return "I apologize, but I couldn't formulate a final answer based on the analysis."

        return final_answer.strip()

    except Exception as e:
        logger.error(f"Error during final answer generation: {e}", exc_info=True)
        return "I encountered an error while generating the final answer."

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

    # Dummy reasoning text for testing
    test_query = "What was the revenue for Company X last quarter and find recent news about them?"
    dummy_reasoning = ("Based on the execution, the FinancialSQL tool reported Company X revenue as $5 million for the last quarter. "
                       "The NewsSearch tool found two relevant articles: one about a recent investment round and another about a new product launch. "
                       "Both parts of the query were successfully addressed. The information seems consistent and complete.")

    print("\n--- Testing Final Output Stage --- Kicking this off ---\n")

    try:
        test_final_chain = create_final_output_chain()
        final_answer = generate_final_answer(test_final_chain, test_query, dummy_reasoning)

        print("\n--- Final Answer ---")
        print(final_answer)

        # Test error case from reasoning
        error_reasoning = "ERROR: Reasoning stage failed due to an internal error."
        final_answer_error = generate_final_answer(test_final_chain, test_query, error_reasoning)
        print("\n--- Final Answer (from error) ---")
        print(final_answer_error)

    except (KeyError, FileNotFoundError) as e:
        print(f"Setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}", exc_info=True) 