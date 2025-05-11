# Wrapper for financial news search
import logging
import os
import json
import sys
import datetime

# Try to add the root directory to path so we can import from agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# First try to import dotenv with error handling
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    logger = logging.getLogger(__name__)
    logger.warning("python-dotenv package not found. Environment variables will not be loaded from .env file.")

try:
    # Import BasicAgent from the root directory
    from basic_agent import BasicAgent
    HAS_AGENT = True
    logger = logging.getLogger(__name__)
    logger.info("Successfully imported BasicAgent")
except ImportError as e:
    HAS_AGENT = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import BasicAgent: {e}")

def get_mock_news_data():
    """Load mock news data from JSON file."""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'mock_news_data.json')
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading mock news data: {e}")
        return {
            "entries": [
                {
                    "title": "Error Loading News Database",
                    "source": "System",
                    "date": datetime.datetime.now().strftime("%B %d, %Y"),
                    "overview": "The mock news database could not be loaded. Please check the JSON file format and path.",
                    "link": "https://example.com/error"
                }
            ]
        }

def format_fallback_response(query):
    """Generate a fallback response when LLM is not available."""
    data = get_mock_news_data()
    
    # Look for any articles with keywords that match parts of the query
    query_terms = query.lower().split()
    relevant_articles = []
    
    for entry in data.get("entries", []):
        keywords = entry.get("keywords", [])
        if any(term in keywords or 
               any(term in keyword.lower() for keyword in keywords) 
               for term in query_terms if len(term) > 3):
            relevant_articles.append(entry)
    
    if not relevant_articles:
        # If no matches, take the first 3 articles
        relevant_articles = data.get("entries", [])[:3]
    
    # Format a simple response
    response_parts = ["# Financial News Report\n"]
    response_parts.append(f"## Query: {query}\n")
    
    if not relevant_articles:
        response_parts.append("No relevant financial news found for this query.")
    else:
        response_parts.append("## Relevant Articles\n")
        for article in relevant_articles[:5]:  # Limit to 5 articles
            response_parts.append(f"### {article.get('title')}")
            response_parts.append(f"**Source:** {article.get('source')} | **Date:** {article.get('date')}")
            response_parts.append(f"**Overview:** {article.get('overview')}")
            response_parts.append(f"**Link:** {article.get('link')}\n")
    
    return "\n".join(response_parts)

def run_financial_news_search(query: str, json_mode=False, json_file_path=None) -> str:
    """
    Generate a financial news report based on the query using the LLM.
    Simply sends the news data and query to the LLM and returns the response.
    
    Args:
        query (str): The search query
        json_mode (bool): Whether to use JSON file as data source
        json_file_path (str): Optional path to specific JSON file
        
    Returns:
        str: Formatted news report
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating financial news report for query: {query}")
    
    # Get the mock news data
    data = get_mock_news_data()
    
    # If we have access to the BasicAgent, use it to generate a report
    if HAS_AGENT:
        try:
            agent = BasicAgent()
            logger.info("Created BasicAgent instance")
            
            prompt = f"""As a financial news analyst, create a concise but comprehensive report based on the following query and available news data.

QUERY: {query}

NEWS DATA:
{json.dumps(data, indent=2)}

Your task:
1. Identify the most relevant articles that address the query
2. Provide a summary analysis of the key insights
3. Format as a professional report with clear sections
4. Include relevant financial details, trends, and implications
5. Only reference information contained in the provided articles

Format your response as Markdown with appropriate headings and structure."""
            
            # Get response from LLM
            logger.info("Calling BasicAgent.query()")
            response = agent.query(prompt)
            logger.info(f"Successfully generated news report using LLM")
            return response
        
        except Exception as e:
            logger.error(f"Error generating report with LLM: {e}")
            return format_fallback_response(query)
    else:
        logger.warning("BasicAgent not available. Using fallback response.")
        return format_fallback_response(query) 