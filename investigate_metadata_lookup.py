#!/usr/bin/env python3
"""
Script to investigate how the metadata lookup tool maps search queries to document IDs.
"""

import os
import sys
import logging
from langchain_tools.tool4_metadata_lookup import get_metadata_lookup_tool
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_metadata_lookup(query):
    """Run a query through the metadata lookup tool and display results."""
    print(f"\n\n{'='*80}")
    print(f"TESTING METADATA LOOKUP: '{query}'")
    print(f"{'='*80}")
    
    # Get metadata lookup tool function
    try:
        metadata_lookup_fn = get_metadata_lookup_tool()
        
        # Run the query
        print(f"\nExecuting query: '{query}'")
        result = metadata_lookup_fn(query)
        
        # Display results
        print("\nRESULTS:")
        print("-"*50)
        print(f"Relevant Category ID: {result.get('relevant_category_id')}")
        print(f"Category Summary Available: {result.get('category_summary_available')}")
        print(f"Number of Relevant Document IDs: {len(result.get('relevant_doc_ids', []))}")
        print(f"Number of Documents with Summaries: {len(result.get('doc_ids_with_summaries', []))}")
        print(f"Error: {result.get('error')}")
        
        # Display document IDs
        print("\nRELEVANT DOCUMENT IDs:")
        print("-"*50)
        for i, doc_id in enumerate(result.get('relevant_doc_ids', [])):
            print(f"{i+1}. {doc_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in metadata lookup: {e}", exc_info=True)
        print(f"ERROR: {str(e)}")
        return None

def get_document_details(doc_id):
    """Get available information about a specific document ID."""
    from pymongo import MongoClient
    
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Find the document
    doc = db.transcripts.find_one({"_id": doc_id})
    
    if doc:
        # Get relevant document details
        return {
            "_id": doc.get("_id"),
            "title": doc.get("title", "Not specified"),
            "company": doc.get("company", "Not specified"),
            "category_id": doc.get("category_id", "Not specified"),
            "quarter": doc.get("quarter", "Not specified"),
            "year": doc.get("year", "Not specified"),
            "content_length": len(doc.get("content", "")) if "content" in doc else "Not available"
        }
    else:
        print(f"Document not found: {doc_id}")
        return None

def main():
    """
    Run metadata lookup tests for various queries to identify mismapping issues.
    """
    # Set API key if available from environment
    if "ANTHROPIC_API_KEY" in os.environ:
        api_key = os.environ["ANTHROPIC_API_KEY"]
        print(f"Using API key from environment.")
    else:
        api_key = input("Enter your Anthropic API key: ")
        os.environ["ANTHROPIC_API_KEY"] = api_key
    
    print("\nRunning metadata lookup tests...")
    
    # Test cases focused on Microsoft vs. Google mapping issue
    test_cases = [
        "Microsoft earnings call",
        "MSFT earnings call",
        "Satya Nadella statements",
        "Google earnings call",
        "GOOGL earnings call",
        "Alphabet earnings call",
        "Sundar Pichai statements",
        "Apple earnings call",
        "AAPL earnings call",
        "Tim Cook statements"
    ]
    
    results = {}
    
    # Run tests and collect results
    for query in test_cases:
        result = test_metadata_lookup(query)
        results[query] = result
        
        # If we have document IDs, get details for the first few
        if result and 'relevant_doc_ids' in result and result['relevant_doc_ids']:
            print("\nSAMPLE DOCUMENT DETAILS:")
            print("-"*50)
            
            for doc_id in result['relevant_doc_ids'][:2]:  # Just show first 2 docs
                doc_details = get_document_details(doc_id)
                if doc_details:
                    print(f"\nDocument ID: {doc_id}")
                    for key, value in doc_details.items():
                        if key != "_id":  # Skip showing the ID again
                            print(f"{key}: {value}")
    
    # Final summary
    print("\n\n" + "="*80)
    print("METADATA LOOKUP MAPPING SUMMARY")
    print("="*80)
    
    print("\nQuery to Category ID Mapping:")
    print("-"*50)
    for query, result in results.items():
        if result:
            category_id = result.get('relevant_category_id', 'None')
            doc_count = len(result.get('relevant_doc_ids', []))
            print(f"'{query}' → Category ID: {category_id}, Doc Count: {doc_count}")
    
    # Check for mismapping patterns
    print("\nPossible Mismapping Issues:")
    print("-"*50)
    
    # Check if Microsoft queries map to Google documents and vice versa
    microsoft_queries = ["Microsoft earnings call", "MSFT earnings call", "Satya Nadella statements"]
    google_queries = ["Google earnings call", "GOOGL earnings call", "Alphabet earnings call", "Sundar Pichai statements"]
    
    # Extract category IDs for Microsoft queries
    ms_category_ids = set()
    for query in microsoft_queries:
        if query in results and results[query]:
            ms_category_ids.add(results[query].get('relevant_category_id'))
    
    # Extract category IDs for Google queries
    google_category_ids = set()
    for query in google_queries:
        if query in results and results[query]:
            google_category_ids.add(results[query].get('relevant_category_id'))
    
    # Check for overlaps
    if ms_category_ids.intersection(google_category_ids):
        print("CRITICAL ISSUE: Microsoft and Google queries map to the same category IDs!")
        print(f"Overlapping category IDs: {ms_category_ids.intersection(google_category_ids)}")
    else:
        print("No direct category ID overlaps between Microsoft and Google queries.")
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 