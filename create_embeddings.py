#!/usr/bin/env python3
"""
Simple script to create document-level embeddings
"""

import logging
from document_level_search import create_document_level_embeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting to create document-level embeddings...")
    collection = create_document_level_embeddings()
    logger.info("Document-level embeddings created successfully.")
    
    # Print collection stats
    count = collection.count()
    logger.info(f"Collection contains {count} documents.") 