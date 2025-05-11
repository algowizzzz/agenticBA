#!/usr/bin/env python3
"""
Test script for Microsoft Q1 2017 query using our new two-layer tools directly
"""

import os
import logging
import sys
import json
from pymongo import MongoClient
from langchain_anthropic import ChatAnthropic
from langchain_tools.summaries_analysis_tool import analyze_document_summaries
from langchain_tools.full_document_analysis_tool import analyze_full_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Query
test_query = "Give me a summary of Microsoft's Q1 2017 earnings call"

def get_msft_document_ids(limit=3):
    """Find relevant Microsoft document IDs from the database"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # First, try to find document IDs by searching for MSFT 2017 Q1
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"company_ticker": "MSFT"}, 
                        {"$or": [
                            {"call_title": {"$regex": "Q1.*2017", "$options": "i"}},
                            {"call_title": {"$regex": "2017.*Q1", "$options": "i"}},
                            {"call_date": {"$regex": "2017", "$options": "i"}}
                        ]}
                    ]
                }
            },
            {"$limit": limit}
        ]
        
        docs = list(db.transcripts.aggregate(pipeline))
        
        # If we found documents, return their IDs
        if docs:
            logger.info(f"Found {len(docs)} Microsoft Q1 2017 documents")
            return [doc.get('document_id') for doc in docs]
        else:
            # If we didn't find specific Q1 2017 documents, just get any Microsoft documents
            logger.info("No specific Q1 2017 documents found, fetching general Microsoft documents")
            docs = list(db.transcripts.find({"company_ticker": "MSFT"}, {"document_id": 1}).limit(limit))
            return [doc.get('document_id') for doc in docs]
    
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []

def test_layer_one(query, document_ids):
    """Test the first layer - document summaries analysis"""
    logger.info(f"Testing Document Summaries Analysis with {len(document_ids)} documents")
    logger.info(f"Document IDs: {document_ids}")
    logger.info(f"Query: {query}")
    
    result = analyze_document_summaries(query, document_ids)
    
    print("\n===== LAYER 1: Document Summaries Analysis =====")
    print(f"Query: {query}")
    print(f"Document IDs: {document_ids}")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"\nAnswer:\n{result.get('answer', 'No answer provided')}")

def test_layer_two(query, document_id):
    """Test the second layer - full document analysis"""
    logger.info(f"Testing Full Document Analysis with document ID: {document_id}")
    logger.info(f"Query: {query}")
    
    result = analyze_full_document(query, document_id)
    
    print("\n===== LAYER 2: Full Document Analysis =====")
    print(f"Query: {query}")
    print(f"Document ID: {document_id}")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"\nAnswer:\n{result.get('answer', 'No answer provided')}")
        print(f"\nHas more chunks: {result.get('has_more_chunks', False)}")
        print(f"Current chunk: {result.get('current_chunk', 0)}")
        print(f"Total chunks: {result.get('total_chunks', 1)}")

def main():
    # Get document IDs
    document_ids = get_msft_document_ids()
    
    if not document_ids:
        logger.error("No document IDs found. Exiting.")
        sys.exit(1)
    
    # Test layer one - document summaries analysis
    test_layer_one(test_query, document_ids)
    
    # Test layer two - full document analysis (using first document ID)
    test_layer_two(test_query, document_ids[0])

if __name__ == "__main__":
    main() 