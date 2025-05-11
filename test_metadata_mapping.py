#!/usr/bin/env python3
"""
Script to investigate the metadata mapping issue between Microsoft and Alphabet documents.
"""

from pymongo import MongoClient
import json
from pprint import pprint

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    print("\n" + "="*80)
    print("INVESTIGATING MICROSOFT/ALPHABET DOCUMENT MISMAPPING ISSUE")
    print("="*80)
    
    # 1. Check all collections in the database
    print("\nCOLLECTIONS IN DATABASE:")
    print("-"*50)
    collections = db.list_collection_names()
    for collection in collections:
        count = db[collection].count_documents({})
        print(f"- {collection}: {count} documents")
    
    # 2. Examine category_summaries for MSFT
    print("\nMSFT CATEGORY SUMMARY:")
    print("-"*50)
    msft_category = db.category_summaries.find_one({"category_id": "MSFT"})
    if msft_category:
        print(f"Found category summary with ID: {msft_category.get('category_id')}")
        print(f"Category: {msft_category.get('category')}")
        print(f"Content length: {len(msft_category.get('content', ''))} characters")
    else:
        print("No category summary found for MSFT")
    
    # 3. Get the UUID that we're seeing in the metadata lookup results
    print("\nCATEGORY ID MAPPING MICROSOFT UUID:")
    print("-"*50)
    microsoft_uuid = "989b35ce-b8fd-44dc-b53f-2d3233a85706"  # UUID observed in Microsoft query results
    microsoft_docs = list(db.transcripts.find({"category_id": microsoft_uuid}, 
                                             {"_id": 1, "title": 1, "company": 1, "quarter": 1}))
    print(f"Found {len(microsoft_docs)} documents with category_id '{microsoft_uuid}'")
    if microsoft_docs:
        print("\nSample documents:")
        for i, doc in enumerate(microsoft_docs[:3]):
            print(f"Document {i+1}:")
            pprint(doc)
    
    # 4. Check the problematic document IDs we observed
    print("\nPROBLEMATIC DOCUMENT IDS:")
    print("-"*50)
    problem_doc_ids = [
        "e761cbf9-2ca9-42e6-b91e-4867d82a0f3e",  # Expected Microsoft, was Google
        "06cfa48b-3494-44d6-bcfc-b81c325b9881",  # Expected Microsoft, was Google
        "e93b73f9-617f-467f-8cc1-42a1fc5a1cb2"   # Expected Microsoft, was Google
    ]
    
    for doc_id in problem_doc_ids:
        doc = db.transcripts.find_one({"_id": doc_id})
        if doc:
            print(f"\nDocument ID: {doc_id}")
            print(f"Company: {doc.get('company', 'Not specified')}")
            print(f"Title: {doc.get('title', 'Not specified')}")
            print(f"Category ID: {doc.get('category_id', 'Not specified')}")
            print(f"Quarter: {doc.get('quarter', 'Not specified')}")
        else:
            print(f"\nDocument ID {doc_id} not found")
    
    # 5. Check if there are any documents actually related to Microsoft
    print("\nSEARCHING FOR ACTUAL MICROSOFT DOCUMENTS:")
    print("-"*50)
    # Try to find Microsoft documents by company name
    microsoft_docs_by_name = list(db.transcripts.find(
        {"company": {"$regex": "Microsoft", "$options": "i"}},
        {"_id": 1, "title": 1, "company": 1, "category_id": 1}
    ))
    print(f"Found {len(microsoft_docs_by_name)} documents with company name containing 'Microsoft'")
    if microsoft_docs_by_name:
        print("\nSample Microsoft documents:")
        for i, doc in enumerate(microsoft_docs_by_name[:3]):
            print(f"Document {i+1}:")
            pprint(doc)
    
    # 6. Verify Alphabet/Google documents 
    print("\nVERIFYING ALPHABET/GOOGLE DOCUMENTS:")
    print("-"*50)
    alphabet_docs = list(db.transcripts.find(
        {"company": {"$regex": "Alphabet|Google", "$options": "i"}},
        {"_id": 1, "title": 1, "company": 1, "category_id": 1}
    ))
    print(f"Found {len(alphabet_docs)} documents with company containing 'Alphabet' or 'Google'")
    if alphabet_docs:
        print("\nSample Alphabet documents:")
        for i, doc in enumerate(alphabet_docs[:3]):
            print(f"Document {i+1}:")
            pprint(doc)
    
    # 7. Check the category ID mapping for GOOGL
    print("\nCHECKING GOOGL CATEGORY SUMMARY:")
    print("-"*50)
    googl_category = db.category_summaries.find_one({"category_id": "GOOGL"})
    if googl_category:
        print(f"Found category summary with ID: {googl_category.get('category_id')}")
        print(f"Category: {googl_category.get('category')}")
    else:
        print("No category summary found for GOOGL")
    
    # 8. Compare ticker symbols with category IDs
    print("\nCOMPARING TICKER SYMBOLS WITH CATEGORY IDS:")
    print("-"*50)
    categories = list(db.category_summaries.find({}, {"category_id": 1, "category": 1, "_id": 0}))
    print(f"Found {len(categories)} category summaries")
    for category in categories:
        print(f"Category ID: {category.get('category_id')}, Category: {category.get('category', 'Not specified')}")
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 