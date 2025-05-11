#!/usr/bin/env python3
"""
Debug script for document search tool to investigate why it returns non-existent document IDs
"""

import logging
import sys
import os
import json
from typing import List, Dict, Any
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the document-level search implementation
sys.path.append('.')
from final_document_level_search import semantic_document_search, get_document_level_search_tool

def debug_search_results(query: str):
    """Test the document search tool and verify IDs against MongoDB"""
    print(f"Testing document search with query: '{query}'")
    
    # 1. Get search results using the tool
    search_tool = get_document_level_search_tool()
    results = search_tool(query)
    
    if results.get("error"):
        print(f"Error: {results['error']}")
        return
    
    documents = results.get("identified_documents", [])
    print(f"Search returned {len(documents)} documents")
    
    # 2. Connect to MongoDB to check if these document IDs exist
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # 3. Check each document ID
    print("\nChecking each document ID against MongoDB:")
    for i, doc in enumerate(documents):
        doc_id = doc.get("document_id", "Unknown")
        doc_name = doc.get("document_name", "Unknown")
        ticker = doc.get("ticker", "Unknown")
        
        # Check if document exists in transcripts collection
        transcript = db.transcripts.find_one({"document_id": doc_id})
        
        # Check if document has a summary
        summary = db.document_summaries.find_one({"document_id": doc_id})
        
        exists_status = "✓ EXISTS" if transcript else "✗ NOT FOUND"
        summary_status = "✓ Has summary" if summary else "✗ No summary"
        
        print(f"{i+1}. {doc_id} | {ticker} | {doc_name}")
        print(f"   MongoDB status: {exists_status} | {summary_status}")
        
        # If not found, print more details about the document returned by search
        if not transcript:
            print(f"   Search returned (not in MongoDB):")
            for key, value in doc.items():
                if key != "excerpt" and key != "content":  # Skip long text fields
                    print(f"      {key}: {value}")
    
    # 4. Check if MongoDB has valid documents we should be finding instead
    print("\nSearching MongoDB for relevant documents (2017 AMZN and AAPL):")
    
    # Query for 2017 AMZN transcripts
    amzn_2017_query = {
        '$and': [
            {'$or': [
                {'ticker': 'AMZN'},
                {'category_id': 'AMZN'}
            ]},
            {'$or': [
                {'year': '2017'},
                {'fiscal_year': '2017'},
                {'date': {'$regex': '2017'}}
            ]}
        ]
    }
    
    # Query for 2017 AAPL transcripts
    aapl_2017_query = {
        '$and': [
            {'$or': [
                {'ticker': 'AAPL'},
                {'category_id': 'AAPL'}
            ]},
            {'$or': [
                {'year': '2017'},
                {'fiscal_year': '2017'},
                {'date': {'$regex': '2017'}}
            ]}
        ]
    }
    
    amzn_docs = list(db.transcripts.find(amzn_2017_query))
    aapl_docs = list(db.transcripts.find(aapl_2017_query))
    
    print(f"Found {len(amzn_docs)} AMZN 2017 transcripts in MongoDB:")
    for doc in amzn_docs:
        doc_id = doc.get("document_id", "Unknown")
        quarter = doc.get("quarter", "Unknown")
        date = doc.get("date", "Unknown date")
        print(f"- {doc_id} | Q{quarter} | {date}")
    
    print(f"\nFound {len(aapl_docs)} AAPL 2017 transcripts in MongoDB:")
    for doc in aapl_docs:
        doc_id = doc.get("document_id", "Unknown")
        quarter = doc.get("quarter", "Unknown")
        date = doc.get("date", "Unknown date")
        print(f"- {doc_id} | Q{quarter} | {date}")
    
    # 5. Examine what's in the ChromaDB collection
    try:
        from chromadb import PersistentClient
        chroma_client = PersistentClient(path="./chroma_db_persist")
        
        if "document_level_embeddings" in [col.name for col in chroma_client.list_collections()]:
            collection = chroma_client.get_collection("document_level_embeddings")
            count = collection.count()
            print(f"\nChromaDB collection 'document_level_embeddings' has {count} documents")
            
            # Sample some IDs from ChromaDB
            if count > 0:
                print("\nSample IDs from ChromaDB:")
                # Get metadata for a few items
                results = collection.get(limit=5)
                for i, doc_id in enumerate(results["ids"]):
                    print(f"{i+1}. {doc_id}")
                    
                    # Check if this ID exists in MongoDB
                    db_doc = db.transcripts.find_one({"document_id": doc_id})
                    if db_doc:
                        print(f"   ✓ EXISTS in MongoDB")
                    else:
                        print(f"   ✗ NOT FOUND in MongoDB")
        else:
            print("\nChromaDB collection 'document_level_embeddings' not found!")
    except Exception as e:
        print(f"\nError examining ChromaDB: {e}")

if __name__ == "__main__":
    # Test with the same query that produced non-existent document IDs
    test_query = "Compare Apple and Amazon's revenue in Q1 2017"
    debug_search_results(test_query) 