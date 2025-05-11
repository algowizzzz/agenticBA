#!/usr/bin/env python3
"""
CategorySearch Tool: Maps a user query to relevant ticker symbols.

This tool uses an LLM to analyze a query and identify which company tickers
are most relevant to the user's question, returning the results as a comma-separated list.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from langchain_anthropic import ChatAnthropic

# Import the category mappings
from langchain_tools.category_id_mapping import TICKER_TO_UUID, UUID_TO_TICKER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def category_search(query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Map a user query to relevant ticker symbols.
    
    Args:
        query: The user's natural language query
        api_key: Optional Anthropic API key (uses environment variable if not provided)
        
    Returns:
        Dict with identified tickers and explanation
    """
    # Get all available tickers
    available_tickers = list(TICKER_TO_UUID.keys())
    
    # Log the search attempt
    log_query = query[:100] + "..." if len(query) > 100 else query
    logger.info(f"Category Search Tool: Processing query: '{log_query}'")
    
    # Get API key from environment if not provided
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Category Search Tool: No API key provided or found in environment")
        return {
            "tickers": "",
            "explanation": "No API key configured.",
            "error": "API Key missing"
        }
    
    # Construct the prompt for the LLM
    prompt = f"""You are a financial analysis assistant. Your task is to identify which company ticker symbols are relevant to the following query.

Available ticker symbols:
{', '.join(available_tickers)}

User query: {query}

Instructions:
1. Identify all ticker symbols that are explicitly mentioned in the query.
2. Identify any companies that are mentioned by name (e.g., "Apple" = AAPL, "Microsoft" = MSFT, "Google" = GOOGL).
3. If the query implies a comparison or analysis of multiple companies, identify all relevant companies.
4. Only include tickers from the available list provided above.

Format your response as follows:
1. A comma-separated list of relevant ticker symbols (no spaces after commas)
2. A brief explanation of why you selected these tickers

Format:
Tickers: TICKER1,TICKER2,TICKER3
Explanation: Brief explanation of your selection process.

Response:
"""
    
    try:
        # Call the LLM
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            max_tokens=500,
            anthropic_api_key=api_key
        )
        
        response = llm.invoke(prompt)
        
        # Extract the content
        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
        
        # Extract tickers and explanation
        tickers_line = ""
        explanation = ""
        
        for line in content.split('\n'):
            if line.lower().startswith("tickers:"):
                tickers_line = line[8:].strip()
            elif line.lower().startswith("explanation:"):
                explanation = line[12:].strip()
        
        # Clean and validate tickers
        tickers_list = [t.strip().upper() for t in tickers_line.split(',')]
        valid_tickers = [t for t in tickers_list if t in available_tickers]
        
        if not valid_tickers:
            logger.warning(f"Category Search Tool: No valid tickers found in response: {tickers_line}")
            return {
                "tickers": "",
                "explanation": "Could not identify any relevant tickers for this query.",
                "error": None
            }
        
        # Return the final result
        result_tickers = ",".join(valid_tickers)
        logger.info(f"Category Search Tool: Identified tickers: {result_tickers}")
        
        return {
            "tickers": result_tickers,
            "explanation": explanation,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Category Search Tool: Error during processing: {e}")
        return {
            "tickers": "",
            "explanation": "An error occurred while identifying relevant tickers.",
            "error": str(e)
        }

def get_category_search_tool():
    """Return the category search tool function."""
    return category_search

# For direct testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python category_search_tool.py 'Your query here'")
        sys.exit(1)
    
    test_query = sys.argv[1]
    result = category_search(test_query)
    
    print(f"\nQuery: {test_query}")
    print("\nIdentified Tickers:")
    print(result["tickers"] or "None")
    print("\nExplanation:")
    print(result["explanation"])
    
    if result["error"]:
        print("\nError:")
        print(result["error"]) 