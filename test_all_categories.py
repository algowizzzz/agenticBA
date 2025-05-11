#!/usr/bin/env python3
"""
Script to test the Category Summary Tool for all categories in the database.
"""

import os
import sys
import json
import logging
import time
from pymongo import MongoClient
from langchain_tools.tool2_category import category_summary_tool

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_all_categories():
    """Retrieve all category IDs from the MongoDB database."""
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Find all categories in the category_summaries collection
    summaries = list(db.category_summaries.find({}, {'category_id': 1, 'category': 1, '_id': 0}))
    
    categories = []
    for summary in summaries:
        # Use category_id if available, otherwise try category field
        category_id = summary.get('category_id') or summary.get('category')
        if category_id:
            categories.append(category_id)
    
    return categories

def test_category(category_id):
    """Test the category tool for a specific category ID."""
    query = f"What are the recent financial trends for {category_id}?"
    
    try:
        # Call the category tool function
        result = category_summary_tool(query=query, category_id=category_id)
        
        # Check for success indicators
        summary_fetched = "error" not in result or not result["error"]
        answer_generated = result["answer"] and "Error" not in result["answer"]
        
        return {
            "category_id": category_id,
            "success": summary_fetched and answer_generated,
            "summary_fetched": summary_fetched,
            "answer_generated": answer_generated,
            "error": result.get("error"),
            "answer_snippet": result["answer"][:100] + "..." if result["answer"] else None
        }
    except Exception as e:
        logger.error(f"Error testing category {category_id}: {e}")
        return {
            "category_id": category_id,
            "success": False,
            "summary_fetched": False,
            "answer_generated": False,
            "error": str(e),
            "answer_snippet": None
        }

def main():
    # Set API key 
    os.environ["ANTHROPIC_API_KEY"] = "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"
    
    # Get all categories
    categories = get_all_categories()
    logger.info(f"Found {len(categories)} categories to test: {categories}")
    
    # Initialize results
    results = []
    
    # Test each category
    for category_id in categories:
        logger.info(f"Testing category: {category_id}")
        result = test_category(category_id)
        results.append(result)
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
    
    # Calculate success rate
    successful = sum(1 for r in results if r["success"])
    success_rate = (successful / len(results)) * 100 if results else 0
    
    # Print summary
    print("\n=== CATEGORY TOOL TESTING SUMMARY ===")
    print(f"Total categories tested: {len(results)}")
    print(f"Successful tests: {successful} ({success_rate:.1f}%)")
    print(f"Failed tests: {len(results) - successful}\n")
    
    # Print details
    print("=== DETAILED RESULTS ===")
    for result in results:
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{status} - {result['category_id']}")
        
        if not result["success"]:
            if not result["summary_fetched"]:
                print(f"  Summary fetch failed: {result['error']}")
            elif not result["answer_generated"]:
                print(f"  Answer generation failed")
        else:
            print(f"  Answer snippet: {result['answer_snippet']}")
        print("")
    
    # Save results to file
    with open("category_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to category_test_results.json")

if __name__ == "__main__":
    main() 