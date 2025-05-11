#!/usr/bin/env python3
"""
Direct test script for querying Microsoft Q1 2017 documents 
with Claude 3 Haiku without depending on problematic imports
"""

import os
import logging
import json
from pymongo import MongoClient
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get API key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY not found in environment")
    exit(1)

# Initialize LLM with Claude 3 Haiku
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    temperature=0.1,
    max_tokens=1500,
    anthropic_api_key=ANTHROPIC_API_KEY
)

# Query
test_query = "Give me a summary of Microsoft's Q1 2017 earnings call"

def get_msft_document_ids(limit=3):
    """Find relevant Microsoft document IDs from the database"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # First, try to find document IDs by searching for MSFT 2017 Q1
        pipeline = [
            {
                "$match": {
                    "$and": [
                        {"company_ticker": "MSFT"}, 
                        {"$or": [
                            {"call_title": {"$regex": "Q1.*2017", "$options": "i"}},
                            {"call_title": {"$regex": "2017.*Q1", "$options": "i"}},
                            {"call_date": {"$regex": "2017", "$options": "i"}}
                        ]}
                    ]
                }
            },
            {"$project": {"document_id": 1, "call_title": 1, "call_date": 1, "_id": 0}},
            {"$limit": limit}
        ]
        
        docs = list(db.transcripts.aggregate(pipeline))
        
        # If we found documents, return their information
        if docs:
            logger.info(f"Found {len(docs)} Microsoft Q1 2017 documents")
            return docs
        else:
            # If we didn't find specific Q1 2017 documents, just get any Microsoft documents
            logger.info("No specific Q1 2017 documents found, fetching general Microsoft documents")
            docs = list(db.transcripts.find({"company_ticker": "MSFT"}, 
                                           {"document_id": 1, "call_title": 1, "call_date": 1, "_id": 0})
                       .limit(limit))
            return docs
    
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []

def get_any_document_ids(limit=3):
    """Find any available document IDs from the database"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # Try to find any documents with document_id
        docs = list(db.transcripts.find({}, 
                                    {"document_id": 1, "call_title": 1, "call_date": 1, "company_ticker": 1, "_id": 0})
                   .limit(limit))
        
        if docs:
            logger.info(f"Found {len(docs)} documents")
            return docs
        else:
            logger.error("No documents found in the database")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []

def get_document_summary(document_id):
    """Get the document summary if it exists"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # Try to find the document summary
        summary = db.document_summaries.find_one({"document_id": document_id})
        
        if summary and "summary" in summary:
            logger.info(f"Found summary for document {document_id}")
            return summary.get("summary")
        else:
            logger.info(f"No summary found for document {document_id}")
            return None
    except Exception as e:
        logger.error(f"Error fetching document summary: {e}")
        return None

def get_document_content(document_id):
    """Get the full document content"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # Try to find the full document
        document = db.transcripts.find_one({"document_id": document_id})
        
        if document and "content" in document:
            logger.info(f"Found content for document {document_id}")
            return document.get("content")
        else:
            logger.info(f"No content found for document {document_id}")
            return None
    except Exception as e:
        logger.error(f"Error fetching document content: {e}")
        return None

def analyze_with_summaries(query, documents):
    """Analyze document summaries using Claude 3 Haiku"""
    # Get summaries for documents
    documents_with_summaries = []
    
    for doc in documents:
        document_id = doc.get('document_id')
        summary = get_document_summary(document_id)
        if summary:
            documents_with_summaries.append({
                "document_id": document_id,
                "title": doc.get('call_title', 'Unknown Title'),
                "date": doc.get('call_date', 'Unknown Date'),
                "summary": summary
            })
    
    if not documents_with_summaries:
        logger.warning("No document summaries found")
        return "No document summaries found. Try analyzing full documents instead."
    
    # Create prompt with summaries
    prompt = f"""You are an expert financial analyst tasked with analyzing earnings call transcripts.
    
Query: {query}

Below are summaries of earnings call transcripts. Please analyze these summaries to provide a comprehensive answer to the query.

"""
    
    for idx, doc in enumerate(documents_with_summaries, 1):
        prompt += f"""
Document {idx}:
Title: {doc.get('title')}
Date: {doc.get('date')}
Document ID: {doc.get('document_id')}

Summary:
{doc.get('summary')}

"""
    
    prompt += """
Based on the summaries above, please provide a comprehensive answer to the query. 
Focus on facts and information found in the transcripts. Structure your response
in a clear, organized format with appropriate headings.
"""
    
    # Call Claude 3 Haiku
    logger.info("Calling Claude 3 Haiku to analyze document summaries")
    response = llm.invoke(prompt)
    
    return response.content

def analyze_full_document(query, document):
    """Analyze the full document content using Claude 3 Haiku"""
    document_id = document.get('document_id')
    content = get_document_content(document_id)
    
    if not content:
        return f"Could not find content for document {document_id}"
    
    # Create a prompt with the document content
    prompt = f"""You are an expert financial analyst tasked with analyzing earnings call transcripts.
    
Query: {query}

Below is the text of an earnings call transcript. Please analyze this transcript to provide a comprehensive answer to the query.

Document Title: {document.get('call_title', 'Unknown Title')}
Document Date: {document.get('call_date', 'Unknown Date')}
Document ID: {document_id}

Transcript:
{content}

Based on the transcript above, please provide a comprehensive answer to the query. 
Focus on facts and information found in the transcript. Structure your response
in a clear, organized format with appropriate headings.
"""
    
    # Call Claude 3 Haiku - the transcript might be long, so we need to handle potential issues
    try:
        logger.info("Calling Claude 3 Haiku to analyze full document")
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        # If the document is too large, we might need to truncate it
        truncated_content = content[:30000] + "...[CONTENT TRUNCATED DUE TO LENGTH]"
        
        # Try again with truncated content
        try:
            truncated_prompt = prompt.replace(content, truncated_content)
            logger.info("Retrying with truncated content")
            response = llm.invoke(truncated_prompt)
            return response.content + "\n\n[Note: The analysis is based on a truncated version of the transcript due to length limitations.]"
        except Exception as e2:
            logger.error(f"Error even with truncated content: {e2}")
            return f"Error analyzing document: {str(e2)}"

def main():
    # First try to get Microsoft document information
    documents = get_msft_document_ids()
    
    # If no Microsoft documents found, try any documents
    if not documents:
        logger.warning("No Microsoft documents found. Trying any available documents.")
        documents = get_any_document_ids()
    
    if not documents:
        logger.error("No documents found. Exiting.")
        return
    
    # Print found documents
    print("\nFound documents:")
    for idx, doc in enumerate(documents, 1):
        print(f"{idx}. {doc.get('company_ticker', 'Unknown Company')} - {doc.get('call_title', 'Unknown')} - {doc.get('call_date', 'Unknown Date')}")
        print(f"   Document ID: {doc.get('document_id', 'Unknown ID')}")
    
    # Update query if not using Microsoft documents
    global test_query
    if documents and documents[0].get('company_ticker') != 'MSFT':
        company = documents[0].get('company_ticker', '')
        call_title = documents[0].get('call_title', '')
        test_query = f"Give me a summary of {company}'s earnings call: {call_title}"
        print(f"\nUpdated query to: {test_query}")
    
    # Try to analyze using summaries first (Layer 1)
    print("\n===== LAYER 1: Document Summaries Analysis =====")
    summary_analysis = analyze_with_summaries(test_query, documents)
    print("\nSummary Analysis Result:")
    print(summary_analysis)
    
    # Then analyze the first document in full (Layer 2)
    if documents:
        print("\n===== LAYER 2: Full Document Analysis =====")
        full_analysis = analyze_full_document(test_query, documents[0])
        print("\nFull Document Analysis Result:")
        print(full_analysis)

if __name__ == "__main__":
    main() 