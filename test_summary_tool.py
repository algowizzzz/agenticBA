#!/usr/bin/env python3
"""
Test the document summaries analysis tool with a simple query and document IDs.
"""

import sys
import json
from langchain_tools.summaries_analysis_tool import analyze_document_summaries

def main():
    # Default query and document IDs
    query = "What was mentioned about revenue growth?"
    document_ids = [
        "ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3",
        "7e538606-f18b-410f-8284-59e5929f2aaa"
    ]
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        query = sys.argv[1]
    if len(sys.argv) > 2:
        document_ids = sys.argv[2].split(",")
    
    print(f"Testing Summary Analysis Tool with:")
    print(f"Query: {query}")
    print(f"Document IDs: {document_ids}")
    
    # Call the tool
    result = analyze_document_summaries(query, document_ids)
    
    # Print result
    print("\n--- Summary Analysis Tool Result ---")
    print(json.dumps(result, indent=2))
    print("------------------------------------")

if __name__ == "__main__":
    main() 