#!/usr/bin/env python3
"""
Tool 5: Document Content Analysis Tool (Prioritizes Summaries)

Takes a user query string and a mandatory document ID.
Fetches the pre-computed summary for the document ID if available.
If no summary exists, fetches the full transcript text.
Uses an LLM to answer the query based *only* on the fetched content (summary or full text).
Returns the plain text response.
"""

import logging
import os
import json
import sys
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
        logger.info("Analysis Tool: MongoDB connection successful.")
        return client
    except Exception as e:
        logger.error(f"Analysis Tool: MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None, None, None # Indicate failure
    db = client['earnings_transcripts']
    return db, db.transcripts, db.document_summaries # Return handles to collections

# --- Document/Summary Fetching by document_id ---
def get_content_by_document_id(transcripts_coll, summaries_coll, document_id: str) -> tuple[Optional[str], str, Optional[str]]:
    """Retrieve content for a document ID. Prioritizes summary, falls back to transcript.
       Returns: (content_text, content_type, error_message)
       content_type is 'summary' or 'transcript'.
    """
    if not document_id:
        return None, "unknown", "Document ID is missing."

    content_text = None
    content_type = "unknown"
    error_msg = None

    # 1. Try fetching the summary
    try:
        logger.info(f"Analysis Tool: Attempting to fetch summary for document_id: {document_id}")
        summary_doc = summaries_coll.find_one({"document_id": document_id})
        if summary_doc and summary_doc.get("summary_text"):
            content_text = summary_doc["summary_text"]
            content_type = "summary"
            logger.info(f"Analysis Tool: Found and using summary for document_id: {document_id}")
        else:
            logger.info(f"Analysis Tool: No summary found for document_id: {document_id}. Attempting to fetch full transcript.")
    except Exception as e:
        logger.warning(f"Analysis Tool: Error fetching summary for {document_id}: {e}. Attempting transcript.")
        # Continue to fetching transcript

    # 2. If no summary found, try fetching the transcript
    if content_text is None:
        try:
            transcript_doc = transcripts_coll.find_one({"document_id": document_id})
            if transcript_doc and transcript_doc.get("transcript_text"):
                content_text = transcript_doc["transcript_text"]
                content_type = "transcript"
                logger.info(f"Analysis Tool: Found and using full transcript for document_id: {document_id}")
            else:
                logger.error(f"Analysis Tool: Neither summary nor transcript found for document_id: {document_id}")
                error_msg = f"Document content not found for ID: {document_id}"
        except Exception as e:
            logger.error(f"Analysis Tool: Error fetching transcript for {document_id}: {e}")
            error_msg = f"Error fetching document content for ID: {document_id}: {e}"

    return content_text, content_type, error_msg


# --- Main Tool Logic (Renamed and Adjusted) ---
def analyze_document_content(query: str, document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calls the LLM with the user query, using the specified document's summary (if available)
    or full transcript as context.
    The document_id is now required.
    """
    log_query = query[:100] + "..." if len(query) > 100 else query

    if not document_id:
        logger.error(f"Analysis Tool called without a document_id for query: '{log_query}'")
        return {"answer": "Error: This tool requires a 'document_id' parameter.", "error": "Missing document_id"}

    logger.info(f"Analysis Tool called with query: '{log_query}' and document_id: '{document_id}'")
    db, transcripts_coll, summaries_coll = init_db()

    if db is None:
         return {"answer": "Error: Database connection failed.", "error": "DB Connection Error"}

    # Fetch content (prioritizes summary)
    content_text, content_type, fetch_error = get_content_by_document_id(transcripts_coll, summaries_coll, document_id)

    if fetch_error:
        logger.error(f"Analysis Tool: {fetch_error}")
        return {"answer": f"Error: {fetch_error}", "error": fetch_error}

    if not content_text:
        # This case should be caught by fetch_error, but as a safeguard
        logger.error(f"Analysis Tool: No content available for document_id: {document_id}")
        return {"answer": f"Error: No content found for document ID: {document_id}", "error": "Content unavailable"}

    # Truncate long content (especially full transcripts) to avoid overly long prompts
    # Consider smarter chunking/summarization for production if needed
    MAX_CONTEXT_LEN = 100000 # Generous limit for Claude 3.5 Sonnet
    truncated_content = content_text
    if len(content_text) > MAX_CONTEXT_LEN:
        truncated_content = content_text[:MAX_CONTEXT_LEN] + "... [CONTENT TRUNCATED]"
        logger.warning(f"Analysis Tool: Content for {document_id} (type: {content_type}) was truncated to {MAX_CONTEXT_LEN} characters.")

    # Construct context-aware prompt indicating source type
    prompt_context_desc = f"summary of an earnings call" if content_type == "summary" else f"full earnings call transcript"
    prompt = f"""Analyze the following document context (a {prompt_context_desc}) to answer the user's query.
Base your answer *only* on the provided document context.
If the document context does not contain the information to answer the query, state that clearly.
Do not use any external knowledge.

QUERY: {query}

DOCUMENT CONTEXT (Document ID: {document_id}, Type: {content_type}):
{truncated_content}

Answer:"""
    logger.info(f"Analysis Tool: Using {content_type} context from {document_id} for LLM prompt.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Analysis Tool: Anthropic API Key not found in environment variables.")
        return {"answer": "API Key not configured. Please set the ANTHROPIC_API_KEY environment variable.", "error": "API Key missing"}
    
    # Log API key length and first/last few characters for debugging (without revealing the full key)
    logger.info(f"Analysis Tool: Found API key in environment (length: {len(api_key)}, starts with: {api_key[:5]}..., ends with: ...{api_key[-5:]})")

    try:
        logger.info("Analysis Tool: Initializing ChatAnthropic with model: claude-3-5-sonnet-20240620")
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620", # Or load from config
            temperature=0.1,
            max_tokens=1500, # Max output tokens for the answer
            anthropic_api_key=api_key
        )
        logger.info("Analysis Tool: ChatAnthropic initialized successfully")

        logger.info("Analysis Tool: Sending prompt to model...")
        response = llm.invoke(prompt)
        logger.info(f"Analysis Tool: Received response of type: {type(response)}")
        
        # Handle different response formats (string vs AIMessage object)
        if isinstance(response, str):
            llm_answer = response.strip()
            logger.info("Analysis Tool: Response is a string")
        elif hasattr(response, 'content'):
            logger.info(f"Analysis Tool: Response has 'content' attribute of type: {type(response.content)}")
            # Handle if content is a string
            if isinstance(response.content, str):
                llm_answer = response.content.strip()
            # Handle if content is a list of message parts
            elif isinstance(response.content, list) and len(response.content) > 0:
                logger.info(f"Analysis Tool: Response content is a list with {len(response.content)} items")
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
            logger.warning(f"Analysis Tool: Unknown response format received: {type(response)}")
            llm_answer = str(response).strip()
        
        logger.info(f"Analysis Tool: Successfully extracted answer of length {len(llm_answer)} chars")
        
        return {"answer": llm_answer, "error": None}

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Enhanced error logging
        logger.error(f"Analysis Tool: {error_type} during LLM call for {document_id}: {error_msg}", exc_info=True)
        
        # Specific handling for authentication errors
        if "authentication" in error_msg.lower() or "401" in error_msg or "api key" in error_msg.lower():
            detailed_error = f"Authentication error with Anthropic API. Please check that your API key is valid and correctly formatted. Error details: {error_msg}"
            logger.critical(f"Analysis Tool: API KEY AUTHENTICATION ERROR: {detailed_error}")
            return {
                "answer": "Failed to process your query due to an authentication error with the AI service. Please contact support with reference code: AUTH-401.", 
                "error": detailed_error
            }
        
        # General error handling
        return {
            "answer": f"An error occurred while processing your query: {error_type}. Please try again later or contact support if the issue persists.", 
            "error": f"{error_type}: {error_msg}"
        }

# --- Tool Factory Function (Renamed and updated docstring) ---
def get_document_analysis_tool(api_key: Optional[str] = None) -> Callable:
    """Factory function to create and return the document content analysis tool.
       Prioritizes using pre-computed summaries if available.
    """
    # Set API key in environment if provided
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        logger.info(f"Document Analysis Tool: Set API key from parameter (length: {len(api_key)})")
    else:
        existing_key = os.getenv("ANTHROPIC_API_KEY")
        if existing_key:
            logger.info(f"Document Analysis Tool: Using existing API key from environment (length: {len(existing_key)})")
        else:
            logger.warning("Document Analysis Tool: No API key provided or found in environment")
    
    tool_func = analyze_document_content
    tool_func.__name__ = "document_content_analysis_tool" # Keep name consistent if needed, or rename
    tool_func.__doc__ = (
        "Use this tool to analyze the content of a specific document (identified by document_id) "
        "to answer a detailed question. It will prioritize using a pre-computed summary if one exists, "
        "falling back to the full transcript text if needed. Returns a concise answer based only on "
        "the document content."
    )
    
    return tool_func

# --- Example Usage (Updated help text and tool call) ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Document Content Analysis Tool (Prioritizes Summaries)")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    # Use document_id now
    parser.add_argument("-id", "--document_id", required=True, help="Document ID (UUID) to analyze.")
    args = parser.parse_args()

    print(f"INFO:__main__:Testing Document Analysis Tool with Query: '{args.query}' and Document ID: '{args.document_id}'")
    # Call the renamed tool run function
    result = analyze_document_content(args.query, args.document_id)
    print("\n--- Document Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("---------------------------------------") 