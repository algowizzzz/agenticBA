#!/usr/bin/env python3
"""
Test the full document analysis tool with a simple query and document ID.
"""

import sys
import json
from langchain_tools.full_document_analysis_tool import analyze_full_document

def main():
    # Default query and document ID
    query = "What was mentioned about future outlook?"
    document_id = "ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3"
    chunk_index = None
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        query = sys.argv[1]
    if len(sys.argv) > 2:
        document_id = sys.argv[2]
    if len(sys.argv) > 3:
        chunk_index = int(sys.argv[3])
    
    print(f"Testing Full Document Analysis Tool with:")
    print(f"Query: {query}")
    print(f"Document ID: {document_id}")
    print(f"Chunk Index: {chunk_index}")
    
    # Call the tool
    result = analyze_full_document(query, document_id, chunk_index)
    
    # Print result
    print("\n--- Full Document Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("------------------------------------------")

if __name__ == "__main__":
    main() 