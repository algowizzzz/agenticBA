# Wrapper for financial news search
import logging
import os
import json
from typing import Union, List, Dict
import datetime

# Assuming SerpAPIWrapper is the intended tool
# Handle potential ImportError
try:
    from langchain_community.utilities import SerpAPIWrapper
except ImportError:
    SerpAPIWrapper = None # Set to None if import fails

logger = logging.getLogger(__name__)

class MockNewsProvider:
    """Mock news provider that returns predefined financial news articles when SerpAPI is unavailable."""
    
    def __init__(self):
        self.today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Predefined news articles by topic
        self.news_database = {
            "apple": [
                {
                    "title": f"Apple's Smartwatch Strategy Evolves with Health Focus ({self.today})",
                    "snippet": "Apple continues to emphasize health features in its latest smartwatch offerings, with analysts predicting further expansion into medical-grade monitoring.",
                    "link": "https://example.com/apple-watch-health-focus",
                    "source": "Financial Times (Mock)",
                    "date": self.today
                },
                {
                    "title": f"Apple Watch Sales Exceed Expectations in Q2 ({self.today})",
                    "snippet": "Apple's wearable segment shows strong growth, driven primarily by increased Apple Watch adoption in healthcare and fitness markets.",
                    "link": "https://example.com/apple-watch-sales-q2",
                    "source": "Bloomberg (Mock)",
                    "date": self.today
                }
            ],
            "microsoft": [
                {
                    "title": f"Microsoft Cloud Revenue Soars on AI Integration ({self.today})",
                    "snippet": "Microsoft reports record cloud segment growth as Azure AI services gain traction among enterprise customers.",
                    "link": "https://example.com/microsoft-cloud-ai-growth",
                    "source": "Wall Street Journal (Mock)",
                    "date": self.today
                }
            ],
            "finance": [
                {
                    "title": f"Federal Reserve Signals Rate Changes ({self.today})",
                    "snippet": "Fed officials indicate potential shift in monetary policy as inflation data shows signs of moderation.",
                    "link": "https://example.com/fed-rate-outlook",
                    "source": "Reuters (Mock)",
                    "date": self.today
                }
            ],
            "default": [
                {
                    "title": f"Global Markets React to Economic Data ({self.today})",
                    "snippet": "Equity markets show mixed results as investors digest latest economic indicators and corporate earnings reports.",
                    "link": "https://example.com/markets-economic-data",
                    "source": "Financial News (Mock)",
                    "date": self.today
                }
            ]
        }
    
    def search(self, query: str) -> List[Dict]:
        """Return mock news results based on the query keywords."""
        query = query.lower()
        results = []
        
        # Check for keywords in the mock database
        for key in self.news_database:
            if key in query:
                results.extend(self.news_database[key])
        
        # If no specific matches, return default news
        if not results:
            results = self.news_database["default"]
            
        # Add mock disclaimer
        for result in results:
            result["snippet"] = f"{result['snippet']} [MOCK NEWS: Generated as SerpAPI fallback]"
            
        return results

def format_news_results(results: List[Dict]) -> str:
    """Format news results into a readable string with proper structure."""
    if not results:
        return "No news articles found."
        
    formatted = "# Financial News Results\n\n"
    
    for i, item in enumerate(results, 1):
        formatted += f"## {i}. {item.get('title', 'Untitled Article')}\n"
        formatted += f"**Source**: {item.get('source', 'Unknown')}\n"
        formatted += f"**Date**: {item.get('date', 'No date')}\n\n"
        formatted += f"{item.get('snippet', 'No description available')}\n\n"
        formatted += f"**Link**: {item.get('link', '#')}\n\n"
        formatted += "---\n\n"
    
    return formatted

def run_financial_news_search(query: str) -> str:
    """
    Performs a web search using the provided query and returns formatted results.
    Now includes a fallback to mock news when SerpAPI is unavailable.
    Returns results as a formatted string.
    """
    logger.info(f"[Financial News Tool] Executing web search for query: {query}")
    
    # Attempt to use SerpAPI first
    use_mock = False
    serpapi_results = []
    
    if SerpAPIWrapper is None:
        logger.warning("SerpAPIWrapper dependency not installed. Falling back to mock news provider.")
        use_mock = True
    else:
        serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        if not serpapi_api_key:
            logger.warning("SERPAPI_API_KEY environment variable not set. Falling back to mock news provider.")
            use_mock = True
        else:
            try:
                search = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)
                results = search.run(query)
                
                # Process SerpAPI results
                if isinstance(results, list):
                    serpapi_results = results
                elif isinstance(results, dict):
                    if 'organic_results' in results and results['organic_results']:
                        serpapi_results = results['organic_results']
                    else:
                        # Single result as a list
                        serpapi_results = [results]
                else:
                    # Convert string to a single result
                    serpapi_results = [{"snippet": str(results), "title": "Search Result", "link": "#"}]
                    
                logger.info(f"[Financial News Tool] Successfully retrieved {len(serpapi_results)} results from SerpAPI")
                
            except Exception as e:
                logger.error(f"[Financial News Tool] Error during web search: {e}", exc_info=True)
                use_mock = True
    
    # Use mock provider if needed
    if use_mock:
        logger.info("[Financial News Tool] Using mock news provider as fallback")
        mock_provider = MockNewsProvider()
        results = mock_provider.search(query)
        return format_news_results(results) + "\n[NOTE: These are mock results provided as a fallback since SerpAPI is unavailable]"
    
    # Format actual results
    return format_news_results(serpapi_results) 