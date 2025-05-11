#!/usr/bin/env python3
"""
MongoDB metadata repair script

This script resolves inconsistency issues between 'transcripts' collection 
(using UUID-style category IDs) and 'document_summaries' collection 
(using ticker symbols) in the earnings_transcripts database.

Two repair options are provided:
1. 'to_tickers': Update transcript documents to use ticker symbols (default)
2. 'to_uuids': Update document_summaries to use UUIDs
3. 'verify': Only verify issues without making changes

Usage:
  python db_metadata_repair.py --method [to_tickers|to_uuids|verify] --backup
"""

import argparse
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Set
from pymongo import MongoClient

def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')  # Test connection
        print("MongoDB connection successful.")
        return client
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None

def create_backup(db, backup_suffix=None):
    """Create backup collections before making changes"""
    print("\nCreating backup collections...")
    
    # Generate timestamp for backup suffix if not provided
    if not backup_suffix:
        backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Backup transcripts collection
    backup_name = f"transcripts_backup_{backup_suffix}"
    if backup_name not in db.list_collection_names():
        db.transcripts.aggregate([{"$out": backup_name}])
        print(f"Backed up transcripts collection to {backup_name}")
    else:
        print(f"Transcript backup {backup_name} already exists")
    
    # Backup document_summaries collection
    backup_name = f"document_summaries_backup_{backup_suffix}"
    if backup_name not in db.list_collection_names():
        db.document_summaries.aggregate([{"$out": backup_name}])
        print(f"Backed up document_summaries collection to {backup_name}")
    else:
        print(f"Document summaries backup {backup_name} already exists")
    
    return backup_suffix

def create_category_mapping(db) -> Dict[str, str]:
    """
    Creates a mapping between UUID category IDs and ticker symbols by analyzing the documents.
    Maps UUID-style IDs to ticker symbols.
    
    Returns dict with format: {uuid: ticker_symbol}
    """
    print("\nCreating category mapping between UUIDs and ticker symbols...")
    
    # Dictionary to map UUID category IDs to ticker symbols
    category_mapping = {}
    
    # Get all documents from document_summaries that have category_id (ticker symbols)
    summaries = list(db.document_summaries.find({}, {"document_id": 1, "category_id": 1, "_id": 0}))
    
    # For each summary, find the corresponding transcript and map its UUID to the ticker
    for summary in summaries:
        doc_id = summary.get("document_id")
        ticker = summary.get("category_id")
        
        if not doc_id or not ticker:
            continue
        
        # Get the UUID from the transcript
        transcript = db.transcripts.find_one({"document_id": doc_id}, {"category_id": 1, "_id": 0})
        if transcript:
            uuid = transcript.get("category_id")
            if uuid and uuid not in category_mapping:
                category_mapping[uuid] = ticker
    
    # Log the mapping count
    print(f"Found {len(category_mapping)} category mappings between UUIDs and ticker symbols")
    
    return category_mapping

def fix_transcripts_to_tickers(db, category_mapping: Dict[str, str]):
    """
    Update all transcripts to use ticker symbols as category_id instead of UUIDs.
    """
    print("\nFixing transcripts collection to use ticker symbols...")
    
    # Get total documents to fix
    total_docs = db.transcripts.count_documents({})
    print(f"Found {total_docs} total documents to check")
    
    # Counter for fixed documents
    fixed_count = 0
    
    # Process each document
    for uuid, ticker in category_mapping.items():
        # Update all documents with this UUID to use the ticker symbol
        result = db.transcripts.update_many(
            {"category_id": uuid},
            {"$set": {"category_id": ticker}}
        )
        
        if result.modified_count > 0:
            print(f"Updated {result.modified_count} documents: {uuid} -> {ticker}")
            fixed_count += result.modified_count
    
    print(f"Fixed {fixed_count} documents in transcripts collection")

def fix_summaries_to_uuids(db, category_mapping: Dict[str, str]):
    """
    Update document_summaries to use UUIDs as category_id instead of ticker symbols.
    """
    print("\nFixing document_summaries collection to use UUIDs...")
    
    # Invert the mapping for reverse lookup
    ticker_to_uuid = {ticker: uuid for uuid, ticker in category_mapping.items()}
    
    # Get total documents to fix
    total_docs = db.document_summaries.count_documents({})
    print(f"Found {total_docs} total documents to check")
    
    # Counter for fixed documents
    fixed_count = 0
    
    # Process each document
    for ticker, uuid in ticker_to_uuid.items():
        # Update all documents with this ticker to use the UUID
        result = db.document_summaries.update_many(
            {"category_id": ticker},
            {"$set": {"category_id": uuid}}
        )
        
        if result.modified_count > 0:
            print(f"Updated {result.modified_count} documents: {ticker} -> {uuid}")
            fixed_count += result.modified_count
    
    print(f"Fixed {fixed_count} documents in document_summaries collection")

def verify_consistency(db):
    """
    Verify consistency between transcripts and document_summaries collections.
    Returns tuple of (inconsistent_count, details)
    """
    print("\nVerifying metadata consistency between collections...")
    
    # Check for mismatches between transcripts and summaries
    mismatch_count = 0
    mismatch_details = []
    
    # Get all document summaries
    all_summaries = list(db.document_summaries.find({}, {"document_id": 1, "category_id": 1, "_id": 0}))
    print(f"Examining {len(all_summaries)} document summaries...")
    
    for summary in all_summaries:
        doc_id = summary.get("document_id")
        summary_category = summary.get("category_id")
        
        # Find matching transcript
        transcript = db.transcripts.find_one({"document_id": doc_id}, {"category_id": 1, "_id": 0})
        if not transcript:
            continue  # Transcript doesn't exist, can't compare
        
        transcript_category = transcript.get("category_id")
        
        # Check if categories match
        if summary_category != transcript_category:
            mismatch_count += 1
            mismatch_details.append({
                "document_id": doc_id,
                "summary_category": summary_category,
                "transcript_category": transcript_category
            })
    
    if mismatch_count == 0:
        print("Verification successful! No mismatches found.")
    else:
        print(f"Verification failed. Found {mismatch_count} category ID mismatches:")
        # Print sample of mismatches
        for i, mismatch in enumerate(mismatch_details[:5]):
            print(f"  {i+1}. Document {mismatch['document_id']}:")
            print(f"     - Summary category: {mismatch['summary_category']}")
            print(f"     - Transcript category: {mismatch['transcript_category']}")
        
        if len(mismatch_details) > 5:
            print(f"     ... and {len(mismatch_details) - 5} more mismatches.")
    
    return mismatch_count, mismatch_details

def main():
    parser = argparse.ArgumentParser(description="Repair MongoDB metadata inconsistencies between collections")
    parser.add_argument("--method", choices=["to_tickers", "to_uuids", "verify"], 
                        default="verify", 
                        help="Repair method: 'to_tickers' updates transcripts to use ticker symbols, "
                             "'to_uuids' updates summaries to use UUIDs, "
                             "'verify' only checks for issues (default)")
    parser.add_argument("--backup", action="store_true", help="Create backup collections before making changes")
    args = parser.parse_args()
    
    print(f"Starting database metadata check/repair process using method: {args.method}")
    start_time = time.time()
    
    # Connect to MongoDB
    client = get_mongodb_client()
    if not client:
        print("Failed to connect to MongoDB. Exiting.")
        return
    
    db = client["earnings_transcripts"]
    
    # Create backup if requested
    backup_suffix = None
    if args.backup:
        backup_suffix = create_backup(db)
    
    # First verify current state
    initial_mismatch_count, initial_details = verify_consistency(db)
    
    if args.method == "verify":
        # Only verify without making changes
        print("\nVerify-only mode completed.")
        
    elif initial_mismatch_count > 0:
        # Proceed with repair
        # Step 1: Create a mapping between UUID category IDs and ticker symbols
        category_mapping = create_category_mapping(db)
        if not category_mapping:
            print("Could not create category mapping. Repair failed.")
            return
        
        # Step 2: Perform the selected repair method
        if args.method == "to_tickers":
            fix_transcripts_to_tickers(db, category_mapping)
        elif args.method == "to_uuids":
            fix_summaries_to_uuids(db, category_mapping)
        
        # Verify the fix
        final_mismatch_count, _ = verify_consistency(db)
        
        if final_mismatch_count == 0:
            print("\n✅ Repair successful! All mismatches have been fixed.")
        else:
            print(f"\n⚠️ Repair partially successful. {initial_mismatch_count - final_mismatch_count} mismatches fixed, "
                  f"but {final_mismatch_count} mismatches remain.")
    else:
        print("\n✅ No mismatches to repair. Database is already consistent.")
    
    # Report execution time
    elapsed_time = time.time() - start_time
    print(f"\nProcess completed in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main() 