#!/usr/bin/env python3
"""
Tool: Full Document Analysis Tool

Analyzes a single full document transcript to answer a query.
Supports chunking for large documents with pagination.
"""

import logging
import os
from typing import Dict, Any, Callable, Optional
from langchain_anthropic import ChatAnthropic

# Import shared utilities
from langchain_tools.earnings_analysis_utils import (
    init_db, get_document_full_text, get_document_metadata, chunk_document_text
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_full_document(query: str, document_id: str, chunk_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze a full document transcript to answer a query.
    Supports chunking for large documents with pagination.
    
    Args:
        query: User query to answer
        document_id: Document ID to analyze
        chunk_index: Optional index of chunk to analyze (for large documents)
        
    Returns:
        Dict with answer and metadata including document size and chunking info
    """
    log_query = query[:100] + "..." if len(query) > 100 else query
    logger.info(f"Full Document Analysis Tool: Called with query: '{log_query}' for document: {document_id}")
    
    # Initialize DB connection
    db, transcripts_coll, summaries_coll = init_db()
    if db is None:
        return {"answer": "Error: Database connection failed.", "error": "DB Connection Error"}
    
    # Get document metadata
    metadata = get_document_metadata(transcripts_coll, document_id)
    if "error" in metadata:
        return {"answer": f"Error: {metadata['error']}", "error": metadata['error']}
    
    # Get full document text
    full_text, error = get_document_full_text(transcripts_coll, document_id)
    if error:
        return {"answer": f"Error: {error}", "error": error}
    
    if not full_text:
        return {"answer": f"No content found for document ID: {document_id}", "error": "Content not found"}
    
    # Split into chunks if large
    CHUNK_SIZE = 80000  # Suitable size for Claude
    chunks = chunk_document_text(full_text, CHUNK_SIZE)
    
    if not chunks:
        return {"answer": f"Error: Failed to chunk document content", "error": "Chunking failed"}
    
    # Set default chunk if not specified
    if chunk_index is None:
        chunk_index = 0
    
    # Validate chunk index
    if chunk_index < 0 or chunk_index >= len(chunks):
        return {
            "answer": f"Error: Invalid chunk index {chunk_index}. Document has {len(chunks)} chunks (0-{len(chunks)-1}).",
            "error": "Invalid chunk index",
            "total_chunks": len(chunks)
        }
    
    # Get the specified chunk
    chunk_content = chunks[chunk_index]
    
    # Construct prompt
    chunk_info = f"(Chunk {chunk_index+1} of {len(chunks)})" if len(chunks) > 1 else ""
    prompt = f"""Analyze this document transcript {chunk_info} to answer the user's query.
Base your answer ONLY on the information in this document.

QUERY: {query}

DOCUMENT: {metadata.get('document_name', f'Document {document_id}')}

CONTENT:
{chunk_content}

Answer:"""

    # Call LLM
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("Full Document Analysis Tool: Anthropic API Key not found.")
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
        
        # Add information about document chunking to help agent
        has_more = chunk_index < len(chunks) - 1
        
        return {
            "answer": llm_answer,
            "error": None,
            "document_id": document_id,
            "document_name": metadata.get("document_name", "Unknown"),
            "current_chunk": chunk_index,
            "total_chunks": len(chunks),
            "has_more_chunks": has_more,
            "next_chunk": chunk_index + 1 if has_more else None
        }
        
    except Exception as e:
        logger.error(f"Full Document Analysis Tool: Error during LLM call: {e}", exc_info=True)
        return {
            "answer": f"Error analyzing document: {str(e)}",
            "error": str(e),
            "document_id": document_id
        }

def get_full_document_analysis_tool() -> Callable:
    """Factory function to create and return the full document analysis tool."""
    tool_func = analyze_full_document
    tool_func.__name__ = "full_document_analysis_tool"
    tool_func.__doc__ = (
        "Use this tool to analyze a full document transcript when summaries aren't sufficient. "
        "It supports chunking for large documents and will indicate if more chunks are available. "
        "Input requires a query, document ID, and optional chunk index. "
        "Use this when you need detailed information not found in summaries."
    )
    return tool_func

# For testing
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python full_document_analysis_tool.py 'query' 'document_id' [chunk_index]")
        sys.exit(1)
    
    test_query = sys.argv[1]
    test_doc_id = sys.argv[2]
    test_chunk = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print(f"Testing Full Document Analysis Tool with:")
    print(f"Query: {test_query}")
    print(f"Document ID: {test_doc_id}")
    print(f"Chunk Index: {test_chunk}")
    
    result = analyze_full_document(test_query, test_doc_id, test_chunk)
    print("\n--- Full Document Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("------------------------------------------") 