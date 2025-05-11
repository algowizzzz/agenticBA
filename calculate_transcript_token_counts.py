#!/usr/bin/env python3
"""
Calculates token counts for all transcripts in MongoDB and identifies those
exceeding a defined threshold, flagging them for potential map-reduce summarization.
"""

import logging
import tiktoken
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# --- Configuration ---
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "earnings_transcripts"
TRANSCRIPTS_COLLECTION = "transcripts"
TOKENIZER_MODEL = "cl100k_base"  # A common tokenizer, good general proxy.
# Define a practical token limit for single-pass high-quality summarization.
# Even if a model supports 200K, summarizing such a large doc in one go can be problematic.
# This is a threshold to consider for map-reduce.
TOKEN_THRESHOLD = 75000

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_mongodb_client():
    """Establishes connection to MongoDB and returns the client object or None on failure."""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB.")
        return client
    except ConnectionFailure:
        logger.error(f"Failed to connect to MongoDB at {MONGODB_URI}. Please ensure MongoDB is running.")
        return None

def calculate_token_counts():
    """
    Iterates through transcripts, calculates token counts, and identifies
    documents exceeding the TOKEN_THRESHOLD.
    """
    client = get_mongodb_client()
    if not client:
        return

    try:
        db = client[DATABASE_NAME]
        transcripts_collection = db[TRANSCRIPTS_COLLECTION]
        
        logger.info(f"Using tokenizer: {TOKENIZER_MODEL}")
        tokenizer = tiktoken.get_encoding(TOKENIZER_MODEL)
        
        total_transcripts = 0
        over_limit_transcripts = 0
        
        logger.info(f"Processing transcripts from collection: {TRANSCRIPTS_COLLECTION}")
        logger.info(f"Identifying transcripts with more than {TOKEN_THRESHOLD:,} tokens.")
        print("\n--- Transcript Token Counts ---")

        # Fetch all documents. Only get document_id and transcript_text to save memory.
        for doc in transcripts_collection.find({}, {"document_id": 1, "transcript_text": 1, "_id": 0}):
            total_transcripts += 1
            doc_id = doc.get("document_id", "N/A")
            transcript_text = doc.get("transcript_text", "")

            if not transcript_text:
                logger.warning(f"Document ID {doc_id} has no transcript_text. Skipping.")
                print(f"Document ID: {doc_id}, Tokens: 0 (No text)")
                continue

            try:
                tokens = tokenizer.encode(transcript_text)
                token_count = len(tokens)
            except Exception as e:
                logger.error(f"Error tokenizing document ID {doc_id}: {e}")
                print(f"Document ID: {doc_id}, Tokens: ERROR ({e})")
                continue
            
            status = ""
            if token_count > TOKEN_THRESHOLD:
                status = f"*** EXCEEDS THRESHOLD ({TOKEN_THRESHOLD:,}) ***"
                over_limit_transcripts += 1
            
            print(f"Document ID: {doc_id}, Tokens: {token_count:,} {status}")

        print("\n--- Summary ---")
        logger.info(f"Total transcripts processed: {total_transcripts}")
        print(f"Total transcripts processed: {total_transcripts}")
        
        logger.info(f"Transcripts exceeding {TOKEN_THRESHOLD:,} tokens: {over_limit_transcripts}")
        print(f"Transcripts exceeding {TOKEN_THRESHOLD:,} tokens: {over_limit_transcripts}")
        
        if over_limit_transcripts > 0:
            logger.info(f"These {over_limit_transcripts} transcripts should be considered for map-reduce summarization.")
            print(f"These {over_limit_transcripts} transcripts will require the map-reduce summarization approach.")
        else:
            logger.info("No transcripts exceeded the token threshold. All can likely be summarized in a single pass.")
            print("No transcripts exceeded the token threshold.")

    except OperationFailure as e:
        logger.error(f"MongoDB operation failed: {e.details}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed.")

if __name__ == "__main__":
    calculate_token_counts() 