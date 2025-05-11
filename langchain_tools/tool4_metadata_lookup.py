"""
Tool 4: Semantic Search Metadata Lookup Tool

Uses semantic search against a pre-populated vector database (ChromaDB)
containing document metadata and summaries to identify relevant document IDs.
"""

import logging
import re
import json
import os
from typing import Dict, Any, List, Optional, Callable, Set
from pymongo import MongoClient # Need MongoDB access for setup
from datetime import datetime # May need for date handling
from langchain_anthropic import ChatAnthropic # Need for summary generation

# --- NEW IMPORTS --- 
import chromadb
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants --- 
# Assuming ChromaDB is running locally or using a persistent path
# Adjust path as needed
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db_persist")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "transcript_embeddings")
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
TOP_N_RESULTS = 5 # Configurable number of results to return
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") # Needed for summary LLM

# --- Initialize ChromaDB Client and Embedding Model (Global Scope) --- 
embedding_model = None
chroma_client = None
collection = None

def _initialize_resources():
    global embedding_model, chroma_client, collection
    if embedding_model is None:
        try:
            logger.info(f"Metadata Tool: Loading embedding model: {EMBEDDING_MODEL_NAME}")
            embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("Metadata Tool: Embedding model loaded.")
        except Exception as e:
            logger.error(f"Metadata Tool: Failed to load embedding model: {e}")
            embedding_model = None # Ensure it's None on failure

    if chroma_client is None:
        try:
            logger.info(f"Metadata Tool: Initializing ChromaDB client: {CHROMA_PERSIST_DIR}")
            chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            logger.info("Metadata Tool: ChromaDB client initialized.")
        except Exception as e:
            logger.error(f"Metadata Tool: Failed to initialize ChromaDB client: {e}")
            chroma_client = None # Ensure it's None on failure

    if collection is None and chroma_client:
        try:
            logger.info(f"Metadata Tool: Getting/creating ChromaDB collection: {COLLECTION_NAME}")
            collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
            logger.info(f"Metadata Tool: ChromaDB collection '{COLLECTION_NAME}' ready.")
        except Exception as e:
            logger.error(f"Metadata Tool: Failed to get/create ChromaDB collection: {e}")
            collection = None # Ensure it's None on failure

# Ensure resources are initialized when the module is loaded
# _initialize_resources() # Call this appropriately, maybe lazily on first use

# --- MongoDB Connection (Needed for setup) --- 
# def get_mongodb_client(): ... (Comment out or delete)

# --- TEMPORARY SETUP FUNCTION --- 
# def _generate_summaries_and_populate_vectordb(): ... (Comment out or delete)

# --- REMOVE OLD/COMMENTED CODE (Keep commented out as before) --- 
# ... (Old functions remain commented) ...

# --- NEW SEMANTIC SEARCH BASED LOGIC (Keep as is) --- 
def semantic_metadata_lookup(query_term: str) -> Dict[str, Any]:
    """Uses semantic search against a pre-populated ChromaDB vector database 
       to find relevant document IDs, their names, and category IDs.
       Returns: Dict with 'identified_documents' list or 'error'.
    """
    _initialize_resources() # Ensure resources are loaded

    if not embedding_model or not collection:
        logger.error("Metadata Tool: Resources not initialized.")
        return {"identified_documents": [], "error": "Tool initialization failed."}

    logger.info(f"Metadata Tool (Semantic): Received query: '{query_term[:100]}...'")
    try:
        query_embedding = embedding_model.encode(query_term).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_N_RESULTS,
            include=['metadatas'] # Only need metadata
        )

        identified_documents_details = []
        if results and results.get('ids') and results.get('metadatas'):
            logger.info(f"Metadata Tool (Semantic): Found {len(results['ids'][0])} matches.")
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'][0] and len(results['metadatas'][0]) > i else {}
                doc_detail = {
                    "document_id": doc_id,
                    "document_name": metadata.get("document_name", "Unknown Name"),
                    "category_id": metadata.get("category_id", "Unknown Category")
                }
                identified_documents_details.append(doc_detail)
        else:
             logger.warning(f"Metadata Tool (Semantic): No relevant documents found.")

        return {
            "identified_documents": identified_documents_details,
            "error": None
        }
    except Exception as e:
        logger.error(f"Metadata Tool (Semantic): Error during search: {e}", exc_info=True)
        return {"identified_documents": [], "error": f"Semantic search failed: {e}"}

# --- Tool Interface (Keep as is) --- 
def get_metadata_lookup_tool_semantic() -> Callable:
    """Factory function to get the semantic metadata lookup tool."""
    def tool_wrapper(query_term: str) -> Dict[str, Any]:
        # Perform input validation if necessary
        if not query_term or not isinstance(query_term, str):
             logger.error(f"Metadata Tool (Semantic): Invalid input: {query_term}")
             return {"identified_documents": [], "error": "Invalid input query."}
        return semantic_metadata_lookup(query_term)
    logger.info("Semantic Metadata Lookup Tool instance created.")
    return tool_wrapper

# --- Modified Example Usage --- 
if __name__ == '__main__':
    # --- Trigger the one-time setup --- 
    # ** RUN THIS SCRIPT ONCE TO POPULATE THE DB **
    # ** COMMENT OUT or REMOVE this call after setup is complete **
    # _generate_summaries_and_populate_vectordb() # COMMENTED OUT
    # print("\n--- Setup Complete (Potential). Now testing search function... ---")
    
    # Restore test code if desired
    print("Testing Semantic Metadata Lookup Tool...")
    test_query = "NVIDIA AI strategy in 2020"
    lookup_func = get_metadata_lookup_tool_semantic()
    results = lookup_func(test_query)
    print("\nResults:")
    print(json.dumps(results, indent=2))

# Explicitly expose only the new factory function if needed by the module structure
# (This depends on how __init__.py or other files import from this module)
# __all__ = ["get_metadata_lookup_tool_semantic"]