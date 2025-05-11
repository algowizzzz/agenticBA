#!/usr/bin/env python3
"""
Script to check if specific document IDs have summaries in the MongoDB database
"""

from pymongo import MongoClient

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Document IDs from our test
    test_ids = [
        '5d8d8a7d-d8b4-4c7f-9c9d-f1c6d3f0d9c4',
        '6f8d5d7b-d7f4-4a6f-9c1a-e6f5b3c8f9c5'
    ]
    
    print('Checking specific document IDs:')
    for doc_id in test_ids:
        summary = db.document_summaries.find_one({'document_id': doc_id})
        print(f'Summary for {doc_id}: {"Found" if summary else "Not found"}')
    
    # Show some document IDs that do have summaries
    print('\nSample of document IDs with summaries:')
    sample_summaries = list(db.document_summaries.find().limit(5))
    for summary in sample_summaries:
        if 'document_id' in summary:
            print(f"- {summary['document_id']}")
    
    # Check if these documents exist in the transcripts collection
    print('\nChecking if documents exist in transcripts collection:')
    for doc_id in test_ids:
        transcript = db.transcripts.find_one({'document_id': doc_id})
        print(f'Transcript for {doc_id}: {"Found" if transcript else "Not found"}')

if __name__ == '__main__':
    main() 