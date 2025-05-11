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
# This prompt asks the LLM to generate content from "narrative_overview" onwards.
# The "document_metadata" will be constructed by the script.
LLM_PROMPT_TEMPLATE = """
You are an expert financial analyst. Your task is to extract key information from the provided financial document, which is an earnings call transcript.

Please read the following document text carefully:
<document_text>
{transcript_text}
</document_text>

Based on the document, extract the information for the fields described below and structure it as a single JSON object.
The JSON object MUST adhere to the schema for these fields.

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

**CRITICAL INSTRUCTIONS:**
- Be comprehensive but concise.
- Extract information directly from the document. Do not infer or add external information.
- If a section of the JSON is not applicable to the document type or the content is not available, use an empty list `[]` for arrays of objects/strings, or an appropriate empty/null string for string fields where it makes sense (e.g., `""`). Do not omit keys.
- The `narrative_overview` MUST be between 300 and 500 words.
- Ensure your output is a single, valid JSON object containing ONLY the fields specified above (from "narrative_overview" to "overall_sentiment"). Do not include any text or explanations outside of this JSON structure.
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

    transcripts_to_process = list(transcripts_collection.find({}))
    total_transcripts = len(transcripts_to_process)
    print(f"Found {total_transcripts} transcripts to process.")

    for i, transcript in enumerate(transcripts_to_process):
        print(f"\nProcessing transcript {i+1}/{total_transcripts}: ID {transcript.get('document_id', 'N/A')}")

        document_id = transcript.get("document_id")
        transcript_text = transcript.get("transcript_text")

        if not document_id:
            print(f"Skipping transcript {i+1} due to missing document_id.")
            continue
        if not transcript_text or not transcript_text.strip():
            print(f"Skipping transcript {document_id} due to empty transcript text.")
            continue

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
            continue

        # 3. Parse LLM JSON response
        try:
            # The LLM is expected to return a JSON string.
            # Sometimes, the string might be wrapped in ```json ... ```, so we strip that.
            if llm_summary_str.strip().startswith("```json"):
                llm_summary_str = llm_summary_str.strip()[7:-3].strip()
            elif llm_summary_str.strip().startswith("```"):
                 llm_summary_str = llm_summary_str.strip()[3:-3].strip()

            llm_generated_content = json.loads(llm_summary_str)
        except json.JSONDecodeError as e:
            print(f"  Error parsing JSON response from LLM for {document_id}: {e}")
            print(f"  Raw LLM response snippet: {llm_summary_str[:500]}...") # Log snippet for debugging
            continue
        except Exception as e:
            print(f"  An unexpected error occurred during JSON processing for {document_id}: {e}")
            continue

        # 4. Combine metadata and LLM content
        final_summary_doc = {
            "transcript_uuid": document_id,  # Keep 'transcript_uuid' as the field name for consistency with existing docs
            "ticker": doc_metadata["ticker_symbol"],
            "quarter": transcript.get("quarter"),
            "year": transcript.get("fiscal_year"),  # Update to use fiscal_year instead of year
            "document_metadata": doc_metadata,
            "summary_content": llm_generated_content, # The structured data from LLM
            "last_updated_utc": datetime.datetime.utcnow()
        }

        # 5. Store in MongoDB
        try:
            summaries_collection.update_one(
                {"transcript_uuid": document_id},
                {"$set": final_summary_doc},
                upsert=True
            )
            print(f"  Successfully saved summary for {document_id} ({doc_metadata['ticker_symbol']} {doc_metadata['fiscal_period']}).")
        except Exception as e:
            print(f"  Error saving summary for {document_id} to MongoDB: {e}")

    print(f"\nFinished processing all {total_transcripts} transcripts.")
    mongo_client.close()

if __name__ == "__main__":
    main() 