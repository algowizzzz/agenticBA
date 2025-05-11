#!/usr/bin/env python3
"""
Script to check the category mappings between category_summaries and transcript documents.
This will help identify the disconnection between ticker symbols and UUIDs.
"""

from pymongo import MongoClient
import json
from pprint import pprint
import uuid
import re

def is_uuid(s):
    try:
        uuid_obj = uuid.UUID(s)
        return True
    except (ValueError, AttributeError, TypeError):
        return False

def is_ticker_symbol(s):
    # Simple check for uppercase letters and length <= 5
    return isinstance(s, str) and s.isupper() and len(s) <= 5

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    print("\n" + "="*80)
    print("ANALYZING CATEGORY MAPPING DISCONNECTION")
    print("="*80)
    
    # 1. Extract all category_ids from category_summaries
    print("\nCATEGORY SUMMARIES COLLECTION:")
    print("-"*50)
    
    category_summaries = list(db.category_summaries.find({}, 
                                                     {"category_id": 1, "category": 1, "_id": 0}))
    
    print(f"Found {len(category_summaries)} records in category_summaries collection")
    
    ticker_categories = []
    uuid_categories = []
    
    for cat in category_summaries:
        cat_id = cat.get("category_id")
        if is_ticker_symbol(cat_id):
            ticker_categories.append(cat_id)
        elif is_uuid(cat_id):
            uuid_categories.append(cat_id)
    
    print(f"Category IDs in ticker format: {len(ticker_categories)}")
    print(f"Category IDs in UUID format: {len(uuid_categories)}")
    
    print("\nSample ticker category IDs:")
    for ticker in ticker_categories[:5]:
        print(f"- {ticker}")
    
    # 2. Extract all category_ids from transcripts
    print("\nTRANSCRIPTS COLLECTION CATEGORY IDS:")
    print("-"*50)
    
    transcript_categories = db.transcripts.distinct("category_id")
    
    transcript_ticker_categories = []
    transcript_uuid_categories = []
    
    for cat_id in transcript_categories:
        if is_ticker_symbol(cat_id):
            transcript_ticker_categories.append(cat_id)
        elif is_uuid(cat_id):
            transcript_uuid_categories.append(cat_id)
    
    print(f"Category IDs in ticker format: {len(transcript_ticker_categories)}")
    print(f"Category IDs in UUID format: {len(transcript_uuid_categories)}")
    
    print("\nSample ticker category IDs in transcripts:")
    for ticker in transcript_ticker_categories[:5]:
        print(f"- {ticker}")
    
    print("\nSample UUID category IDs in transcripts:")
    for uuid_str in transcript_uuid_categories[:5]:
        print(f"- {uuid_str}")
    
    # 3. Find overlapping and non-overlapping categories
    print("\nCOMPARING CATEGORY IDS:")
    print("-"*50)
    
    summary_cat_ids = set([c.get("category_id") for c in category_summaries])
    transcript_cat_ids = set(transcript_categories)
    
    overlapping = summary_cat_ids.intersection(transcript_cat_ids)
    summaries_only = summary_cat_ids - transcript_cat_ids
    transcripts_only = transcript_cat_ids - summary_cat_ids
    
    print(f"Category IDs in both collections: {len(overlapping)}")
    print(f"Category IDs only in summaries: {len(summaries_only)}")
    print(f"Category IDs only in transcripts: {len(transcripts_only)}")
    
    # 4. Check if there's a mapping between ticker symbols and UUIDs
    print("\nCHECKING FOR TICKER-UUID MAPPING:")
    print("-"*50)
    
    # Look at documents table for potential mappings
    ticker_to_uuid_map = {}
    uuid_to_ticker_map = {}
    
    # Get documents with both category and category_id
    category_name_docs = list(db.transcripts.find(
        {"category": {"$exists": True}, "category_id": {"$exists": True}},
        {"category": 1, "category_id": 1, "_id": 0}
    ).limit(100))  # Limit to prevent huge output
    
    print(f"Found {len(category_name_docs)} documents with both category and category_id fields")
    
    # Extract potential mappings
    for doc in category_name_docs:
        category = doc.get("category")
        category_id = doc.get("category_id")
        
        # Skip if any field is missing
        if not category or not category_id:
            continue
        
        # Check if category is a ticker symbol
        if is_ticker_symbol(category):
            if is_uuid(category_id):
                if category not in ticker_to_uuid_map:
                    ticker_to_uuid_map[category] = set()
                ticker_to_uuid_map[category].add(category_id)
        
        # Check if category_id is a ticker symbol
        if is_ticker_symbol(category_id):
            if is_uuid(category):
                if category_id not in ticker_to_uuid_map:
                    ticker_to_uuid_map[category_id] = set()
                ticker_to_uuid_map[category_id].add(category)
    
    # Check if we found any mappings
    if ticker_to_uuid_map:
        print("Found potential ticker-to-UUID mappings:")
        for ticker, uuids in ticker_to_uuid_map.items():
            uuids_str = ", ".join(uuids)
            print(f"- {ticker} → {uuids_str}")
    else:
        print("No direct ticker-to-UUID mappings found in transcripts collection")
    
    # 5. Check if we can find a company name to ticker mapping
    print("\nCHECKING FOR COMPANY NAME TO TICKER MAPPING:")
    print("-"*50)
    
    # Check if we can find company name field
    company_docs = list(db.transcripts.find(
        {"company": {"$exists": True}, "category_id": {"$exists": True}},
        {"company": 1, "category_id": 1, "_id": 0}
    ).limit(100))
    
    print(f"Found {len(company_docs)} documents with both company and category_id fields")
    
    company_to_ticker = {}
    company_to_uuid = {}
    
    for doc in company_docs:
        company = doc.get("company")
        category_id = doc.get("category_id")
        
        if not company or not category_id:
            continue
        
        if is_ticker_symbol(category_id):
            if company not in company_to_ticker:
                company_to_ticker[company] = set()
            company_to_ticker[company].add(category_id)
        elif is_uuid(category_id):
            if company not in company_to_uuid:
                company_to_uuid[company] = set()
            company_to_uuid[company].add(category_id)
    
    if company_to_ticker:
        print("Found company-to-ticker mappings:")
        for company, tickers in company_to_ticker.items():
            tickers_str = ", ".join(tickers)
            print(f"- {company} → {tickers_str}")
    else:
        print("No company-to-ticker mappings found")
    
    if company_to_uuid:
        print("\nFound company-to-UUID mappings:")
        for company, uuids in company_to_uuid.items():
            uuids_str = ", ".join(list(uuids)[:2]) + (f" and {len(uuids)-2} more" if len(uuids) > 2 else "")
            print(f"- {company} → {uuids_str}")
    else:
        print("\nNo company-to-UUID mappings found")
    
    # 6. Check if we have filename or other identifiers that might help
    print("\nCHECKING FILENAME FIELD FOR COMPANY INDICATORS:")
    print("-"*50)
    
    # Check for filename field
    filename_docs = list(db.transcripts.find(
        {"filename": {"$exists": True}, "category_id": {"$exists": True}},
        {"filename": 1, "category_id": 1, "_id": 0}
    ).limit(50))
    
    print(f"Found {len(filename_docs)} documents with both filename and category_id fields")
    
    # Look for company identifiers in filenames
    if filename_docs:
        print("Sample filename patterns:")
        for i, doc in enumerate(filename_docs[:10]):
            filename = doc.get("filename")
            category_id = doc.get("category_id")
            print(f"{i+1}. {filename} → {category_id}")
    
    # 7. Check category_id to category name mappings in category_summaries
    print("\nCATEGORY ID TO NAME MAPPINGS IN CATEGORY_SUMMARIES:")
    print("-"*50)
    
    category_name_map = {}
    for cat in category_summaries:
        cat_id = cat.get("category_id")
        cat_name = cat.get("category")
        if cat_id and cat_name:
            category_name_map[cat_id] = cat_name
    
    print(f"Found {len(category_name_map)} category-to-name mappings")
    print("Sample mappings:")
    for cat_id, name in list(category_name_map.items())[:10]:
        print(f"- {cat_id} → {name}")
    
    # 8. Check problematic queries and IDs
    print("\nANALYZING PROBLEMATIC QUERIES:")
    print("-"*50)
    
    # Check for Microsoft UUID in category_name_map
    msft_uuid = "5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18"  # UUID we observed in Microsoft query results
    if msft_uuid in category_name_map:
        print(f"Microsoft UUID maps to category name: {category_name_map[msft_uuid]}")
    else:
        print(f"Microsoft UUID not found in category_name_map")
    
    # Check for Google UUID in category_name_map
    google_uuid = "989b35ce-b8fd-44dc-b53f-2d3233a85706"  # UUID we observed in Google query results
    if google_uuid in category_name_map:
        print(f"Google UUID maps to category name: {category_name_map[google_uuid]}")
    else:
        print(f"Google UUID not found in category_name_map")
    
    # Check for problematic document IDs
    print("\nANALYZING PROBLEMATIC DOCUMENT IDS:")
    print("-"*50)
    
    problem_doc_ids = [
        "e761cbf9-2ca9-42e6-b91e-4867d82a0f3e",  # Expected Microsoft, was Google
        "06cfa48b-3494-44d6-bcfc-b81c325b9881",  # Expected Microsoft, was Google
        "e93b73f9-617f-467f-8cc1-42a1fc5a1cb2"   # Expected Microsoft, was Google
    ]
    
    for doc_id in problem_doc_ids:
        doc = db.transcripts.find_one({"document_id": doc_id})
        if doc:
            category_id = doc.get("category_id")
            category = doc.get("category")
            print(f"Document ID: {doc_id}")
            print(f"- Category ID: {category_id}")
            print(f"- Category: {category}")
            
            # Check if this category_id maps to a ticker
            cat_ticker = None
            for ticker, uuids in ticker_to_uuid_map.items():
                if category_id in uuids:
                    cat_ticker = ticker
                    break
            
            if cat_ticker:
                print(f"- Maps to ticker: {cat_ticker}")
            else:
                print("- No ticker mapping found")
        else:
            print(f"Document ID {doc_id} not found")
    
    # 9. Investigate potential mapping between category_id in transcripts and category_id in category_summaries
    print("\nINVESTIGATING CATEGORY ID MAPPING BETWEEN COLLECTIONS:")
    print("-"*50)
    
    # Create dictionary mapping ticker symbols to UUIDs based on patterns we've observed
    manual_ticker_map = {
        "MSFT": "5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18",  # Microsoft 
        "GOOGL": "989b35ce-b8fd-44dc-b53f-2d3233a85706"  # Google
    }
    
    # Check which ticker symbols in category_summaries correspond to which UUID in transcripts
    ticker_to_docs = {}
    for ticker in ticker_categories:
        uuid_value = manual_ticker_map.get(ticker)
        if uuid_value:
            # Check how many docs have this UUID
            doc_count = db.transcripts.count_documents({"category_id": uuid_value})
            ticker_to_docs[ticker] = {
                "uuid": uuid_value,
                "doc_count": doc_count
            }
    
    if ticker_to_docs:
        print("Ticker symbol to UUID mapping (with document counts):")
        for ticker, info in ticker_to_docs.items():
            print(f"- {ticker} → {info['uuid']} ({info['doc_count']} documents)")
    else:
        print("No ticker to UUID mappings confirmed")
    
    print("\n" + "="*80)
    print("INVESTIGATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main() 