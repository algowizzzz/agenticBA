#!/usr/bin/env python3
import os
import sys
import argparse
import pymongo
import datetime
import json
from anthropic import Anthropic

# MongoDB connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]
transcripts_collection = db["transcripts"]
category_summaries_collection = db["category_summaries"]

# Load improved prompt configuration
config = {}
try:
    with open("improved_summary_prompts_config.json", "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"Warning: Could not load improved_summary_prompts_config.json: {str(e)}")
    print("Will use default prompt template.")

def get_transcripts_for_category(category, limit=100):
    """Retrieve the most recent transcripts for a given category"""
    query = {"category_id": category.upper()}
    
    # Sort by date descending to get the most recent transcripts
    cursor = transcripts_collection.find(query).sort("date", -1).limit(limit)
    results = list(cursor)
    return results

def format_category_stats(category, transcripts):
    """Format basic information about the category and its transcripts"""
    if not transcripts:
        return f"No transcripts found for category {category}"
    
    dates = [transcript.get('date') for transcript in transcripts]
    quarters = [f"Q{transcript.get('quarter')} {transcript.get('fiscal_year')}" 
               for transcript in transcripts if 'quarter' in transcript and transcript['quarter']]
    
    info = f"Category: {category}\n"
    info += f"Number of transcripts: {len(transcripts)}\n"
    info += f"Date range: {min(dates)} to {max(dates)}\n"
    info += f"Recent quarters: {', '.join(quarters[:3])}\n"
    
    # Calculate token statistics if available
    token_counts = [transcript.get('token_count') for transcript in transcripts if 'token_count' in transcript]
    if token_counts:
        info += f"Average token count: {sum(token_counts) / len(token_counts):.1f}\n"
        info += f"Min/Max token count: {min(token_counts)} / {max(token_counts)}\n"
    
    return info

def summarize_category_with_claude(category, transcripts, max_words=1500):
    """Summarize a category using Claude"""
    # Check if API key is set
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY environment variable not set", None, []
    
    # Initialize Claude client
    client = Anthropic(api_key=api_key)
    
    # Get configuration for category summary
    category_config = config.get("category_summary", {})
    model = category_config.get("model", "claude-3-5-sonnet-20240620")
    system_prompt = category_config.get("system_prompt", "You are a financial analyst providing comprehensive cross-quarter analysis of company performance and strategy. Focus on identifying patterns, strategic shifts, and business trajectory based on earnings call data.")
    max_tokens = category_config.get("max_tokens", 3000)
    temperature = category_config.get("temperature", 0.0)
    default_max_words = category_config.get("default_max_words", 1500)
    
    # Use config max_words if not specified
    if max_words == 1500 and default_max_words != 1500:
        max_words = default_max_words
    
    # Sort transcripts by date (most recent first)
    sorted_transcripts = sorted(transcripts, key=lambda x: x.get('date', ''), reverse=True)
    
    # Format transcript details
    transcript_details = ""
    document_ids = []
    for transcript in sorted_transcripts:
        document_id = transcript.get('document_id', '')
        document_ids.append(document_id)
        date = transcript.get('date', '')
        quarter = transcript.get('quarter', '')
        fiscal_year = transcript.get('fiscal_year', '')
        
        transcript_details += f"Document ID: {document_id}\n"
        transcript_details += f"Date: {date}\n"
        if quarter and fiscal_year:
            transcript_details += f"Quarter: Q{quarter} {fiscal_year}\n"
        transcript_details += f"Excerpt:\n{transcript.get('transcript_text', '')[:2500]}...\n\n"
    
    # Determine time period
    earliest_date = min([t.get('date', '') for t in transcripts]) if transcripts else ''
    latest_date = max([t.get('date', '') for t in transcripts]) if transcripts else ''
    time_period = f"{earliest_date} to {latest_date}"
    
    # Use improved prompt template if available, otherwise use default
    user_prompt_template = category_config.get("user_prompt_template")
    
    if user_prompt_template:
        # Fill in the template variables
        prompt = user_prompt_template.format(
            category_id=category,
            num_transcripts=len(transcripts),
            time_period=time_period,
            transcript_details=transcript_details
        )
    else:
        # Use default prompt
        prompt = f"""
        Please provide a {max_words}-word comprehensive analysis of {category}'s business performance, trends, and strategy 
        based on information from their recent earnings calls.
        
        I'll provide snippets from the {len(sorted_transcripts)} most recent earnings calls. Focus on:

        1. Overall business trajectory and key performance trends across quarters
        2. Strategic initiatives and investments
        3. Product/service innovations and their market reception
        4. Competitive positioning
        5. Major challenges and management's approach
        6. Financial performance patterns and outlook

        RECENT EARNINGS CALLS:
        """
        
        for idx, transcript in enumerate(sorted_transcripts[:3]):
            quarter = transcript.get('quarter', '')
            year = transcript.get('fiscal_year', '')
            date = transcript.get('date', '')
            if quarter and year:
                prompt += f"\n--- Q{quarter} {year} ({date}) ---\n"
            else:
                prompt += f"\n--- {date} ---\n"
            prompt += transcript.get('transcript_text', '')[:5000] + "...\n"
        
        prompt += f"\nPlease synthesize this information into a cohesive {max_words}-word analysis of {category}'s business."
    
    try:
        # Call Claude API
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Get token usage from response metadata (if available)
        token_info = None
        if hasattr(message, 'usage'):
            token_info = {
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens
            }
        
        # Return the response, token info, and document IDs
        return message.content[0].text, token_info, document_ids
    
    except Exception as e:
        return f"Error calling Claude API: {str(e)}", None, document_ids

def count_words(text):
    """Count the number of words in a text"""
    return len(text.split())

def save_category_summary_to_db(category, summary_text, token_info=None, transcript_count=0, document_ids=None):
    """Save the summary to the category_summaries collection"""
    # Check if a summary already exists for this category
    existing_summary = category_summaries_collection.find_one({"category_id": category})
    
    # Prepare the summary document
    summary_doc = {
        "category_id": category,
        "summary_text": summary_text,
        "wordcount": count_words(summary_text),
        "transcript_count": transcript_count,
        "last_updated": datetime.datetime.now(),
        "document_ids": document_ids or []
    }
    
    # Add token information if available
    if token_info:
        summary_doc["input_tokens"] = token_info.get('input_tokens')
        summary_doc["output_tokens"] = token_info.get('output_tokens')
    
    if existing_summary:
        # Update existing summary
        category_summaries_collection.update_one(
            {"category_id": category},
            {"$set": summary_doc}
        )
        return f"Updated existing summary for category {category}"
    else:
        # Insert new summary
        category_summaries_collection.insert_one(summary_doc)
        return f"Created new summary for category {category}"

def main():
    parser = argparse.ArgumentParser(description="Generate and save a category summary based on recent earnings calls")
    parser.add_argument("--category", required=True, help="Company category/ticker (e.g., NVDA)")
    parser.add_argument("--max-words", type=int, default=1500, help="Maximum words for summary (default: 1500)")
    parser.add_argument("--transcript-limit", type=int, default=100, help="Number of most recent transcripts to consider (default: 100)")
    parser.add_argument("--dry-run", action="store_true", help="Generate summary but don't save to database")
    
    args = parser.parse_args()
    
    # Get transcripts for the category
    category = args.category.upper()
    transcripts = get_transcripts_for_category(category, args.transcript_limit)
    
    if not transcripts:
        print(f"No transcripts found for category {category}")
        sys.exit(1)
    
    # Display category stats
    print(format_category_stats(category, transcripts))
    
    # Generate summary
    print(f"\nGenerating category summary (max {args.max_words} words)...")
    summary, token_info, document_ids = summarize_category_with_claude(category, transcripts, args.max_words)
    
    # Display token usage if available
    if token_info:
        print(f"\nToken Usage:")
        print(f"Input Tokens: {token_info.get('input_tokens')}")
        print(f"Output Tokens: {token_info.get('output_tokens')}")
    
    # Display summary
    print("\nCategory Summary:")
    print(summary)
    
    # Save to database if not a dry run and there's no API error
    if not args.dry_run and not summary.startswith("Error"):
        print("\nSaving summary to database...")
        result = save_category_summary_to_db(category, summary, token_info, len(transcripts), document_ids)
        print(result)
    elif not args.dry_run and summary.startswith("Error"):
        print("\nNot saving to database due to API error.")
    else:
        print("\nDry run - summary not saved to database")

if __name__ == "__main__":
    main() 