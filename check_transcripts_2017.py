#!/usr/bin/env python3
"""
Script to specifically examine the 2017 transcripts for AMZN and AAPL
and check if they have corresponding summaries
"""

from pymongo import MongoClient

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
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
    
    print("==== AMAZON (AMZN) 2017 TRANSCRIPTS ====")
    amzn_2017_transcripts = list(db.transcripts.find(amzn_2017_query))
    print(f"Found {len(amzn_2017_transcripts)} AMZN transcripts from 2017")
    
    for transcript in amzn_2017_transcripts:
        doc_id = transcript.get('document_id', 'Unknown')
        date = transcript.get('date', 'Unknown date')
        quarter = transcript.get('quarter', transcript.get('fiscal_quarter', 'Unknown'))
        
        # Check if this transcript has a summary
        summary = db.document_summaries.find_one({'document_id': doc_id})
        summary_status = "✓ Has summary" if summary else "✗ No summary"
        
        print(f"- {doc_id} | Q{quarter} | {date} | {summary_status}")
    
    print("\n==== APPLE (AAPL) 2017 TRANSCRIPTS ====")
    aapl_2017_transcripts = list(db.transcripts.find(aapl_2017_query))
    print(f"Found {len(aapl_2017_transcripts)} AAPL transcripts from 2017")
    
    for transcript in aapl_2017_transcripts:
        doc_id = transcript.get('document_id', 'Unknown')
        date = transcript.get('date', 'Unknown date')
        quarter = transcript.get('quarter', transcript.get('fiscal_quarter', 'Unknown'))
        
        # Check if this transcript has a summary
        summary = db.document_summaries.find_one({'document_id': doc_id})
        summary_status = "✓ Has summary" if summary else "✗ No summary"
        
        print(f"- {doc_id} | Q{quarter} | {date} | {summary_status}")
    
    # Check if specific Q1 2017 transcripts mentioned in our test exist
    print("\n==== CHECKING SPECIFIC DOCUMENT IDs FROM TEST ====")
    test_ids = [
        '5d8d8a7d-d8b4-4c7f-9c9d-f1c6d3f0d9c4',
        '6f8d5d7b-d7f4-4a6f-9c1a-e6f5b3c8f9c5'
    ]
    for doc_id in test_ids:
        transcript = db.transcripts.find_one({'document_id': doc_id})
        if transcript:
            ticker = transcript.get('ticker', transcript.get('category_id', 'Unknown'))
            date = transcript.get('date', 'Unknown date')
            print(f"Found transcript: {doc_id} | {ticker} | {date}")
        else:
            print(f"No transcript found with ID: {doc_id}")

if __name__ == '__main__':
    main() 