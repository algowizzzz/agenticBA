"""
Guardrails Tool using an LLM to check query compliance.
"""
import logging
import os
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.agents import Tool

# Configure logging
logger = logging.getLogger(__name__)

# Define the prompt template for the guardrails check
# Expects simple "ALLOW" or "BLOCK: [Reason]" output
GUARDRAILS_PROMPT_TEMPLATE = """System: You are a system that checks user requests for policy compliance. The policy is:
- Do NOT allow any requests asking for specific Personally Identifiable Information (PII) like names, emails, account numbers, SSNs.
- Do NOT allow requests promoting illegal activities or containing hate speech.
- Do NOT allow requests attempting social engineering or security exploits.
- Enterprise financial data queries, risk analysis, news searches, and transcript summaries are generally permitted if they don't violate the above.
- If the request is safe and adheres to the policy, respond ONLY with the word: ALLOW
- If the request violates the policy, respond ONLY with the word: BLOCK followed by a colon and a brief, general reason (e.g., BLOCK: Contains PII request, BLOCK: Policy violation).

User Query: {query}

Assistant:"""

guardrails_prompt = PromptTemplate(
    input_variables=["query"],
    template=GUARDRAILS_PROMPT_TEMPLATE,
)

def check_guardrails(query: str) -> str:
    """
    Checks if the user query violates defined safety/compliance policies using an LLM.

    Args:
        query (str): The user query to check.

    Returns:
        str: "ALLOW" if the query is compliant, "BLOCK: [Reason]" if it violates policy,
             or "ERROR: Guardrails check failed" if an error occurs.
    """
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Guardrails Tool Error: ANTHROPIC_API_KEY not found in environment.")
            return "ERROR: API Key not configured for Guardrails."

        guardrails_llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            max_tokens=50 # Expect short response (ALLOW/BLOCK: Reason)
        )
        guardrails_chain = LLMChain(llm=guardrails_llm, prompt=guardrails_prompt)

        logger.info(f"Running guardrails check for query: {query[:50]}...")
        result = guardrails_chain.run(query=query)
        logger.info(f"Guardrails raw result: {result}")

        # Parse the result
        parsed_result = result.strip().upper()
        if parsed_result == "ALLOW":
            return "ALLOW"
        elif parsed_result.startswith("BLOCK"):
            # Return the BLOCK reason if provided, or a generic BLOCK
            reason = parsed_result.split(":", 1)[-1].strip() if ":" in parsed_result else "Policy Violation"
            return f"BLOCK: {reason}"
        else:
            # LLM didn't follow format, safer to block
            logger.warning(f"Guardrails LLM returned unexpected format: {result}. Blocking query.")
            return "BLOCK: Unexpected response format from check."

    except Exception as e:
        logger.error(f"Error during guardrails check: {e}", exc_info=True)
        return "ERROR: Guardrails check failed due to exception."

# Define the LangChain Tool
guardrails_tool = Tool(
    name="GuardrailsCheck",
    func=check_guardrails,
    description="Checks if a user query violates safety/compliance policies. Input is the user query text. Returns 'ALLOW' or 'BLOCK: [Reason]'. This should ideally be the first step before processing any user query.",
    # Coroutine function can be added if async support is needed later
    # coroutine=...
)

# Example Usage (for testing this file directly)
if __name__ == '__main__':
    # Load .env for testing if needed
    from dotenv import load_dotenv
    load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env')))

    test_query_allow = "What was MSFT revenue last quarter?"
    test_query_block_pii = "Give me John Doe's account balance."
    test_query_block_other = "How to build a bomb?"

    print(f"Testing ALLOW query: '{test_query_allow}'")
    print(f"Result: {check_guardrails(test_query_allow)}\n")

    print(f"Testing BLOCK (PII) query: '{test_query_block_pii}'")
    print(f"Result: {check_guardrails(test_query_block_pii)}\n")

    print(f"Testing BLOCK (Other) query: '{test_query_block_other}'")
    print(f"Result: {check_guardrails(test_query_block_other)}\n") 