#!/usr/bin/env python3
"""
MongoDB Metadata Report Generator

This script generates a detailed report about the MongoDB database 
metadata structure, including collections, document counts, consistency 
between collections, and company/category distributions.

Usage:
  python db_metadata_report.py [--output OUTPUT_FILE] [--format {text,json}]
"""

import argparse
import json
import time
from datetime import datetime
from typing import Dict, List, Any
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

def get_collection_stats(db):
    """Get basic stats about collections in the database."""
    stats = {}
    
    # Get counts for each collection
    collections = db.list_collection_names()
    for collection_name in collections:
        # Skip backup collections
        if "backup" in collection_name:
            continue
        
        count = db[collection_name].count_documents({})
        stats[collection_name] = count
    
    return stats

def get_category_distribution(db):
    """Get distribution of documents by category."""
    category_distribution = {}
    
    # Get unique categories from transcripts collection
    categories = db.transcripts.distinct("category_id")
    
    for category in categories:
        # Count documents in transcripts collection
        transcript_count = db.transcripts.count_documents({"category_id": category})
        
        # Count documents in summaries collection
        summary_count = db.document_summaries.count_documents({"category_id": category})
        
        # Check if category has a synthesized summary
        category_summary = db.category_summaries.find_one({"category_id": category})
        has_category_summary = bool(category_summary)
        
        category_distribution[category] = {
            "transcript_count": transcript_count,
            "document_summary_count": summary_count,
            "has_category_summary": has_category_summary
        }
    
    return category_distribution

def get_date_range_info(db):
    """Get date range information for documents."""
    # Find oldest and newest documents
    oldest = db.transcripts.find_one({}, sort=[("date", 1)])
    newest = db.transcripts.find_one({}, sort=[("date", -1)])
    
    # Format date based on type
    def format_date(date_value):
        if not date_value:
            return "N/A"
        
        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")
        elif isinstance(date_value, str):
            # Try to parse the string as date if it's not already formatted
            try:
                return datetime.strptime(date_value[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return date_value
        else:
            return str(date_value)
    
    date_range = {
        "oldest_document": {
            "date": format_date(oldest.get("date")) if oldest else "N/A",
            "document_id": oldest.get("document_id") if oldest else None,
            "category_id": oldest.get("category_id") if oldest else None
        },
        "newest_document": {
            "date": format_date(newest.get("date")) if newest else "N/A",
            "document_id": newest.get("document_id") if newest else None,
            "category_id": newest.get("category_id") if newest else None
        }
    }
    
    return date_range

def check_consistency(db):
    """Check consistency between transcripts and document_summaries collections."""
    # Check for mismatches between transcripts and summaries
    transcript_count = db.transcripts.count_documents({})
    summary_count = db.document_summaries.count_documents({})
    
    # Find documents in transcripts without a summary
    transcripts_without_summary = []
    transcript_ids = set(db.transcripts.distinct("document_id"))
    summary_ids = set(db.document_summaries.distinct("document_id"))
    transcripts_without_summary = list(transcript_ids - summary_ids)
    
    # Find summaries without a transcript
    summaries_without_transcript = list(summary_ids - transcript_ids)
    
    # Check for category ID mismatches
    mismatch_count = 0
    mismatch_details = []
    
    all_summaries = list(db.document_summaries.find({}, {"document_id": 1, "category_id": 1, "_id": 0}))
    for summary in all_summaries:
        doc_id = summary.get("document_id")
        summary_category = summary.get("category_id")
        
        transcript = db.transcripts.find_one({"document_id": doc_id}, {"category_id": 1, "_id": 0})
        if transcript:
            transcript_category = transcript.get("category_id")
            
            if summary_category != transcript_category:
                mismatch_count += 1
                mismatch_details.append({
                    "document_id": doc_id,
                    "summary_category": summary_category,
                    "transcript_category": transcript_category
                })
    
    consistency_report = {
        "transcript_count": transcript_count,
        "summary_count": summary_count,
        "transcripts_without_summary_count": len(transcripts_without_summary),
        "summaries_without_transcript_count": len(summaries_without_transcript),
        "category_id_mismatches": mismatch_count,
        "sample_mismatches": mismatch_details[:5] if mismatch_details else []
    }
    
    # Add sample documents without summaries (limited to 5)
    if transcripts_without_summary:
        sample_docs = []
        for doc_id in transcripts_without_summary[:5]:
            doc = db.transcripts.find_one({"document_id": doc_id}, 
                                         {"document_id": 1, "category_id": 1, "date": 1, "_id": 0})
            if doc:
                # Handle date formatting
                date_value = doc.get("date")
                if date_value:
                    if isinstance(date_value, datetime):
                        doc["date"] = date_value.strftime("%Y-%m-%d")
                    elif isinstance(date_value, str):
                        try:
                            doc["date"] = datetime.strptime(date_value[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
                        except (ValueError, TypeError):
                            doc["date"] = date_value
                    else:
                        doc["date"] = str(date_value)
                sample_docs.append(doc)
        
        consistency_report["sample_transcripts_without_summary"] = sample_docs
    else:
        consistency_report["sample_transcripts_without_summary"] = []
    
    return consistency_report

def generate_report(db, format="text"):
    """Generate a comprehensive report about the database."""
    report = {}
    
    print("Generating MongoDB metadata report...")
    
    # Get collection stats
    print("Getting collection statistics...")
    report["collection_stats"] = get_collection_stats(db)
    
    # Get category distribution 
    print("Analyzing category distribution...")
    report["category_distribution"] = get_category_distribution(db)
    
    # Get date range information
    print("Getting document date range information...")
    report["date_range"] = get_date_range_info(db)
    
    # Check consistency
    print("Checking consistency between collections...")
    report["consistency"] = check_consistency(db)
    
    # Add metadata
    report["metadata"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "database": "earnings_transcripts"
    }
    
    return report

def output_report(report, format="text", output_file=None):
    """Output the report in the specified format."""
    if format == "json":
        # Convert any datetime objects to strings
        report_json = json.dumps(report, indent=2, default=str)
        
        if output_file:
            with open(output_file, "w") as f:
                f.write(report_json)
            print(f"Report saved to {output_file}")
        else:
            print(report_json)
    else:
        # Text format (human-readable)
        if output_file:
            with open(output_file, "w") as f:
                output_text_report(report, f)
            print(f"Report saved to {output_file}")
        else:
            output_text_report(report)

def output_text_report(report, file=None):
    """Output the report in a human-readable text format."""
    def write(text):
        if file:
            file.write(text + "\n")
        else:
            print(text)
    
    write("=" * 80)
    write(f"MONGODB METADATA REPORT - {report['metadata']['generated_at']}")
    write("=" * 80)
    
    # Collection stats
    write("\nCOLLECTION STATISTICS:")
    write("-" * 50)
    for collection, count in report["collection_stats"].items():
        write(f"{collection}: {count} documents")
    
    # Consistency
    consistency = report["consistency"]
    write("\nCONSISTENCY REPORT:")
    write("-" * 50)
    write(f"Transcripts: {consistency['transcript_count']}")
    write(f"Document Summaries: {consistency['summary_count']}")
    write(f"Transcripts without summary: {consistency['transcripts_without_summary_count']}")
    write(f"Summaries without transcript: {consistency['summaries_without_transcript_count']}")
    write(f"Category ID mismatches: {consistency['category_id_mismatches']}")
    
    if consistency['category_id_mismatches'] > 0:
        write("\nSample category ID mismatches:")
        for mismatch in consistency['sample_mismatches']:
            write(f"  - Document {mismatch['document_id']}:")
            write(f"    Summary category: {mismatch['summary_category']}")
            write(f"    Transcript category: {mismatch['transcript_category']}")
    
    # Date range
    write("\nDATE RANGE:")
    write("-" * 50)
    oldest = report["date_range"]["oldest_document"]
    newest = report["date_range"]["newest_document"]
    write(f"Oldest document: {oldest['date']} (ID: {oldest['document_id']}, Category: {oldest['category_id']})")
    write(f"Newest document: {newest['date']} (ID: {newest['document_id']}, Category: {newest['category_id']})")
    
    # Category distribution
    write("\nCATEGORY DISTRIBUTION:")
    write("-" * 50)
    categories = report["category_distribution"]
    for category, stats in categories.items():
        write(f"- {category}:")
        write(f"  Transcripts: {stats['transcript_count']}")
        write(f"  Document Summaries: {stats['document_summary_count']}")
        write(f"  Has Category Summary: {'Yes' if stats['has_category_summary'] else 'No'}")
    
    write("\n" + "=" * 80)
    write("END OF REPORT")
    write("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Generate MongoDB metadata report")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # Connect to MongoDB
    client = get_mongodb_client()
    if not client:
        print("Failed to connect to MongoDB. Exiting.")
        return
    
    db = client["earnings_transcripts"]
    
    # Generate report
    report = generate_report(db, args.format)
    
    # Output report
    output_report(report, args.format, args.output)
    
    elapsed_time = time.time() - start_time
    print(f"\nReport generated in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main() 