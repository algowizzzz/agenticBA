"""
Implements the Guardrails stage for request validation.
"""
import logging
import os
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Configure logging
logger = logging.getLogger(__name__)

# Constants
PROMPT_PATH = "prompts/guardrails_prompt.txt"
DEFAULT_MODEL = "claude-3-haiku-20240307"

def create_guardrails_chain(model_name: str = DEFAULT_MODEL, temperature: float = 0.0) -> LLMChain:
    """
    Creates and returns an LLMChain for the guardrails check.

    Args:
        model_name (str): The name of the Claude model to use.
        temperature (float): The temperature setting for the LLM.

    Returns:
        LLMChain: The configured LangChain LLMChain.

    Raises:
        FileNotFoundError: If the prompt file cannot be found.
        KeyError: If the ANTHROPIC_API_KEY environment variable is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Guardrails Stage Error: ANTHROPIC_API_KEY not found.")
        raise KeyError("ANTHROPIC_API_KEY environment variable not set.")

    try:
        # Read the prompt content from the .txt file
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        guardrails_prompt = PromptTemplate(template=prompt_content, input_variables=["query"])
    except FileNotFoundError:
        logger.error(f"Guardrails Stage Error: Prompt file not found at {PROMPT_PATH}")
        raise
    except Exception as e:
        logger.error(f"Guardrails Stage Error: Failed to read or parse prompt file {PROMPT_PATH} - {e}")
        raise RuntimeError(f"Failed to load guardrails prompt: {e}")

    guardrails_llm = ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_tokens=50 # Expect short response (ALLOW/BLOCK: Reason)
    )

    guardrails_chain = LLMChain(llm=guardrails_llm, prompt=guardrails_prompt)
    logger.info(f"Guardrails chain created with model {model_name}")
    return guardrails_chain

def run_guardrails_check(guardrails_chain: LLMChain, query: str) -> tuple[bool, str | None]:
    """
    Runs the guardrails check on the user query.

    Args:
        guardrails_chain (LLMChain): The pre-configured guardrails LLMChain.
        query (str): The user query to check.

    Returns:
        tuple[bool, str | None]: A tuple containing:
            - bool: True if the query is allowed, False otherwise.
            - str | None: The reason for blocking, if applicable, otherwise None.
    """
    try:
        logger.info(f"Running guardrails check for query: {query[:50]}...")
        result = guardrails_chain.run(query=query)
        logger.info(f"Guardrails raw result: {result}")

        # Parse the result
        parsed_result = result.strip().upper()
        if parsed_result == "ALLOW":
            logger.info("Guardrails check passed.")
            return True, None
        elif parsed_result.startswith("BLOCK"):
            # Extract the reason if provided
            reason = parsed_result.split(":", 1)[-1].strip() if ":" in parsed_result else "Policy Violation"
            logger.warning(f"Guardrails check failed. Reason: {reason}")
            return False, reason
        else:
            # LLM didn't follow expected format, safer to block
            logger.warning(f"Guardrails LLM returned unexpected format: {result}. Blocking query.")
            return False, "Unexpected response format from guardrails check."

    except Exception as e:
        logger.error(f"Error during guardrails check: {e}", exc_info=True)
        # Fail safe: block if the check encounters an error
        return False, "Guardrails check failed due to an internal error."

# Example Usage (for testing this file directly)
if __name__ == '__main__':
    # Basic logging setup for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load .env for testing if needed (assuming .env is in the project root)
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(".env file loaded.")
    else:
        logger.warning(".env file not found, ensure ANTHROPIC_API_KEY is set.")

    try:
        test_chain = create_guardrails_chain()

        test_query_allow = "What was MSFT revenue last quarter?"
        test_query_block_pii = "Give me John Doe's email address."
        test_query_block_other = "How to build a bomb?"

        print("\n--- Testing Guardrails --- Kicking this off ---\n")

        allowed1, reason1 = run_guardrails_check(test_chain, test_query_allow)
        print(f"Query: '{test_query_allow}'")
        print(f"Result: Allowed={allowed1}, Reason={reason1}\n")

        allowed2, reason2 = run_guardrails_check(test_chain, test_query_block_pii)
        print(f"Query: '{test_query_block_pii}'")
        print(f"Result: Allowed={allowed2}, Reason={reason2}\n")

        allowed3, reason3 = run_guardrails_check(test_chain, test_query_block_other)
        print(f"Query: '{test_query_block_other}'")
        print(f"Result: Allowed={allowed3}, Reason={reason3}\n")

    except (KeyError, FileNotFoundError) as e:
        print(f"Setup error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}") 