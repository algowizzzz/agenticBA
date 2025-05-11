# Wrapper for financial news search
import logging
import os
import json
from typing import Union, List, Dict
import datetime
import re

logger = logging.getLogger(__name__)

class MockNewsProvider:
    """A mock provider that returns predefined news results."""
    
    def __init__(self):
        """Initialize the mock news provider by loading data from JSON file."""
        try:
            # Load mock news data from the JSON file
            json_path = os.path.join(os.path.dirname(__file__), 'mock_news_data.json')
            with open(json_path, 'r') as f:
                data = json.load(f)
                
            # Extract entries and keyword mappings
            self.news_database = {}
            
            # Build the database of news entries indexed by keywords
            for keyword, indices in data["keywords"].items():
                self.news_database[keyword] = []
                for idx in indices:
                    entry = data["entries"][idx]
                    # Format the entry to match the expected structure in the search method
                    news_item = {
                        "title": entry["title"],
                        "snippet": entry["overview"],
                        "link": entry["link"],
                        "source": entry["source"],
                        "date": entry["date"],
                        "full_content": entry["full_content"]
                    }
                    self.news_database[keyword].append(news_item)
                    
            logger.info(f"Successfully loaded mock news data with {len(data['entries'])} entries and {len(data['keywords'])} keyword mappings")
        except Exception as e:
            logger.error(f"Error loading mock news data: {e}")
            # Fallback to empty database in case of error
            self.news_database = {"default": [
                {
                    "title": "Error Loading News Database",
                    "snippet": "The mock news database could not be loaded. Please check the JSON file format and path.",
                    "link": "https://example.com/error",
                    "source": "System",
                    "date": datetime.datetime.now().strftime("%B %d, %Y")
                }
            ]}
    
    def search(self, query: str) -> List[Dict]:
        """Return mock news results based on the query keywords."""
        query = query.lower()
        results = []
        
        # Check for keywords in the mock database
        for key in self.news_database:
            if key in query:
                results.extend(self.news_database[key])
        
        # If no specific matches, return default news
        if not results and "default" in self.news_database:
            results = self.news_database["default"]
            
        return results

def format_news_results(results: List[Dict]) -> str:
    """
    Format news results into a readable string.
    
    Args:
        results (List[Dict]): List of news article dictionaries
        
    Returns:
        str: Formatted news results as a string
    """
    if not results:
        return "No financial news results found for the query."
    
    formatted_output = ["## Financial News Results", ""]
    
    for i, result in enumerate(results, 1):
        # Extract fields with safe defaults
        title = result.get("title", "No Title")
        snippet = result.get("snippet", "No description available.")
        link = result.get("link", "#")
        source = result.get("source", "Unknown Source")
        date = result.get("date", "Unknown Date")
        full_content = result.get("full_content", "")
        
        # Add article header with number, title, source, and date
        formatted_output.append(f"### {i}. {title}")
        formatted_output.append(f"**Source:** {source} | **Date:** {date}")
        formatted_output.append("")
        
        # Add snippet/overview
        formatted_output.append(f"**Overview:** {snippet}")
        formatted_output.append("")
        
        # Add link
        formatted_output.append(f"**Link:** {link}")
        formatted_output.append("")
        
        # Add full content if available
        if full_content:
            formatted_output.append("**Full Article:**")
            formatted_output.append(full_content)
            formatted_output.append("")
        
        # Add separator between articles
        if i < len(results):
            formatted_output.append("---")
            formatted_output.append("")
    
    return "\n".join(formatted_output)

def run_financial_news_search(query: str) -> str:
    """
    Search for financial news using the mock provider.
    
    Args:
        query (str): The search query
        
    Returns:
        str: Formatted news results
    """
    logger.info(f"Searching for financial news with query: {query}")
    
    # Create mock news provider
    provider = MockNewsProvider()
    
    # Execute the search
    try:
        results = provider.search(query)
        logger.info(f"Found {len(results)} news results for query: {query}")
        
        # Format the results
        formatted_results = format_news_results(results)
        return formatted_results
    except Exception as e:
        error_msg = f"Error searching for financial news: {str(e)}"
        logger.error(error_msg)
        return f"Failed to retrieve financial news: {error_msg}" 