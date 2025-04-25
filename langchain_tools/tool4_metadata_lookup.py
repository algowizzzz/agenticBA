"""
Tool 4: LLM-Driven Metadata Lookup Tool

Uses an LLM to analyze a query against a provided metadata context 
to identify relevant category and document IDs.
WARNING: Passing all metadata in the prompt is not scalable.
"""

import logging
import re
import json
import os
from typing import Dict, Any, List, Optional, Callable
from pymongo import MongoClient
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from .config import sanitize_json_response # Reverted to relative import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Connection --- 
def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping') # Test connection
        return client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None
    return client['earnings_transcripts']

# --- Metadata Fetching --- 
def fetch_all_metadata(db) -> Optional[Dict[str, Any]]:
    """Fetch category-to-doc mapping and doc-to-details mapping from 'transcripts' collection."""
    if db is None:
         return None
    try:
        categories = {}
        all_doc_ids = set()
        # Fetch category summaries
        for cat in db.category_summaries.find({}, {"_id": 0, "category_id": 1, "document_ids": 1}):
            cat_id = cat.get("category_id")
            doc_ids = cat.get("document_ids", [])
            if cat_id and doc_ids:
                 categories[cat_id] = doc_ids
                 all_doc_ids.update(doc_ids)
        
        documents = {}
        # Fetch document details from TRANSCRIPTS collection
        if all_doc_ids:
            all_doc_ids_list = [str(doc_id) for doc_id in all_doc_ids if doc_id is not None]
            if all_doc_ids_list:
                 logger.info(f"Fetching metadata from 'transcripts' for {len(all_doc_ids_list)} unique document IDs...")
                 # Use 'document_id' field for matching, fetch needed metadata fields
                 for doc in db.transcripts.find({"document_id": {"$in": all_doc_ids_list}},
                                             {"document_id": 1, "date": 1, "filename": 1, "quarter": 1, "fiscal_year": 1}): 
                    doc_id_str = doc.get("document_id") # Use document_id (UUID string) as the key
                    if doc_id_str:
                        details = {}
                        if doc.get("date"):
                            doc_date = doc["date"]
                            if isinstance(doc_date, datetime):
                                details["date"] = doc_date.strftime("%Y-%m-%d") 
                            elif isinstance(doc_date, str): 
                                 details["date"] = doc_date[:10] 
                        if doc.get("filename"):
                            details["filename"] = doc["filename"]
                        if doc.get("quarter") and doc.get("fiscal_year"):
                             details["quarter"] = f"Q{doc['quarter']} {doc['fiscal_year']}"
                        documents[doc_id_str] = details # Use document_id string as key
                    
        logger.info(f"Fetched details for {len(documents)} documents.")
        return {"categories": categories, "documents": documents}
        
    except Exception as e:
        logger.error(f"Failed to fetch metadata: {e}")
        return None

# --- LLM Prompt Formatting ---
def format_metadata_prompt(query: str, metadata: Dict[str, Any]) -> str:
    """Formats the prompt for the LLM metadata lookup (plain text output)."""
    # Convert metadata to strings for the prompt
    categories_str = json.dumps(metadata.get("categories", {}), indent=2)
    documents_str = json.dumps(metadata.get("documents", {}), indent=2)
    
    # Limit size to avoid exceeding context window (very basic truncation)
    max_len = 15000 # Adjust based on model context window and typical metadata size
    if len(categories_str) + len(documents_str) > max_len:
        ratio = len(categories_str) / (len(categories_str) + len(documents_str) + 1e-6)
        cat_limit = int(max_len * ratio)
        doc_limit = max_len - cat_limit
        categories_str = categories_str[:cat_limit] + "... (truncated)"
        documents_str = documents_str[:doc_limit] + "... (truncated)"
        logger.warning("Metadata truncated for prompt due to size limit.")
        
    # Modified prompt asking for single category name and multiple transcript names (up to 4)
    prompt_template = """You are a helpful assistant. Your task is to identify the single most relevant Category Name and up to 4 relevant Transcript Filenames based on a user query and provided metadata.

METADATA CONTEXT:

1. Category Mappings (Category ID -> List of associated Document IDs):
{categories_metadata}

2. Document Details (Document ID -> Details like date, filename, quarter):
{documents_metadata}

USER QUERY: {query}

Based ONLY on the User Query and the METADATA CONTEXT provided above:
1. Identify the SINGLE Category Name (e.g., company ticker like AMZN) that is most relevant to the query. If no single category is clearly relevant, return None.
2. Identify UP TO FOUR (0-4) Transcript Filenames (e.g., 2023-Oct-26-AMZN.txt) that are most relevant to the query. Prioritize transcripts matching any specified time periods (dates, quarters, years). If multiple transcripts are relevant, list the most relevant ones, up to a maximum of four.
3. If the query clearly points to one category or specific transcripts, return those.

Format your response as PLAIN TEXT with exactly two sections, one per line:
Category Name: [Single relevant Category Name or None]
Transcript Names: [Comma-separated list of 0-4 relevant Transcript Filenames, or None if none are relevant]

Example for multiple relevant transcripts:
Category Name: AMZN
Transcript Names: 2023-Oct-26-AMZN.txt, 2023-Jul-27-AMZN.txt

Example for no relevant transcripts:
Category Name: MSFT
Transcript Names: None

Example for no relevant category:
Category Name: None
Transcript Names: None

CRITICAL: Your response MUST contain ONLY the two lines starting with 'Category Name:' and 'Transcript Names:' with no other text, comments, or explanations.
"""

    return prompt_template.format(
        categories_metadata=categories_str,
        documents_metadata=documents_str,
        query=query
    )

# --- Main Tool Logic (LLM Based + Python Post-processing) --- 
def llm_metadata_lookup(query_term: str) -> Dict[str, Any]:
    """Uses an LLM to find relevant category name and transcript filenames based on metadata.
       Expects plain text output from LLM.
       Returns: {'category_name': str|None, 'transcript_names': List[str]|None, 'error': str|None}
    """
    db = init_db()
    metadata = fetch_all_metadata(db)
    
    # DEBUG: Print fetched metadata (optional)
    # logger.debug("--- Fetched Metadata for Tool4 Prompt --- ")
    # logger.debug(json.dumps(metadata, indent=2))
    # logger.debug("-----------------------------------------")
    
    if metadata is None:
        return {"category_name": None, "transcript_names": [], "error": "Failed to fetch metadata"}
        
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
         return {"category_name": None, "transcript_names": [], "error": "ANTHROPIC_API_KEY not set"}
         
    final_category_name = None
    final_transcript_names = []
    error_msg = None

    try:
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620", 
            temperature=0,
            max_tokens=500, # Adjusted for potentially longer list
            anthropic_api_key=api_key
        )
        
        prompt = format_metadata_prompt(query_term, metadata)
        response = llm.invoke(prompt)
        raw_llm_output = response.content.strip()
        
        # --- Parse plain text output using Regex --- 
        logger.debug(f"Raw LLM output from metadata tool: {repr(raw_llm_output)}")
        llm_category_name = None
        llm_transcript_names_raw = None # Store the raw string first
        
        # Parse for Category Name
        cat_match = re.search(r"Category Name:(.*?)(?:Transcript Names:|$)", raw_llm_output, re.DOTALL | re.IGNORECASE)
        if cat_match:
            parsed_cat_name = cat_match.group(1).strip()
            if parsed_cat_name.lower() != 'none':
                llm_category_name = parsed_cat_name

        # Parse for Transcript Names (comma-separated string)
        doc_match = re.search(r"Transcript Names:(.*)", raw_llm_output, re.DOTALL | re.IGNORECASE)
        if doc_match:
            llm_transcript_names_raw = doc_match.group(1).strip()

        # --- Process and Validate Names --- 
        valid_categories = metadata.get("categories", {}).keys()
        valid_filenames = {details.get("filename") for details in metadata.get("documents", {}).values() if details.get("filename")}

        # Validate Category Name
        if llm_category_name and llm_category_name in valid_categories:
            final_category_name = llm_category_name
        elif llm_category_name:
            logger.warning(f"LLM returned category name '{llm_category_name}' not found in metadata. Setting to None.")
        
        # Validate Transcript Names
        if llm_transcript_names_raw and llm_transcript_names_raw.lower() != 'none':
            potential_names = [name.strip() for name in llm_transcript_names_raw.split(',') if name.strip()]
            for name in potential_names:
                if name in valid_filenames:
                    if len(final_transcript_names) < 4: # Enforce max limit
                         final_transcript_names.append(name)
                    else:
                         logger.warning(f"LLM returned more than 4 valid transcript names. Truncating list after {name}.")
                         break # Stop adding after 4
                else:
                    logger.warning(f"LLM returned transcript name '{name}' not found in metadata. Skipping.")
        
        # Ensure final_transcript_names is a list, even if empty
        if not isinstance(final_transcript_names, list):
            final_transcript_names = []

        logger.info(f"Metadata lookup found category: {final_category_name}, transcripts: {final_transcript_names}")

    except Exception as e:
        logger.error(f"Error during LLM metadata lookup / post-processing: {e}")
        error_msg = f"Processing Error: {str(e)}"
        # Ensure error is returned in standard structure
        return {
            "category_name": None, 
            "transcript_names": [], # Return empty list on error 
            "error": error_msg
        }

    # Return validated/processed names
    return {
         "category_name": final_category_name, 
         "transcript_names": final_transcript_names, # This is now a list
         "error": error_msg # Will be None if no error
    }

# --- Tool Factory Function --- 
def get_tool() -> Callable:
    """Factory function to create and return the LLM metadata lookup tool."""
    tool_func = llm_metadata_lookup
    tool_func.__name__ = "metadata_lookup_tool"
    # Updated docstring to reflect new output
    tool_func.__doc__ = (
        "Use this tool to find the single most relevant Category Name (e.g., company ticker) and a list of up to 4 relevant Transcript Filenames "
        "based on a natural language query or term. Analyzes the query against available metadata (categories, filenames, dates). "
        "Input is the user query or specific term. Output includes 'category_name' (string or None) and 'transcript_names' (list of 0-4 strings)."
    )
    return tool_func

# Example Usage (for testing)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM-based Metadata Lookup.")
    parser.add_argument("query_term", help="Natural language query or term to search for.")
    args = parser.parse_args()
    
    result = llm_metadata_lookup(args.query_term)
    print(json.dumps(result, indent=2)) 