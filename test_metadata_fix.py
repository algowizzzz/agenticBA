#!/usr/bin/env python3
"""
Test script to verify that the metadata lookup tool correctly handles
both ticker symbols and UUIDs after applying the fix.
"""

import os
import json
from langchain_tools.tool4_metadata_lookup import get_metadata_lookup_tool
from langchain_tools.category_id_mapping import (
    TICKER_TO_UUID,
    UUID_TO_TICKER,
    normalize_category_id,
    get_uuid_for_ticker,
    get_ticker_for_uuid
)

# Set API key
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("Please set ANTHROPIC_API_KEY environment variable")
    exit(1)

def test_mapping_functions():
    """Test the mapping functions directly."""
    print("\n" + "="*80)
    print("TESTING CATEGORY ID MAPPING FUNCTIONS")
    print("="*80)
    
    test_cases = [
        # Known ticker symbols
        ("MSFT", "Expected ticker->UUID: 5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18"),
        ("GOOGL", "Expected ticker->UUID: 989b35ce-b8fd-44dc-b53f-2d3233a85706"),
        
        # Known UUIDs
        ("5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18", "Expected UUID->ticker: MSFT"),
        ("989b35ce-b8fd-44dc-b53f-2d3233a85706", "Expected UUID->ticker: GOOGL"),
        
        # Normalize function (should return ticker form when available)
        ("MSFT", "normalize_category_id should return: MSFT"),
        ("5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18", "normalize_category_id should return: MSFT"),
        ("GOOGL", "normalize_category_id should return: GOOGL"),
        ("989b35ce-b8fd-44dc-b53f-2d3233a85706", "normalize_category_id should return: GOOGL"),
        
        # Unknown values
        ("UNKNOWN_TICKER", "Should return: None or UNKNOWN_TICKER"),
        ("unknown-uuid-value", "Should return: None or unknown-uuid-value")
    ]
    
    print("\nMAPPING FUNCTION TESTS:")
    print("-"*50)
    
    for i, (test_value, description) in enumerate(test_cases):
        print(f"Test {i+1}: {description}")
        print(f"  Input value: {test_value}")
        
        # Test get_uuid_for_ticker
        uuid_result = get_uuid_for_ticker(test_value)
        print(f"  get_uuid_for_ticker result: {uuid_result}")
        
        # Test get_ticker_for_uuid
        ticker_result = get_ticker_for_uuid(test_value)
        print(f"  get_ticker_for_uuid result: {ticker_result}")
        
        # Test normalize_category_id
        normalized = normalize_category_id(test_value)
        print(f"  normalize_category_id result: {normalized}")
        print()

def test_metadata_lookup_tool():
    """Test the metadata lookup tool with various queries."""
    print("\n" + "="*80)
    print("TESTING METADATA LOOKUP TOOL WITH FIXED MAPPING")
    print("="*80)
    
    # Get metadata lookup tool
    try:
        metadata_lookup_fn = get_metadata_lookup_tool()
    except Exception as e:
        print(f"Error creating metadata lookup tool: {e}")
        return
    
    # Test queries
    test_queries = [
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
    
    for query in test_queries:
        print(f"\nQUERY: {query}")
        print("-"*50)
        
        try:
            result = metadata_lookup_fn(query)
            print(f"Category ID: {result.get('relevant_category_id')}")
            
            # Check if the category ID is in normalized form (ticker if available)
            category_id = result.get('relevant_category_id')
            if category_id:
                expected_form = normalize_category_id(category_id)
                if category_id != expected_form:
                    print(f"WARNING: Category ID {category_id} is not in normalized form. Expected: {expected_form}")
                else:
                    print("✓ Category ID is in the correct normalized form.")
            
            # Print document IDs
            doc_ids = result.get('relevant_doc_ids', [])
            if doc_ids:
                print(f"Found {len(doc_ids)} relevant document IDs:")
                for i, doc_id in enumerate(doc_ids[:3]):  # Show first 3
                    print(f"  {i+1}. {doc_id}")
                if len(doc_ids) > 3:
                    print(f"  ...and {len(doc_ids) - 3} more")
            else:
                print("No relevant document IDs found.")
                
        except Exception as e:
            print(f"Error calling metadata lookup for query '{query}': {e}")
    
def main():
    """Run the tests."""
    test_mapping_functions()
    test_metadata_lookup_tool()

if __name__ == "__main__":
    main() 