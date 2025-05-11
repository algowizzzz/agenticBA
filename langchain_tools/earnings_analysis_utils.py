#!/usr/bin/env python3
"""
Shared utilities for earnings call document analysis tools.
Contains common functions for MongoDB connection, document retrieval, etc.
"""

import logging
import os
from typing import Dict, Any, Optional, Tuple, List
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Connection ---
def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping')
        logger.info("Analysis Utils: MongoDB connection successful.")
        return client
    except Exception as e:
        logger.error(f"Analysis Utils: MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None, None, None  # Indicate failure
    db = client['earnings_transcripts']
    return db, db.transcripts, db.document_summaries  # Return handles to collections

# --- Document/Summary Fetching ---
def get_document_summary(summaries_coll, document_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Retrieve only the summary for a document ID.
       Returns: (summary_text, error_message)
    """
    if not document_id:
        return None, "Document ID is missing."

    summary_text = None
    error_msg = None

    try:
        logger.info(f"Analysis Utils: Fetching summary for document_id: {document_id}")
        summary_doc = summaries_coll.find_one({"transcript_uuid": document_id})
        
        if summary_doc and "summary_content" in summary_doc:
            # Extract the summary content - this is the structured JSON object
            summary_content = summary_doc["summary_content"]
            
            # Format the summary into a readable text
            summary_text = format_summary_to_text(summary_content, summary_doc)
            logger.info(f"Analysis Utils: Found summary for document_id: {document_id}")
        else:
            logger.info(f"Analysis Utils: No summary found for document_id: {document_id}")
            error_msg = f"No summary found for document ID: {document_id}"
    except Exception as e:
        logger.warning(f"Analysis Utils: Error fetching summary for {document_id}: {e}")
        error_msg = f"Error fetching summary: {e}"

    return summary_text, error_msg

def format_summary_to_text(summary_content: Dict, doc_metadata: Dict) -> str:
    """Formats the structured summary content into readable text."""
    if not summary_content:
        return "Summary not available."
    
    # Get document metadata for context
    ticker = doc_metadata.get("ticker", "Unknown")
    quarter = doc_metadata.get("quarter", "Unknown")
    year = doc_metadata.get("year", "Unknown")
    
    # Start with document identification
    text = f"SUMMARY FOR: {ticker} Q{quarter} {year} Earnings Call\n\n"
    
    # Add narrative overview
    narrative = summary_content.get("narrative_overview", "")
    if narrative:
        text += f"OVERVIEW:\n{narrative}\n\n"
    
    # Add key events
    events = summary_content.get("key_events_and_announcements", [])
    if events:
        text += "KEY EVENTS:\n"
        for event in events:
            desc = event.get("event_description", "")
            impact = event.get("impact_assessment", "")
            if desc:
                text += f"- {desc}"
                if impact:
                    text += f" - {impact}"
                text += "\n"
        text += "\n"
    
    # Add major themes
    themes = summary_content.get("major_themes_and_topics", [])
    if themes:
        text += "MAJOR THEMES:\n"
        for theme in themes:
            name = theme.get("theme_name", "")
            details = theme.get("details", "")
            if name:
                text += f"- {name}: {details}\n"
        text += "\n"
    
    # Add key metrics
    metrics = summary_content.get("key_metrics_and_financials", [])
    if metrics:
        text += "KEY METRICS:\n"
        for metric in metrics:
            name = metric.get("metric_name", "")
            value = metric.get("value", "")
            period = metric.get("period", "")
            commentary = metric.get("commentary", "")
            
            if name and value:
                text += f"- {name}: {value}"
                if period:
                    text += f" ({period})"
                if commentary:
                    text += f" - {commentary}"
                text += "\n"
        text += "\n"
    
    # Add overall sentiment
    sentiment = summary_content.get("overall_sentiment", {})
    if sentiment:
        rating = sentiment.get("rating", "")
        justification = sentiment.get("justification", "")
        if rating:
            text += f"OVERALL SENTIMENT: {rating}"
            if justification:
                text += f" - {justification}"
            text += "\n\n"
    
    return text

def get_document_full_text(transcripts_coll, document_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Retrieve full transcript text for a document ID.
       Returns: (transcript_text, error_message)
    """
    if not document_id:
        return None, "Document ID is missing."

    transcript_text = None
    error_msg = None

    try:
        logger.info(f"Analysis Utils: Fetching transcript for document_id: {document_id}")
        transcript_doc = transcripts_coll.find_one({"document_id": document_id})
        
        if transcript_doc and "transcript_text" in transcript_doc:
            transcript_text = transcript_doc["transcript_text"]
            logger.info(f"Analysis Utils: Found transcript for document_id: {document_id}")
        else:
            logger.info(f"Analysis Utils: No transcript found for document_id: {document_id}")
            error_msg = f"No transcript found for document ID: {document_id}"
    except Exception as e:
        logger.error(f"Analysis Utils: Error fetching transcript for {document_id}: {e}")
        error_msg = f"Error fetching transcript: {e}"

    return transcript_text, error_msg

def get_document_metadata(transcripts_coll, document_id: str) -> Dict[str, Any]:
    """Fetch document metadata from the transcripts collection."""
    try:
        transcript_doc = transcripts_coll.find_one({"document_id": document_id})
        if not transcript_doc:
            return {"error": f"Document not found: {document_id}"}
        
        # Extract meaningful metadata fields
        metadata = {
            "document_id": document_id,
            "ticker": transcript_doc.get("category", "Unknown"),
            "quarter": transcript_doc.get("quarter", "Unknown"),
            "year": transcript_doc.get("fiscal_year", "Unknown"),
            "date": transcript_doc.get("date", "Unknown")
        }
        
        # Create a readable document name
        metadata["document_name"] = f"{metadata['ticker']} Q{metadata['quarter']} {metadata['year']} Earnings Call"
        
        return metadata
    except Exception as e:
        logger.error(f"Analysis Utils: Error fetching metadata for {document_id}: {e}")
        return {"error": f"Error fetching metadata: {e}"}

def chunk_document_text(text: str, chunk_size: int = 80000) -> List[str]:
    """Splits document text into manageable chunks for LLM processing."""
    if not text:
        return []
    
    # Simple chunking based on character count
    # For more sophisticated chunking, consider sentence or paragraph boundaries
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    
    return chunks 