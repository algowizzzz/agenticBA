#!/usr/bin/env python3
"""
Tool: Document Summaries Analysis Tool

Analyzes multiple document summaries (up to 5) in a single call.
Provides a comprehensive answer based on all provided summaries.
"""

import logging
import os
from typing import Dict, Any, List, Callable, Optional
from langchain_anthropic import ChatAnthropic

# Import shared utilities
from langchain_tools.earnings_analysis_utils import (
    init_db, get_document_summary, get_document_metadata
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_document_summaries(query: str, document_ids: List[str]) -> Dict[str, Any]:
    """
    Analyze multiple document summaries to answer a query.
    
    Args:
        query: User query to answer
        document_ids: List of document IDs (up to 5)
        
    Returns:
        Dict with answer and metadata
    """
    log_query = query[:100] + "..." if len(query) > 100 else query
    logger.info(f"Summary Analysis Tool: Called with query: '{log_query}' and {len(document_ids)} document(s)")
    
    # Limit to 5 documents to prevent context window issues
    if len(document_ids) > 5:
        logger.warning(f"Summary Analysis Tool: Limiting analysis to first 5 of {len(document_ids)} documents")
        document_ids = document_ids[:5]
    
    # Initialize DB connection
    db, transcripts_coll, summaries_coll = init_db()
    if db is None:
        return {"answer": "Error: Database connection failed.", "error": "DB Connection Error"}
    
    # Fetch summaries for all document IDs
    document_summaries = []
    document_metadata = []
    
    for doc_id in document_ids:
        # Try to get summary for this document
        summary_content, error = get_document_summary(summaries_coll, doc_id)
        
        if summary_content:
            metadata = get_document_metadata(transcripts_coll, doc_id)
            document_summaries.append({
                "document_id": doc_id,
                "content": summary_content,
                "metadata": metadata
            })
            document_metadata.append(metadata)
        else:
            logger.warning(f"Summary Analysis Tool: No summary found for document ID: {doc_id}")
    
    if not document_summaries:
        return {
            "answer": "No summaries found for the provided document IDs.",
            "error": "No summaries available",
            "documents_analyzed": document_ids
        }
    
    # Construct prompt with multiple document summaries
    prompt = f"""Analyze the following document summaries to answer the user's query.
Base your answer ONLY on the information in these summaries.
If more detailed information is needed that might be in the full documents, state this clearly.

QUERY: {query}

"""
    # Add each document summary to the prompt
    for i, doc in enumerate(document_summaries):
        metadata = doc["metadata"]
        prompt += f"""
DOCUMENT {i+1}: {metadata.get('document_name', f'Document {doc["document_id"]}')}
{doc["content"]}

"""
    
    prompt += """
Answer:"""

    # Call LLM with the prompt
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Summary Analysis Tool: Anthropic API Key not found.")
            return {"answer": "API Key not configured.", "error": "API Key missing"}
            
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307", 
            temperature=0.1,
            max_tokens=1500,
            anthropic_api_key=api_key
        )
        
        response = llm.invoke(prompt)
        
        # Handle different response formats
        if isinstance(response, str):
            llm_answer = response.strip()
        elif hasattr(response, 'content'):
            # Handle if content is a string
            if isinstance(response.content, str):
                llm_answer = response.content.strip()
            # Handle if content is a list of message parts
            elif isinstance(response.content, list) and len(response.content) > 0:
                if hasattr(response.content[0], 'text'):
                    llm_answer = response.content[0].text.strip()
                elif isinstance(response.content[0], dict) and 'text' in response.content[0]:
                    llm_answer = response.content[0]['text'].strip()
                else:
                    llm_answer = str(response.content[0]).strip()
            else:
                llm_answer = str(response.content).strip()
        else:
            # Fallback for unknown response format
            llm_answer = str(response).strip()
        
        return {
            "answer": llm_answer,
            "error": None,
            "documents_analyzed": [doc["document_id"] for doc in document_summaries],
            "document_metadata": document_metadata
        }
        
    except Exception as e:
        logger.error(f"Summary Analysis Tool: Error during LLM call: {e}", exc_info=True)
        return {
            "answer": f"Error analyzing document summaries: {str(e)}",
            "error": str(e),
            "documents_analyzed": [doc["document_id"] for doc in document_summaries]
        }

def get_document_summaries_analysis_tool() -> Callable:
    """Factory function to create and return the document summaries analysis tool."""
    tool_func = analyze_document_summaries
    tool_func.__name__ = "document_summaries_analysis_tool"
    tool_func.__doc__ = (
        "Use this tool to analyze multiple document summaries (up to 5) at once. "
        "It will provide a comprehensive answer based on the information from all summaries. "
        "Input requires a query and list of document IDs. "
        "Use this as your primary tool for document analysis."
    )
    return tool_func

# For testing
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python summaries_analysis_tool.py 'query' 'document_id1,document_id2,...'")
        sys.exit(1)
    
    test_query = sys.argv[1]
    test_doc_ids = sys.argv[2].split(',')
    
    print(f"Testing Summary Analysis Tool with:")
    print(f"Query: {test_query}")
    print(f"Document IDs: {test_doc_ids}")
    
    result = analyze_document_summaries(test_query, test_doc_ids)
    print("\n--- Summary Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("------------------------------------") 