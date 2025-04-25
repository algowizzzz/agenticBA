#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime
from pymongo import MongoClient
from anthropic import Anthropic

# Load configuration
with open('improved_summary_prompts_config.json', 'r') as f:
    config = json.load(f)

# Get department summary config
dept_config = config['department_summary']

# Load API key from environment variable
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY environment variable not set.")
    sys.exit(1)

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def get_mongodb_client():
    """Get MongoDB client with error handling"""
    try:
        return MongoClient('mongodb://localhost:27017/')
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

def get_category_summaries(target_categories=None):
    """Retrieve category summaries from the database"""
    client = get_mongodb_client()
    db = client.earnings_transcripts
    
    query = {}
    if target_categories:
        query['category_id'] = {'$in': target_categories}
    
    summaries = list(db.category_summaries.find(query))
    return summaries

def format_category_summaries(summaries):
    """Format category summaries for the prompt"""
    formatted_summaries = []
    for summary in summaries:
        # Clean up the summary object for JSON serialization
        clean_summary = {k: v for k, v in summary.items() if k != '_id'}
        formatted_summaries.append(clean_summary)
    
    return json.dumps(formatted_summaries, indent=2, cls=DateTimeEncoder)

def format_prompt(formatted_summaries, category_list):
    """Format the prompt template with the summaries"""
    template = dept_config['user_prompt_template']
    
    return template.format(
        department_id="TECH",
        num_categories=len(category_list),
        category_list=", ".join(category_list),
        category_summaries=formatted_summaries
    )

def generate_department_summary(prompt):
    """Generate department summary using Anthropic API"""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    print("Generating department summary...")
    
    try:
    response = client.messages.create(
            model=dept_config['model'],
        max_tokens=dept_config['max_tokens'],
        temperature=dept_config['temperature'],
            system=dept_config['system_prompt'],
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        sys.exit(1)

def save_department_summary(summary_text, department_id="TECH", category_ids=None):
    """Save the department summary to the database"""
    client = get_mongodb_client()
    db = client.earnings_transcripts
    
    department_summary = {
        "department_id": department_id,
        "summary_text": summary_text,
        "last_updated": datetime.now(),
        "model": dept_config['model'],
        "category_ids": category_ids or []
    }
    
    result = db.department_summaries.update_one(
        {"department_id": department_id},
        {"$set": department_summary},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"Created new department summary for {department_id}")
    else:
        print(f"Updated existing department summary for {department_id}")
    
    return department_summary

def main():
    parser = argparse.ArgumentParser(description="Generate a department summary from category summaries")
    parser.add_argument("--dry-run", action="store_true", help="Show the formatted prompt without making API call")
    args = parser.parse_args()
    
    # Target categories
    target_categories = ['AAPL', 'AMZN', 'NVDA', 'MU']
    
    # Get summaries for target categories
    summaries = get_category_summaries(target_categories)
    if not summaries:
        print(f"No summaries found for categories: {target_categories}")
        return
    
    found_categories = [s['category_id'] for s in summaries]
    print(f"Found summaries for categories: {found_categories}")
    
    # Format summaries for the prompt
    formatted_summaries = format_category_summaries(summaries)
    
    # Format the prompt
    prompt = format_prompt(formatted_summaries, found_categories)
    
    # For dry run, just show the prompt
    if args.dry_run:
        print("\nSystem Prompt:")
        print(dept_config['system_prompt'])
        print("\nUser Prompt Preview (first 500 chars):")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        return
    
    # Generate department summary
        summary_text = generate_department_summary(prompt)
        
        # Save to database
    save_department_summary(summary_text, category_ids=found_categories)
        
        print("\nDepartment Summary Preview:")
        print(summary_text[:500] + "..." if len(summary_text) > 500 else summary_text)

if __name__ == "__main__":
    main() 