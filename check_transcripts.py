#!/usr/bin/env python3
"""
Script to check what document IDs exist in the transcripts collection,
with a focus on 2017 earnings calls for Amazon and Apple
"""

from pymongo import MongoClient
import re

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Check total number of transcripts
    transcript_count = db.transcripts.count_documents({})
    print(f"Total transcripts in database: {transcript_count}")
    
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
    
    amzn_2017_transcripts = list(db.transcripts.find(amzn_2017_query))
    print(f"\nFound {len(amzn_2017_transcripts)} AMZN transcripts from 2017")
    
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
    
    aapl_2017_transcripts = list(db.transcripts.find(aapl_2017_query))
    print(f"Found {len(aapl_2017_transcripts)} AAPL transcripts from 2017")
    
    # Show sample of transcript document IDs with ticker/date
    print("\nSample of available transcripts:")
    all_transcripts = list(db.transcripts.find().limit(10))
    for transcript in all_transcripts:
        doc_id = transcript.get('document_id', 'Unknown')
        ticker = transcript.get('ticker', transcript.get('category_id', 'Unknown'))
        date = transcript.get('date', 'Unknown date')
        print(f"- {doc_id} | {ticker} | {date}")

    # Check if any of these have summaries
    print("\nChecking if sample transcripts have summaries:")
    for transcript in all_transcripts[:5]:  # Just check the first 5
        doc_id = transcript.get('document_id')
        if doc_id:
            summary = db.document_summaries.find_one({'document_id': doc_id})
            print(f"Summary for {doc_id}: {'Found' if summary else 'Not found'}")

if __name__ == '__main__':
    main() 