#!/usr/bin/env python3
"""
Script to examine document structure in MongoDB to identify the mismapping issue.
"""

from pymongo import MongoClient
import json
from pprint import pprint
import os

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    print("\n" + "="*80)
    print("EXAMINING DOCUMENT STRUCTURE TO IDENTIFY MISMAPPING ISSUE")
    print("="*80)
    
    # Check document schema in transcripts collection
    print("\nTRANSCRIPT DOCUMENT SCHEMA:")
    print("-"*50)
    
    # Get first document to check field structure
    first_doc = db.transcripts.find_one({})
    if first_doc:
        print("Fields in transcript documents:")
        for field in first_doc.keys():
            print(f"- {field}")
    
    # Check for expected fields
    print("\nCHECKING FOR EXPECTED FIELDS:")
    print("-"*50)
    
    # Check for 'company' field
    company_docs = db.transcripts.count_documents({"company": {"$exists": True}})
    print(f"Documents with 'company' field: {company_docs}")
    
    # Check for 'title' field
    title_docs = db.transcripts.count_documents({"title": {"$exists": True}})
    print(f"Documents with 'title' field: {title_docs}")
    
    # Check for 'category_id' field
    category_id_docs = db.transcripts.count_documents({"category_id": {"$exists": True}})
    print(f"Documents with 'category_id' field: {category_id_docs}")
    
    # Check for 'document_id' field
    document_id_docs = db.transcripts.count_documents({"document_id": {"$exists": True}})
    print(f"Documents with 'document_id' field: {document_id_docs}")
    
    # Check primary key field
    id_field_docs = db.transcripts.count_documents({"_id": {"$exists": True}})
    print(f"Documents with '_id' field: {id_field_docs}")
    
    # Examine the relationship between _id and document_id
    print("\nCHECKING RELATIONSHIP BETWEEN _id AND document_id:")
    print("-"*50)
    
    # Get a sample document with both fields
    sample_doc = db.transcripts.find_one({"document_id": {"$exists": True}})
    if sample_doc:
        print(f"Sample document:")
        print(f"- _id: {sample_doc.get('_id')}")
        print(f"- document_id: {sample_doc.get('document_id')}")
    
    # Check if any documents have document_id matching _id
    matching_ids = db.transcripts.count_documents({
        "document_id": {"$exists": True},
        "$expr": {"$eq": ["$document_id", {"$toString": "$_id"}]}
    })
    print(f"Documents where document_id equals _id (as string): {matching_ids}")
    
    # Examine categories
    print("\nANALYZING CATEGORY_ID FIELD:")
    print("-"*50)
    
    # Get all unique category_id values
    category_ids = db.transcripts.distinct("category_id")
    print(f"Found {len(category_ids)} unique category_id values:")
    for i, cat_id in enumerate(category_ids):
        count = db.transcripts.count_documents({"category_id": cat_id})
        print(f"{i+1}. {cat_id}: {count} documents")
    
    # Check if _id field is being used in the document lookup
    print("\nCHECKING ID FIELDS USAGE:")
    print("-"*50)
    
    # Get category_id and company mapping
    category_company_map = {}
    pipeline = [
        {"$group": {"_id": "$category_id", "companies": {"$addToSet": "$company"}}}
    ]
    for doc in db.transcripts.aggregate(pipeline):
        cat_id = doc["_id"]
        companies = doc.get("companies", [])
        if companies:
            category_company_map[cat_id] = companies
    
    print("Category ID to company name mapping:")
    for cat_id, companies in category_company_map.items():
        company_str = ", ".join(companies) if companies else "No company name found"
        print(f"- {cat_id}: {company_str}")
    
    # Check document ID format in document_summaries
    print("\nDOCUMENT_SUMMARIES COLLECTION ID FORMAT:")
    print("-"*50)
    
    # Get sample document summary
    sample_summary = db.document_summaries.find_one({})
    if sample_summary:
        print("Sample document summary fields:")
        for field in sample_summary.keys():
            print(f"- {field}: {type(sample_summary[field])}")
        
        # Check if document_id in summaries refers to _id or document_id in transcripts
        if "document_id" in sample_summary:
            doc_id = sample_summary["document_id"]
            print(f"\nLooking for document with ID '{doc_id}'")
            
            # Check if it matches _id in transcripts
            match_id = db.transcripts.find_one({"_id": doc_id})
            if match_id:
                print("✓ Found matching document using _id field")
            else:
                print("✗ No match found using _id field")
            
            # Check if it matches document_id in transcripts
            match_doc_id = db.transcripts.find_one({"document_id": doc_id})
            if match_doc_id:
                print("✓ Found matching document using document_id field")
            else:
                print("✗ No match found using document_id field")
    
    # Specific problem with MSFT queries
    print("\nINVESTIGATING MSFT DOCUMENT MAPPING:")
    print("-"*50)
    
    # First, check if there's a category_id 'MSFT'
    msft_category = db.category_summaries.find_one({"category_id": "MSFT"})
    if msft_category:
        print(f"Found MSFT category in category_summaries")
        # Check which documents have this category_id
        msft_docs = list(db.transcripts.find({"category_id": "MSFT"}, {"_id": 1, "document_id": 1, "title": 1, "company": 1}))
        print(f"Found {len(msft_docs)} documents with category_id 'MSFT'")
        if msft_docs:
            print("Sample MSFT documents:")
            for i, doc in enumerate(msft_docs[:3]):
                print(f"Doc {i+1}:")
                pprint(doc)
    
    # Check if there's a category_id 'Microsoft' or similar
    microsoft_docs = list(db.transcripts.find(
        {"category_id": {"$regex": "Microsoft", "$options": "i"}}, 
        {"_id": 1, "document_id": 1, "title": 1, "company": 1}
    ))
    print(f"Found {len(microsoft_docs)} documents with category_id containing 'Microsoft'")
    
    # Check if there are documents with company name 'Microsoft'
    microsoft_company_docs = list(db.transcripts.find(
        {"company": {"$regex": "Microsoft", "$options": "i"}}, 
        {"_id": 1, "document_id": 1, "title": 1, "company": 1, "category_id": 1}
    ))
    print(f"Found {len(microsoft_company_docs)} documents with company field containing 'Microsoft'")
    if microsoft_company_docs:
        print("Sample Microsoft company documents:")
        for i, doc in enumerate(microsoft_company_docs[:3]):
            print(f"Doc {i+1}:")
            pprint(doc)
    
    # Check metadata lookup tool functionality
    print("\nTESTING METADATA LOOKUP EXTRACTION:")
    print("-"*50)
    
    # Simulate the metadata extraction logic from tool4_metadata_lookup.py
    category_to_doc_ids = {}
    for doc in db.transcripts.find({}, {"document_id": 1, "category_id": 1, "_id": 0}):
        doc_id_str = doc.get("document_id")
        category_id = doc.get("category_id")
        if not doc_id_str or not category_id:
            continue
        
        if category_id not in category_to_doc_ids:
            category_to_doc_ids[category_id] = []
        category_to_doc_ids[category_id].append(doc_id_str)
    
    print(f"Extracted mappings for {len(category_to_doc_ids)} categories")
    
    # Check for ticker-like categories ("MSFT", "AAPL", etc.)
    ticker_categories = [cat for cat in category_to_doc_ids.keys() if cat.isupper() and len(cat) <= 5]
    print(f"Found {len(ticker_categories)} ticker-like categories: {ticker_categories}")
    
    # Check specifically for MSFT mapping
    if "MSFT" in category_to_doc_ids:
        print(f"MSFT maps to {len(category_to_doc_ids['MSFT'])} document IDs")
        print(f"Sample MSFT document IDs: {category_to_doc_ids['MSFT'][:3]}")
    else:
        print("No MSFT category mapping found")
    
    # Check for GOOGL mapping
    if "GOOGL" in category_to_doc_ids:
        print(f"GOOGL maps to {len(category_to_doc_ids['GOOGL'])} document IDs")
        print(f"Sample GOOGL document IDs: {category_to_doc_ids['GOOGL'][:3]}")
    else:
        print("No GOOGL category mapping found")
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 