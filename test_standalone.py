#!/usr/bin/env python3
"""
Standalone Test Script for Two-Layered Document Analysis 

Tests the concept of two-layered document analysis without package dependencies.
Uses a mock LLM response to avoid API calls.
"""

import os
import json
import logging
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Utility Functions ---

def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')
        logger.info("MongoDB connection successful.")
        return client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None, None, None  # Indicate failure
    db = client['earnings_transcripts']
    return db, db.transcripts, db.document_summaries  # Return handles to collections

def get_document_summary(summaries_coll, document_id: str):
    """Retrieve summary for a document ID."""
    try:
        # Try first with document_id
        summary_doc = summaries_coll.find_one({"document_id": document_id})
        if not summary_doc:
            # Try with transcript_uuid
            summary_doc = summaries_coll.find_one({"transcript_uuid": document_id})
        
        if summary_doc:
            # Check for different summary content structures
            if "summary_content" in summary_doc:
                # New structured summary content (JSON)
                summary_content = summary_doc["summary_content"]
                
                # Format summary content as text
                ticker = summary_doc.get("ticker", "Unknown")
                quarter = summary_doc.get("quarter", "Unknown")
                year = summary_doc.get("year", "Unknown")
                
                text = f"SUMMARY FOR: {ticker} Q{quarter} {year} Earnings Call\n\n"
                
                # Add narrative overview
                narrative = summary_content.get("narrative_overview", "")
                if narrative:
                    text += f"OVERVIEW:\n{narrative}\n\n"
                    
                # Add sentiment
                sentiment = summary_content.get("overall_sentiment", {})
                rating = sentiment.get("rating", "") if sentiment else ""
                if rating:
                    text += f"SENTIMENT: {rating}\n\n"
                
                return text, None
                
            elif "summary_text" in summary_doc:
                # Old plain text summary
                return summary_doc["summary_text"], None
            else:
                return None, "Summary content structure not recognized"
        else:
            return None, "No summary found"
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return None, str(e)

def get_document_full_text(transcripts_coll, document_id: str):
    """Retrieve full transcript text for a document ID."""
    try:
        transcript_doc = transcripts_coll.find_one({"document_id": document_id})
        
        if transcript_doc and "transcript_text" in transcript_doc:
            return transcript_doc["transcript_text"], None
        else:
            return None, "No transcript found"
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return None, str(e)

def get_document_metadata(transcripts_coll, document_id: str):
    """Fetch document metadata."""
    try:
        transcript_doc = transcripts_coll.find_one({"document_id": document_id})
        if not transcript_doc:
            return {"error": f"Document not found: {document_id}"}
        
        return {
            "document_id": document_id,
            "ticker": transcript_doc.get("category", "Unknown"),
            "quarter": transcript_doc.get("quarter", "Unknown"),
            "year": transcript_doc.get("fiscal_year", "Unknown"),
            "document_name": f"{transcript_doc.get('category', 'Unknown')} Q{transcript_doc.get('quarter', 'Unknown')} {transcript_doc.get('fiscal_year', 'Unknown')} Earnings Call"
        }
    except Exception as e:
        logger.error(f"Error fetching metadata: {e}")
        return {"error": str(e)}

def chunk_document_text(text, chunk_size=80000):
    """Split document text into chunks."""
    if not text:
        return []
    
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    
    return chunks

# --- Mock LLM Response ---

def mock_llm_response(prompt):
    """Mock LLM response to avoid API calls."""
    # Extract query from prompt
    query_line = ""
    for line in prompt.split('\n'):
        if line.startswith("QUERY:"):
            query_line = line
            break
    
    if "revenue" in query_line.lower() or "business" in query_line.lower() or "segment" in query_line.lower():
        return """Based on the document summaries, here is an analysis of revenue growth and key business segments:

Revenue Growth:
- Amazon reported strong revenue growth in Q4 2019, with net sales exceeding guidance at $87.4 billion
- AWS showed continued growth with revenue of $10+ billion (annual run rate)
- Third-party seller services grew by 31% in revenue, showing strong marketplace performance
- Subscription services revenue grew by 32% year-over-year

Key Business Segments:
1. North American Retail
   - Showed accelerated growth due to one-day shipping program
   - Strong holiday season performance from mid-November onward

2. AWS (Amazon Web Services)
   - Remains a key growth driver with expanding features and geographic presence
   - Now in 69 availability zones across 22 geographic regions
   - Broad-based growth across industries and enterprise customers

3. Third-Party Marketplace
   - Increased participation in one-day delivery program
   - FBA (Fulfillment by Amazon) showing stronger growth than MFN (Merchant Fulfilled Network)

4. International Retail
   - Also benefiting from one-day shipping improvements
   - Continuing to invest in international growth

These segments collectively show Amazon's diversified business model with growth across multiple revenue streams."""
    
    elif "outlook" in query_line.lower() or "guidance" in query_line.lower():
        return """Based on the document transcript, Amazon provided the following information about future outlook and guidance during their Q4 2019 earnings call:

1. Q1 2020 Revenue Guidance:
   - Net sales are expected to be between $69 billion and $73 billion
   - This represents growth of 16% to 22% compared to Q1 2019

2. Q1 2020 Operating Income Guidance:
   - Operating income is expected to be between $3.0 billion and $4.2 billion
   - This compares with $4.4 billion in Q1 2019
   - The guidance includes approximately $800 million in costs related to COVID-19

3. Key Investment Areas for 2020:
   - Continued investment in the one-day shipping program
   - Further expansion of AWS infrastructure and capabilities
   - Ongoing investments in devices and digital content

4. COVID-19 Impact:
   - Management acknowledged uncertainty around COVID-19's impact on operations
   - Expecting increased costs related to employee safety measures
   - Anticipating potential supply chain disruptions, especially for hardware products

5. Long-term Strategy:
   - Continued focus on customer experience and Prime membership growth
   - Expansion of fulfillment and logistics capabilities
   - Emphasis on AWS's leadership position in the cloud market

The management team maintained their typically conservative approach to guidance while highlighting their commitment to long-term investments despite potential near-term margin pressures."""
    
    else:
        return "I've analyzed the document(s) but couldn't find specific information related to your query. The documents primarily discuss financial results, business segments, and future outlook for the respective earnings periods. If you'd like more specific information, please refine your query."

# --- Tool Functions ---

def analyze_document_summaries(query, document_ids, max_docs=3):
    """Analyze multiple document summaries."""
    logger.info(f"Summary Analysis: Analyzing {len(document_ids)} documents for query: {query[:100]}...")
    
    # Initialize DB
    db, transcripts_coll, summaries_coll = init_db()
    if db is None:
        return {"answer": "Database connection failed", "error": "DB Connection Error"}
    
    # Limit documents
    if len(document_ids) > max_docs:
        document_ids = document_ids[:max_docs]
    
    # Get summaries
    document_summaries = []
    
    for doc_id in document_ids:
        summary_text, error = get_document_summary(summaries_coll, doc_id)
        if summary_text:
            metadata = get_document_metadata(transcripts_coll, doc_id)
            document_summaries.append({
                "document_id": doc_id,
                "content": summary_text,
                "metadata": metadata
            })
    
    if not document_summaries:
        return {"answer": "No summaries found", "error": "No summaries available"}
    
    # Construct prompt
    prompt = f"""Analyze these document summaries to answer the query.
Base your answer ONLY on the information in these summaries.

QUERY: {query}

"""
    # Add each summary
    for i, doc in enumerate(document_summaries):
        metadata = doc["metadata"]
        prompt += f"""
DOCUMENT {i+1}: {metadata.get('document_name', f'Document {doc["document_id"]}')}
{doc["content"]}

"""
    
    prompt += """
Answer:"""
    
    try:
        # Use mock LLM response
        answer = mock_llm_response(prompt)
        
        return {
            "answer": answer,
            "documents_analyzed": [doc["document_id"] for doc in document_summaries]
        }
    except Exception as e:
        logger.error(f"Error with mock LLM: {e}")
        return {"answer": f"Error: {str(e)}", "error": str(e)}

def analyze_full_document(query, document_id, chunk_index=None):
    """Analyze a full document transcript."""
    logger.info(f"Full Document Analysis: Analyzing document {document_id} for query: {query[:100]}...")
    
    # Initialize DB
    db, transcripts_coll, summaries_coll = init_db()
    if db is None:
        return {"answer": "Database connection failed", "error": "DB Connection Error"}
    
    # Get document text
    full_text, error = get_document_full_text(transcripts_coll, document_id)
    if error:
        return {"answer": f"Error: {error}", "error": error}
    
    metadata = get_document_metadata(transcripts_coll, document_id)
    
    # Chunk the text
    chunks = chunk_document_text(full_text)
    if not chunks:
        return {"answer": "Failed to chunk document", "error": "Chunking failed"}
    
    # Validate chunk index
    if chunk_index is None:
        chunk_index = 0
    
    if chunk_index < 0 or chunk_index >= len(chunks):
        return {"answer": f"Invalid chunk index {chunk_index}", "error": "Invalid chunk index"}
    
    # Get specified chunk
    chunk_content = chunks[chunk_index]
    
    # Construct prompt
    chunk_info = f"(Chunk {chunk_index+1} of {len(chunks)})" if len(chunks) > 1 else ""
    prompt = f"""Analyze this document transcript {chunk_info} to answer the query.
Base your answer ONLY on the information in this document.

QUERY: {query}

DOCUMENT: {metadata.get('document_name', f'Document {document_id}')}

CONTENT:
{chunk_content}

Answer:"""
    
    try:
        # Use mock LLM response
        answer = mock_llm_response(prompt)
        
        has_more = chunk_index < len(chunks) - 1
        
        return {
            "answer": answer,
            "document_id": document_id,
            "document_name": metadata.get("document_name", "Unknown"),
            "current_chunk": chunk_index,
            "total_chunks": len(chunks),
            "has_more_chunks": has_more,
            "next_chunk": chunk_index + 1 if has_more else None
        }
    except Exception as e:
        logger.error(f"Error with mock LLM: {e}")
        return {"answer": f"Error: {str(e)}", "error": str(e)}

# --- Testing Functions ---

def get_document_ids(limit=3):
    """Fetch document IDs for testing."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['earnings_transcripts']
        
        # Get document IDs from transcripts collection
        docs = list(db.transcripts.find({}, {"document_id": 1}).limit(limit))
        document_ids = [doc["document_id"] for doc in docs if "document_id" in doc]
        
        return document_ids
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []

def test_summary_analysis():
    """Test the document summaries analysis tool"""
    print("\n===== Testing Document Summaries Analysis =====")
    
    # Get some document IDs
    document_ids = get_document_ids(3)
    if not document_ids:
        print("No document IDs found. Skipping summary analysis test.")
        return
    
    print(f"Found {len(document_ids)} document IDs:")
    for i, doc_id in enumerate(document_ids):
        print(f"  {i+1}. {doc_id}")
    
    # Test query
    test_query = "Analyze the revenue growth"
    print(f"\nQuery: {test_query}")
    
    # Call the tool
    result = analyze_document_summaries(test_query, document_ids)
    
    # Print result
    print("\nResult:")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print("Documents analyzed:", ", ".join(result.get("documents_analyzed", [])))
        print("\nAnswer:")
        print(result.get("answer", "No answer provided"))

def test_full_document_analysis():
    """Test the full document analysis tool"""
    print("\n===== Testing Full Document Analysis =====")
    
    # Get a document ID
    document_ids = get_document_ids(1)
    if not document_ids:
        print("No document IDs found. Skipping full document analysis test.")
        return
    
    document_id = document_ids[0]
    print(f"Using document ID: {document_id}")
    
    # Test query
    test_query = "What was mentioned about future outlook and guidance?"
    print(f"\nQuery: {test_query}")
    
    # Call the tool
    result = analyze_full_document(test_query, document_id)
    
    # Print result
    print("\nResult:")
    if "error" in result and result["error"]:
        print(f"Error: {result['error']}")
    else:
        print(f"Document: {result.get('document_name', 'Unknown')}")
        print(f"Total chunks: {result.get('total_chunks', 0)}")
        print(f"Current chunk: {result.get('current_chunk', 0)}")
        print(f"Has more chunks: {result.get('has_more_chunks', False)}")
        
        print("\nAnswer:")
        print(result.get("answer", "No answer provided"))

def main():
    """Main test function."""
    print("Starting Two-Layered Document Analysis Test\n")
    
    # Test Summary Analysis
    test_summary_analysis()
    
    # Test Full Document Analysis
    test_full_document_analysis()
    
    print("\nTests completed!")

if __name__ == "__main__":
    main() 