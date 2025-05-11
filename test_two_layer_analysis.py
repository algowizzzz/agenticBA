#!/usr/bin/env python3
"""
Test Script for Two-Layered Document Analysis Tools

Tests the new document summaries and full document analysis tools.
"""

import os
import sys
import json
import logging

# Add the parent directory to sys.path to make imports work
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Direct imports to avoid package conflicts
from langchain_anthropic import ChatAnthropic
from pymongo import MongoClient

# Import our new tools directly
from langchain_tools.earnings_analysis_utils import init_db, get_document_summary, get_document_full_text
from langchain_tools.summaries_analysis_tool import analyze_document_summaries
from langchain_tools.full_document_analysis_tool import analyze_full_document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_document_ids(limit=3):
    """Fetch some document IDs from MongoDB for testing"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # Get documents that have summaries
        summary_docs = list(db.document_summaries.find({}, {"transcript_uuid": 1}).limit(limit))
        document_ids = [doc["transcript_uuid"] for doc in summary_docs if "transcript_uuid" in doc]
        
        return document_ids
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []

def test_summary_analysis():
    """Test the document summaries analysis tool"""
    print("\n===== Testing Document Summaries Analysis Tool =====")
    
    # Get some document IDs
    document_ids = get_document_ids(3)
    if not document_ids:
        print("No document IDs found. Skipping summary analysis test.")
        return
    
    print(f"Found {len(document_ids)} document IDs:")
    for i, doc_id in enumerate(document_ids):
        print(f"  {i+1}. {doc_id}")
    
    # Test query
    test_query = "Analyze the revenue growth and key business segments"
    print(f"\nQuery: {test_query}")
    
    # Call the tool
    result = analyze_document_summaries(test_query, document_ids)
    
    # Print result
    print("\nResult:")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print("Documents analyzed:", ", ".join(result.get("documents_analyzed", [])))
        print("\nAnswer:")
        print(result.get("answer", "No answer provided"))

def test_full_document_analysis():
    """Test the full document analysis tool"""
    print("\n===== Testing Full Document Analysis Tool =====")
    
    # Get a document ID
    document_ids = get_document_ids(1)
    if not document_ids:
        print("No document IDs found. Skipping full document analysis test.")
        return
    
    document_id = document_ids[0]
    print(f"Using document ID: {document_id}")
    
    # Test query
    test_query = "What was mentioned about future outlook and guidance?"
    print(f"\nQuery: {test_query}")
    
    # Call the tool
    result = analyze_full_document(test_query, document_id)
    
    # Print result
    print("\nResult:")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"Document: {result.get('document_name', 'Unknown')}")
        print(f"Total chunks: {result.get('total_chunks', 0)}")
        print(f"Current chunk: {result.get('current_chunk', 0)}")
        print(f"Has more chunks: {result.get('has_more_chunks', False)}")
        
        print("\nAnswer:")
        print(result.get("answer", "No answer provided"))
        
        # Test next chunk if available
        if result.get("has_more_chunks", False):
            next_chunk = result.get("next_chunk", 0)
            print(f"\nTesting next chunk ({next_chunk})...")
            
            # Call the tool with next chunk
            chunk_result = analyze_full_document(test_query, document_id, next_chunk)
            
            print("\nNext Chunk Result:")
            print(f"Total chunks: {chunk_result.get('total_chunks', 0)}")
            print(f"Current chunk: {chunk_result.get('current_chunk', 0)}")
            print(f"Has more chunks: {chunk_result.get('has_more_chunks', False)}")
            
            print("\nNext Chunk Answer:")
            print(chunk_result.get("answer", "No answer provided"))

def main():
    print("Starting Two-Layered Document Analysis Tools Test\n")
    
    # Test Summary Analysis
    test_summary_analysis()
    
    # Test Full Document Analysis
    test_full_document_analysis()
    
    print("\nTests completed!")

if __name__ == "__main__":
    main() 