import os
import json
import time
import datetime
import re
from pymongo import MongoClient
from dotenv import load_dotenv
import anthropic

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration - Using hardcoded values to match other scripts
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "earnings_transcripts"  # Changed to match other scripts
COLLECTION_TRANSCRIPTS = "transcripts"  # Changed to match other scripts
COLLECTION_SUMMARIES = "document_summaries"

# Get Anthropic API key from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# LLM Configuration
LLM_MODEL_NAME = "claude-3-haiku-20240307"  # Updated to use haiku for maximum cost efficiency
MAX_OUTPUT_TOKENS = 4096

# --- PROMPT DEFINITION ---
# Updated prompt to more strongly enforce JSON-only output
LLM_PROMPT_TEMPLATE = """
You are an expert financial analyst. Your task is to extract key information from the provided financial document, which is an earnings call transcript.

Please read the following document text carefully:
<document_text>
{transcript_text}
</document_text>

Based on the document, extract the information for the fields described below and structure it as a single JSON object.
The JSON object MUST adhere to the schema for these fields.

**IMPORTANT INSTRUCTIONS:**
1. Your output MUST be a valid JSON object only. Do not include any explanatory text before or after the JSON.
2. Do not include code block markers like ```json or ``` around your JSON.
3. Ensure the JSON is properly formatted with escaped characters where necessary.
4. Start your response with the opening curly brace {{ and end with the closing curly brace }}.

**JSON Schema (for your output):**
{{
  "narrative_overview": "string (A detailed narrative summary of 300-500 words covering the most critical aspects, key takeaways, and overall sentiment of the document. This should be a well-written, coherent paragraph.)",
  "key_events_and_announcements": [
    {{
      "event_description": "string (Brief description of a significant event or announcement)",
      "impact_assessment": "string (Brief assessment of its potential impact or importance)"
    }}
  ],
  "major_themes_and_topics": [
    {{
      "theme_name": "string (e.g., 'Revenue Growth', 'Product Innovation', 'Regulatory Challenges', 'Market Expansion', 'Cost Optimization')",
      "details": "string (Specific details or quotes from the document related to this theme)"
    }}
  ],
  "entities_mentioned": {{
    "companies": ["string (List of other company names mentioned, excluding the primary company if applicable)"],
    "products_services": ["string (List of key products or services discussed)"],
    "people": ["string (List of key individuals mentioned, e.g., executives, analysts)"],
    "geographies": ["string (List of key regions or countries discussed)"]
  }},
  "strategic_factors": {{
    "strengths": ["string (Key strengths highlighted or inferred)"],
    "weaknesses": ["string (Key weaknesses or challenges identified)"],
    "opportunities": ["string (Potential opportunities discussed or implied)"],
    "threats": ["string (Potential threats or risks mentioned)"]
  }},
  "key_metrics_and_financials": [
    {{
      "metric_name": "string (e.g., 'Revenue', 'Net Income', 'EPS', 'User Growth', 'Projected Guidance')",
      "value": "string (The reported value or range)",
      "period": "string (The period to which the metric applies, e.g., 'Q1 2023', 'YoY Growth')",
      "commentary": "string (Any additional context or explanation provided in the document)"
    }}
  ],
  "forward_looking_statements_and_guidance": [
    {{
      "statement_type": "string (e.g., 'Revenue Guidance', 'EPS Outlook', 'Strategic Goals for Next Year')",
      "details": "string (Specific guidance, targets, or future plans mentioned)",
      "timeframe": "string (Associated timeframe, e.g., 'Q2 2023', 'Full Year 2024')"
    }}
  ],
  "analyst_qa_highlights": [
    {{
      "question": "string (The core question asked by an analyst)",
      "answer_summary": "string (A concise summary of the company's response)",
      "analyst_name_firm": "string (Name and firm of the analyst, if available)"
    }}
  ],
  "critical_insights_and_takeaways": [
    "string (Bulleted list of the most important insights or conclusions that can be drawn from the document)"
  ],
  "open_questions_and_areas_for_further_analysis": [
    "string (Bulleted list of questions or areas that remain unclear or warrant deeper investigation)"
  ],
  "overall_sentiment": {{
    "rating": "string (e.g., 'Positive', 'Neutral', 'Negative', 'Mixed')",
    "justification": "string (Brief explanation for the sentiment rating based on document content)"
  }}
}}

**Field requirements:**
- Be comprehensive but concise.
- Extract information directly from the document. Do not infer or add external information.
- If a section is not applicable or the content is not available, use an empty list `[]` for arrays or an appropriate empty string `""` for string fields. Never omit keys.
- The `narrative_overview` MUST be between 300 and 500 words.
"""

def format_date_for_json(date_obj):
    """Formats a datetime object or a date string into YYYY-MM-DD string."""
    if isinstance(date_obj, datetime.datetime):
        return date_obj.strftime('%Y-%m-%d')
    if isinstance(date_obj, str):
        try:
            # Attempt to parse if it's a full ISO string (e.g., from MongoDB)
            dt_obj = datetime.datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
            return dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            # If it's already YYYY-MM-DD or another format, return as is or handle more parsing
            # For simplicity, assume it might already be in the correct format if parsing fails
            return date_obj
    return str(date_obj) if date_obj else None

def extract_json_from_text(text):
    """
    Improved function to extract JSON from text, handling cases where the model
    adds explanatory text before or after the JSON.
    """
    # First attempt: try to parse the text directly as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Second attempt: try to find JSON between code block markers
    json_pattern = r"```(?:json)?(.*?)```"
    matches = re.findall(json_pattern, text, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError:
            pass
    
    # Third attempt: try to find text between curly braces, ensuring we get the outermost braces
    try:
        # Find the first opening brace
        start_idx = text.find('{')
        if start_idx != -1:
            brace_count = 1
            for i in range(start_idx + 1, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    
                if brace_count == 0:
                    # Found the matching closing brace
                    json_str = text[start_idx:i+1]
                    return json.loads(json_str)
    except (json.JSONDecodeError, ValueError, IndexError):
        pass
    
    # If all attempts fail, raise an exception
    raise ValueError("Could not extract valid JSON from the text")

def generate_summary(client, transcript_text):
    """Calls the LLM to generate the summary content."""
    prompt = LLM_PROMPT_TEMPLATE.format(transcript_text=transcript_text)
    try:
        response = client.messages.create(
            model=LLM_MODEL_NAME,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        if response.content and isinstance(response.content, list) and len(response.content) > 0:
            return response.content[0].text
        else:
            print("Error: Received unexpected response structure from LLM.")
            print(f"Response: {response}")
            return None
    except anthropic.APIConnectionError as e:
        print(f"Anthropic API connection error: {e}")
    except anthropic.RateLimitError as e:
        print(f"Anthropic API rate limit exceeded: {e}. Waiting and retrying...")
        time.sleep(60) # Wait for 60 seconds before potential next attempt (if part of a larger retry loop)
        # For a single call, this specific retry is illustrative; a more robust retry mechanism would be external.
    except anthropic.APIStatusError as e:
        print(f"Anthropic API status error: {e.status_code} - {e.response}")
    except Exception as e:
        print(f"An unexpected error occurred while calling Anthropic API: {e}")
    return None

def process_transcript(transcript, anthropic_client, transcripts_collection, summaries_collection):
    """Process a single transcript and generate its summary."""
    document_id = transcript.get("document_id")
    transcript_text = transcript.get("transcript_text")

    if not document_id:
        print(f"Skipping transcript due to missing document_id.")
        return False
    if not transcript_text or not transcript_text.strip():
        print(f"Skipping transcript {document_id} due to empty transcript text.")
        return False

    # 1. Construct document_metadata
    doc_metadata = {
        "document_type": "Earnings Call Transcript",
        "source_document_id": document_id,
        "company_name": transcript.get("category") or "N/A",
        "ticker_symbol": transcript.get("category") or "N/A",
        "fiscal_period": f"Q{transcript.get('quarter', 'N/A')} {transcript.get('fiscal_year', 'N/A')}",
        "publication_date": format_date_for_json(transcript.get("date"))
    }

    # 2. Get summary content from LLM
    print(f"  Generating summary for {doc_metadata['ticker_symbol']} {doc_metadata['fiscal_period']}...")
    llm_summary_str = generate_summary(anthropic_client, transcript_text)

    if not llm_summary_str:
        print(f"  Failed to generate summary for {document_id}. Skipping.")
        return False

    # 3. Parse LLM JSON response
    try:
        llm_generated_content = extract_json_from_text(llm_summary_str)
        
        # Verify that the JSON structure contains the expected top-level keys
        expected_keys = ["narrative_overview", "key_events_and_announcements", "major_themes_and_topics", 
                        "entities_mentioned", "strategic_factors", "key_metrics_and_financials", 
                        "forward_looking_statements_and_guidance", "analyst_qa_highlights", 
                        "critical_insights_and_takeaways", "open_questions_and_areas_for_further_analysis", 
                        "overall_sentiment"]
        
        for key in expected_keys:
            if key not in llm_generated_content:
                print(f"  Warning: Missing expected key '{key}' in generated JSON")
                
    except Exception as e:
        print(f"  Error parsing JSON response from LLM for {document_id}: {e}")
        print(f"  Raw LLM response snippet: {llm_summary_str[:500]}...") # Log snippet for debugging
        return False

    # 4. Combine metadata and LLM content
    final_summary_doc = {
        "transcript_uuid": document_id,  # Keep 'transcript_uuid' as the field name for consistency with existing docs
        "ticker": doc_metadata["ticker_symbol"],
        "quarter": transcript.get("quarter"),
        "year": transcript.get("fiscal_year"),  # Update to use fiscal_year instead of year
        "document_metadata": doc_metadata,
        "summary_content": llm_generated_content, # The structured data from LLM
        "last_updated_utc": datetime.datetime.now(datetime.timezone.utc)  # Use timezone-aware datetime
    }

    # 5. Store in MongoDB
    try:
        summaries_collection.update_one(
            {"transcript_uuid": document_id},
            {"$set": final_summary_doc},
            upsert=True
        )
        print(f"  Successfully saved summary for {document_id} ({doc_metadata['ticker_symbol']} {doc_metadata['fiscal_period']}).")
        return True
    except Exception as e:
        print(f"  Error saving summary for {document_id} to MongoDB: {e}")
        return False

def main():
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        return

    print(f"Connecting to MongoDB: {MONGO_URI}, Database: {MONGO_DB_NAME}")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    transcripts_collection = db[COLLECTION_TRANSCRIPTS]
    summaries_collection = db[COLLECTION_SUMMARIES]

    print(f"Initializing Anthropic client with model: {LLM_MODEL_NAME}")
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # By default, process all transcripts
    process_all = True
    limit = None
    
    # Check for command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            process_all = False
            limit = int(sys.argv[1])
            print(f"Will process at most {limit} transcripts for testing")
        elif sys.argv[1] == "test":
            process_all = False
            limit = 3  # Default test limit
            print(f"Running in test mode, will process {limit} transcripts")
    
    # Get transcripts to process
    query = {}
    if not process_all and limit:
        transcripts_to_process = list(transcripts_collection.find(query).limit(limit))
    else:
        transcripts_to_process = list(transcripts_collection.find(query))
        
    total_transcripts = len(transcripts_to_process)
    print(f"Found {total_transcripts} transcripts to process.")

    success_count = 0
    for i, transcript in enumerate(transcripts_to_process):
        print(f"\nProcessing transcript {i+1}/{total_transcripts}: ID {transcript.get('document_id', 'N/A')}")
        
        if process_transcript(transcript, anthropic_client, transcripts_collection, summaries_collection):
            success_count += 1

    print(f"\nFinished processing {total_transcripts} transcripts.")
    print(f"Successfully generated summaries for {success_count}/{total_transcripts} transcripts.")
    mongo_client.close()

if __name__ == "__main__":
    main() 