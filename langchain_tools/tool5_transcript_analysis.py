#!/usr/bin/env python3
"""
Tool 5: Transcript Analysis Tool

Takes a user query string and a mandatory document filename (e.g., earnings transcript).
Fetches the document content and uses an LLM to answer the query based *only* on the document.
Returns the plain text response.
"""

import logging
import os
import json
from typing import Dict, Any, Optional, Callable
from langchain_anthropic import ChatAnthropic
from pymongo import MongoClient
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Connection --- 
def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')
        return client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None
    # Assumes transcript text is in the 'transcripts' collection
    return client['earnings_transcripts'] 

# --- Document Fetching by Filename ---
def get_document_by_filename(db, filename: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single document by its filename from the 'transcripts' collection."""
    if db is None or not filename:
        return None
    try:
        logger.info(f"Attempting to fetch document with filename: {filename}")
        # Assumes a 'filename' field exists and is indexed for performance
        document = db.transcripts.find_one({"filename": filename})
        if document:
            logger.info(f"Document found for filename: {filename}")
            return document
        else:
            logger.warning(f"No document found for filename: {filename}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving document by filename {filename}: {e}")
        return None

# --- Main Tool Logic (Renamed and Adjusted) ---
def transcript_analysis_tool_run(query: str, document_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Calls the LLM with the user query, using the specified document as context.
    The document_name is now expected and crucial for this tool.
    """
    log_query = query[:100] + "..." if len(query) > 100 else query

    if not document_name:
        logger.error(f"Transcript Analysis Tool called without a document_name for query: '{log_query}'")
        return {"answer": "Error: This tool requires a 'document_name' parameter.", "error": "Missing document_name"}

    logger.info(f"Transcript Analysis Tool called with query: '{log_query}' and document_name: '{document_name}'")
    db = init_db()
    document = get_document_by_filename(db, document_name)
    doc_found = False
    doc_content_snippet = f"Document '{document_name}' requested." # Initial status

    if document:
        doc_found = True
        transcript_text = document.get("transcript_text", "")
        # Truncate content to avoid overly long prompts
        # Consider smarter chunking/summarization for production
        MAX_CONTEXT_LEN = 10000 # Increased context slightly
        truncated_content = transcript_text[:MAX_CONTEXT_LEN]
        if len(transcript_text) > MAX_CONTEXT_LEN:
            truncated_content += "... [CONTENT TRUNCATED]"
        doc_content_snippet = truncated_content

        # Construct context-aware prompt specifically for transcript analysis
        prompt = f"""Analyze the following document context (an earnings call transcript) to answer the user's query.
        Base your answer *only* on the provided document context.
        If the document does not contain the information to answer the query, state that clearly.
        Do not use any external knowledge.

        QUERY: {query}

        DOCUMENT CONTEXT ({document_name}):
        {truncated_content}

        Answer:"""
        logger.info(f"Using document context from {document_name} for LLM prompt.")
    else:
        logger.warning(f"Document '{document_name}' not found. Cannot proceed with analysis.")
        return {"answer": f"Error: Document '{document_name}' not found in the database.", "error": f"Document not found: {document_name}"}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
         logger.error("Anthropic API Key not found in environment for Transcript Analysis Tool.")
         return {"answer": "API Key not configured.", "error": "API Key missing"}

    try:
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0.1,
            max_tokens=1500,
            anthropic_api_key=api_key
        )

        response = llm.invoke(prompt) # Send the context-specific prompt
        llm_answer = response.content.strip()
        logger.debug("Received plain text answer from transcript analysis LLM call.")

        # No need to add the "not found" note here as we return an error earlier if not found
        return {"answer": llm_answer, "error": None}

    except Exception as e:
        logger.error(f"Error during transcript analysis LLM call: {e}")
        return {"answer": f"An error occurred during LLM call for document {document_name}: {e}", "error": str(e)}

# --- Tool Factory Function (Renamed and updated docstring) ---
def get_transcript_analysis_tool(api_key: Optional[str] = None) -> Callable:
    """Factory function to create and return the transcript analysis tool."""
    # Note: api_key isn't directly used here as the tool run function gets it from env,
    # but kept for potential future configuration flexibility.
    tool_func = transcript_analysis_tool_run
    tool_func.__name__ = "transcript_analysis_tool"
    tool_func.__doc__ = (
        "Use this tool to analyze the content of a specific document (e.g., an earnings call transcript) to answer a detailed question. "
        "Input MUST be in the format: \"<query>, document_name=<filename.txt>\". "
        "The tool will fetch the document named <filename.txt> and use its content to answer the <query>."
        "Only use this tool when you need specific details from a known document."
    )
    return tool_func

# --- Example Usage (Updated help text and tool call) ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Transcript Analysis Tool Directly")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    # Document name is now required for direct testing of this specific tool's logic
    parser.add_argument("-n", "--doc_name", required=True, help="Document filename to analyze.")
    args = parser.parse_args()

    print(f"INFO:__main__:Testing Transcript Analysis Tool with Query: '{args.query}' and Document: '{args.doc_name}'")
    # Call the renamed tool run function
    result = transcript_analysis_tool_run(args.query, args.doc_name)
    print("\n--- Transcript Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("---------------------------------------") 