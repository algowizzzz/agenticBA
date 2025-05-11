#!/usr/bin/env python3

from pymongo import MongoClient

def main():
    print("Connecting to MongoDB...")
    client = MongoClient('mongodb://localhost:27017/')
    db = client['earnings_transcripts']
    
    uuid_categories = [
        '077deca3-7e7e-4c48-b848-6f8cfcf84b5c',
        '1598ce28-8bb0-4787-ad40-f5227d3a72a6',
        '5602d908-a5c5-43c1-b888-975dff32a2c4',
        '5d1b4d21-59cb-4ff3-bae1-fe9f1129cf18',
        '989b35ce-b8fd-44dc-b53f-2d3233a85706',
        'f39dc51b-689e-424d-af9b-0ba2d2c0bb86'
    ]
    
    for cat_id in uuid_categories:
        doc = db.transcripts.find_one({'category_id': cat_id})
        if doc and 'transcript_text' in doc:
            # Extract first 1000 characters to look for company name
            sample_text = doc['transcript_text'][:1000]
            
            print(f"\nCategory ID: {cat_id}")
            print(f"Document ID: {doc.get('document_id', 'N/A')}")
            print(f"Filename: {doc.get('filename', 'N/A')}")
            
            # Look for common company references in earnings calls
            if "Microsoft" in sample_text:
                print("COMPANY: MICROSOFT detected")
            elif "Google" in sample_text or "Alphabet" in sample_text:
                print("COMPANY: GOOGLE/ALPHABET detected")
            elif "Facebook" in sample_text or "Meta" in sample_text:
                print("COMPANY: FACEBOOK/META detected")
            elif "Tesla" in sample_text:
                print("COMPANY: TESLA detected")
            elif "NVIDIA" in sample_text or "Nvidia" in sample_text:
                print("COMPANY: NVIDIA detected")
            else:
                print("Sample text (first 200 chars):")
                print(sample_text[:200] + "...")

if __name__ == "__main__":
    main() 