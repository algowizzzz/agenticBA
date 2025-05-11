#!/usr/bin/env python3
from pymongo import MongoClient

def main():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    # Check categories collection
    print("\nCATEGORIES COLLECTION:")
    print("-" * 50)
    try:
        categories = list(db.categories.find({}, {'_id': 0}))
        if categories:
            for cat in categories:
                print(cat)
        else:
            print("No documents found in categories collection")
    except Exception as e:
        print(f"Error querying categories: {e}")
    
    # Get UUID to ticker mapping
    print("\nCATEGORY ID MAPPING:")
    print("-" * 50)
    try:
        # Try to get category IDs from transcripts collection
        category_ids = db.transcripts.distinct('category_id')
        print(f"Found {len(category_ids)} unique category IDs in transcripts collection:")
        for cat_id in category_ids:
            print(f"- {cat_id}")
            
            # Try to find a document with this category ID
            doc = db.transcripts.find_one({'category_id': cat_id}, 
                                         {'document_id': 1, 'filename': 1, '_id': 0})
            if doc and 'filename' in doc:
                print(f"  Sample filename: {doc['filename']}")
    except Exception as e:
        print(f"Error querying transcripts: {e}")
    
    # Check for Microsoft specifically
    print("\nMICROSOFT SPECIFIC:")
    print("-" * 50)
    try:
        # Try different potential category IDs for Microsoft
        for msft_id in ['MSFT', 'Microsoft', 'microsoft', '5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18']:
            count = db.transcripts.count_documents({'category_id': msft_id})
            if count > 0:
                print(f"Found {count} transcripts with category_id: {msft_id}")
                doc = db.transcripts.find_one({'category_id': msft_id})
                if doc:
                    print(f"Sample document ID: {doc.get('document_id')}")
                    print(f"Sample filename: {doc.get('filename')}")
            else:
                print(f"No transcripts found with category_id: {msft_id}")
    except Exception as e:
        print(f"Error querying Microsoft transcripts: {e}")
    
    # Check category summaries
    print("\nCATEGORY SUMMARIES:")
    print("-" * 50)
    try:
        summaries = list(db.category_summaries.find({}, {'category_id': 1, '_id': 0}))
        if summaries:
            print(f"Found {len(summaries)} category summaries:")
            for summary in summaries:
                print(f"- {summary}")
        else:
            print("No documents found in category_summaries collection")
    except Exception as e:
        print(f"Error querying category summaries: {e}")

if __name__ == "__main__":
    main() 