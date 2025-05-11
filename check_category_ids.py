#!/usr/bin/env python3

from pymongo import MongoClient
import re

def is_uuid_format(id_str):
    """Check if string resembles a UUID format."""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    return bool(uuid_pattern.match(id_str.lower()))

def is_ticker_format(id_str):
    """Check if string resembles a stock ticker format (all caps, 1-5 chars)."""
    return id_str.isupper() and 1 <= len(id_str) <= 5

def main():
    print("Connecting to MongoDB...")
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Check transcripts collection
    print("\nTRANSCRIPTS COLLECTION CATEGORIES:")
    print("--------------------------------------------------")
    uuid_style = 0
    ticker_style = 0
    other_style = 0
    
    uuid_examples = []
    ticker_examples = []
    other_examples = []
    
    for doc in db.transcripts.find({}, {'document_id': 1, 'category_id': 1, '_id': 0}):
        if 'category_id' in doc:
            category_id = doc['category_id']
            if is_uuid_format(category_id):
                uuid_style += 1
                if len(uuid_examples) < 3:
                    uuid_examples.append(doc)
            elif is_ticker_format(category_id):
                ticker_style += 1
                if len(ticker_examples) < 3:
                    ticker_examples.append(doc)
            else:
                other_style += 1
                if len(other_examples) < 3:
                    other_examples.append(doc)
    
    print(f"UUID-style categories: {uuid_style}")
    if uuid_examples:
        print("Examples:")
        for ex in uuid_examples:
            print(f"  {ex}")
    
    print(f"\nTicker-style categories: {ticker_style}")
    if ticker_examples:
        print("Examples:")
        for ex in ticker_examples:
            print(f"  {ex}")
    
    print(f"\nOther format categories: {other_style}")
    if other_examples:
        print("Examples:")
        for ex in other_examples:
            print(f"  {ex}")
    
    # Check document_summaries collection
    print("\nDOCUMENT SUMMARIES COLLECTION CATEGORIES:")
    print("--------------------------------------------------")
    uuid_style = 0
    ticker_style = 0
    other_style = 0
    
    uuid_examples = []
    ticker_examples = []
    other_examples = []
    
    for doc in db.document_summaries.find({}, {'document_id': 1, 'category_id': 1, '_id': 0}):
        if 'category_id' in doc:
            category_id = doc['category_id']
            if is_uuid_format(category_id):
                uuid_style += 1
                if len(uuid_examples) < 3:
                    uuid_examples.append(doc)
            elif is_ticker_format(category_id):
                ticker_style += 1
                if len(ticker_examples) < 3:
                    ticker_examples.append(doc)
            else:
                other_style += 1
                if len(other_examples) < 3:
                    other_examples.append(doc)
    
    print(f"UUID-style categories: {uuid_style}")
    if uuid_examples:
        print("Examples:")
        for ex in uuid_examples:
            print(f"  {ex}")
    
    print(f"\nTicker-style categories: {ticker_style}")
    if ticker_examples:
        print("Examples:")
        for ex in ticker_examples:
            print(f"  {ex}")
    
    print(f"\nOther format categories: {other_style}")
    if other_examples:
        print("Examples:")
        for ex in other_examples:
            print(f"  {ex}")

if __name__ == "__main__":
    main() 