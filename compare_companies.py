#!/usr/bin/env python3

from pymongo import MongoClient
import json
from datetime import datetime

def main():
    print("Connecting to MongoDB...")
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Company IDs
    amzn_id = 'AMZN'
    msft_id = '5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18'
    
    print("\n" + "="*80)
    print("COMPARISON: AMAZON (AMZN) vs MICROSOFT (MSFT)")
    print("="*80)
    
    # Basic stats
    print("\nBASIC STATS:")
    print("-"*40)
    amzn_count = db.transcripts.count_documents({'category_id': amzn_id})
    msft_count = db.transcripts.count_documents({'category_id': msft_id})
    amzn_summary_count = db.document_summaries.count_documents({'category_id': amzn_id})
    msft_summary_count = db.document_summaries.count_documents({'category_id': msft_id})
    
    print(f"Amazon transcripts: {amzn_count}")
    print(f"Amazon summaries: {amzn_summary_count}")
    print(f"Microsoft transcripts: {msft_count}")
    print(f"Microsoft summaries: {msft_summary_count}")
    
    # Date ranges
    print("\nDATE RANGES:")
    print("-"*40)
    
    # Amazon
    oldest_amzn = db.transcripts.find_one({'category_id': amzn_id}, sort=[('date', 1)])
    newest_amzn = db.transcripts.find_one({'category_id': amzn_id}, sort=[('date', -1)])
    
    if oldest_amzn and newest_amzn:
        old_date = oldest_amzn.get('date')
        if isinstance(old_date, datetime):
            old_date = old_date.strftime('%Y-%m-%d')
        new_date = newest_amzn.get('date')
        if isinstance(new_date, datetime):
            new_date = new_date.strftime('%Y-%m-%d')
            
        print(f"Amazon: {old_date} to {new_date}")
        print(f"        Q{oldest_amzn.get('quarter')} {oldest_amzn.get('fiscal_year')} to Q{newest_amzn.get('quarter')} {newest_amzn.get('fiscal_year')}")
    
    # Microsoft
    oldest_msft = db.transcripts.find_one({'category_id': msft_id}, sort=[('date', 1)])
    newest_msft = db.transcripts.find_one({'category_id': msft_id}, sort=[('date', -1)])
    
    if oldest_msft and newest_msft:
        old_date = oldest_msft.get('date')
        if isinstance(old_date, datetime):
            old_date = old_date.strftime('%Y-%m-%d')
        new_date = newest_msft.get('date')
        if isinstance(new_date, datetime):
            new_date = new_date.strftime('%Y-%m-%d')
            
        print(f"Microsoft: {old_date} to {new_date}")
        print(f"           Q{oldest_msft.get('quarter')} {oldest_msft.get('fiscal_year')} to Q{newest_msft.get('quarter')} {newest_msft.get('fiscal_year')}")
    
    # Latest earnings call info
    print("\nLATEST EARNINGS CALL INFORMATION:")
    print("-"*40)
    
    # Amazon latest
    if newest_amzn:
        print(f"Amazon (Q{newest_amzn.get('quarter')} {newest_amzn.get('fiscal_year')}):")
        amzn_summary = None
        if 'document_id' in newest_amzn:
            amzn_summary = db.document_summaries.find_one({'document_id': newest_amzn['document_id']})
        
        if amzn_summary and 'summary_text' in amzn_summary:
            # Extract first 10 lines
            summary_lines = amzn_summary['summary_text'].split('\n')[:10]
            print('\n'.join(summary_lines))
            print("...")
        else:
            # Extract part of the transcript
            if 'transcript_text' in newest_amzn:
                print("Excerpt from transcript:")
                # Find financial highlights section
                text = newest_amzn['transcript_text']
                start_idx = text.find("Financial Results")
                if start_idx == -1:
                    start_idx = text.find("financial results")
                if start_idx == -1:
                    start_idx = 0
                excerpt = text[start_idx:start_idx+500]
                print(excerpt + "...")
    
    # Microsoft latest
    if newest_msft:
        print(f"\nMicrosoft (Q{newest_msft.get('quarter')} {newest_msft.get('fiscal_year')}):")
        msft_summary = None
        if 'document_id' in newest_msft:
            msft_summary = db.document_summaries.find_one({'document_id': newest_msft['document_id']})
        
        if msft_summary and 'summary_text' in msft_summary:
            # Extract first 10 lines
            summary_lines = msft_summary['summary_text'].split('\n')[:10]
            print('\n'.join(summary_lines))
            print("...")
        else:
            # Extract part of the transcript
            if 'transcript_text' in newest_msft:
                print("Excerpt from transcript:")
                # Find financial highlights section
                text = newest_msft['transcript_text']
                start_idx = text.find("Financial Results")
                if start_idx == -1:
                    start_idx = text.find("financial results")
                if start_idx == -1:
                    start_idx = 0
                excerpt = text[start_idx:start_idx+500]
                print(excerpt + "...")

if __name__ == "__main__":
    main() 