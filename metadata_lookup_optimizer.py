#!/usr/bin/env python3
"""
Metadata Lookup Tool Optimizer

This script improves the existing metadata lookup tool by:
1. Creating a structured JSON index of metadata
2. Replacing the inefficient two-prompt approach with a single structured lookup
3. Measuring token usage savings

Usage:
  python metadata_lookup_optimizer.py [--test]
"""

import argparse
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage

# --- Database Connection ---
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

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None
    return client['earnings_transcripts']

# --- Metadata Fetching ---
def fetch_all_metadata(db) -> Optional[Dict[str, Any]]:
    """Fetch minimal transcript details, category mappings, and summary availability for ALL documents."""
    if db is None:
        print("Database connection is None.")
        return None
    try:
        print("Fetching minimal metadata for ALL documents...")
        
        # 1. Fetch minimal transcript document details
        documents = {}
        category_to_doc_ids = {}
        all_doc_ids = set()
        
        # Fetch ALL documents, only essential fields
        for doc in db.transcripts.find({}, {"document_id": 1, "category_id": 1, "date": 1, "quarter": 1, "fiscal_year": 1, "_id": 0}):
            doc_id_str = doc.get("document_id")
            category_id = doc.get("category_id")
            if not doc_id_str or not category_id:
                continue

            all_doc_ids.add(doc_id_str)
            if category_id not in category_to_doc_ids:
                category_to_doc_ids[category_id] = []
            category_to_doc_ids[category_id].append(doc_id_str)

            # Format date if it exists
            details = {"category_id": category_id}
            if doc.get("date"):
                doc_date = doc["date"]
                if isinstance(doc_date, datetime):
                    details["date"] = doc_date.strftime("%Y-%m-%d")
                elif isinstance(doc_date, str):
                    try:
                        details["date"] = datetime.strptime(doc_date[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
                    except ValueError:
                        details["date"] = doc_date
            else:
                details["date"] = None
                
            if doc.get("quarter") and doc.get("fiscal_year"):
                details["quarter"] = f"Q{doc['quarter']} {doc['fiscal_year']}"
            else:
                details["quarter"] = None
                
            documents[doc_id_str] = details

        print(f"Fetched minimal details for {len(documents)} documents across {len(category_to_doc_ids)} categories.")

        # 2. Fetch Document IDs with available individual summaries
        doc_ids_with_summaries = set()
        try:
            summary_cursor = db.document_summaries.find({}, {"document_id": 1, "_id": 0})
            doc_ids_with_summaries = {s['document_id'] for s in summary_cursor if s.get('document_id')}
            print(f"Found {len(doc_ids_with_summaries)} documents with individual summaries.")
        except Exception as e:
            print(f"Could not fetch document summary availability: {e}")

        # 3. Fetch Category IDs with available synthesized summaries
        categories_with_summaries = set()
        try:
            cat_summary_cursor = db.category_summaries.find({}, {"category_id": 1, "_id": 0})
            categories_with_summaries = {s['category_id'] for s in cat_summary_cursor if s.get('category_id')}
            print(f"Found {len(categories_with_summaries)} categories with synthesized summaries.")
        except Exception as e:
            print(f"Could not fetch category summary availability: {e}")

        return {
            "categories": category_to_doc_ids,
            "documents": documents,
            "doc_ids_with_summaries": doc_ids_with_summaries,
            "categories_with_summaries": categories_with_summaries
        }
        
    except Exception as e:
        print(f"Failed to fetch metadata: {e}")
        return None

# --- Structured Index Creation ---
def create_structured_metadata_index(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a structured JSON index mapping {company → time period → document types/IDs}
    that organizes documents by category, time period, and document IDs efficiently.
    """
    structured_index = {}
    
    # Get ticker to company name mapping if available
    ticker_to_company = {}
    # Future improvement: could load this from a file or database
    
    # Iterate over all documents
    for doc_id, details in metadata.get("documents", {}).items():
        category_id = details.get("category_id")
        date = details.get("date")
        quarter = details.get("quarter")
        
        # Skip if any essential detail is missing
        if not category_id:
            continue
        
        # Initialize company entry if not present
        if category_id not in structured_index:
            company_name = ticker_to_company.get(category_id, category_id)
            structured_index[category_id] = {
                "name": company_name,
                "time_periods": {},
                "has_category_summary": category_id in metadata.get("categories_with_summaries", set())
            }
        
        # Use quarter as time period if available, otherwise use date
        time_period = quarter if quarter else (date if date else "Unknown")
        
        # Initialize time period entry if not present
        if time_period not in structured_index[category_id]["time_periods"]:
            structured_index[category_id]["time_periods"][time_period] = {
                "documents": []
            }
        
        # Add document details
        doc_info = {
            "document_id": doc_id,
            "date": date,
            "has_summary": doc_id in metadata.get("doc_ids_with_summaries", set())
        }
        
        structured_index[category_id]["time_periods"][time_period]["documents"].append(doc_info)
        
    # Sort documents by date within each time period
    for category in structured_index.values():
        for time_period in category["time_periods"].values():
            time_period["documents"].sort(
                key=lambda x: x.get("date") or "", 
                reverse=True  # Most recent first
            )
    
    return structured_index

# --- LLM Prompt Generation ---
def format_metadata_prompt_original(query: str, metadata: Dict[str, Any]) -> str:
    """Format the original two-prompt approach for token usage comparison."""
    # Convert metadata to strings for the prompt, using compact JSON format
    categories_str = json.dumps(metadata.get("categories", {}), separators=(',', ':'))
    minimal_documents = {
        doc_id: {
            k: v for k, v in details.items() if k in ["category_id", "date", "quarter"]
        }
        for doc_id, details in metadata.get("documents", {}).items()
    }
    documents_str = json.dumps(minimal_documents, separators=(',', ':'))
    doc_ids_with_summaries_str = json.dumps(list(metadata.get("doc_ids_with_summaries", set())), separators=(',', ':'))
    categories_with_summaries_str = json.dumps(list(metadata.get("categories_with_summaries", set())), separators=(',', ':'))

    # Original prompt template (partial)
    prompt_template = """You are a metadata analysis assistant. Your task is to identify relevant information resources based on a user query and provided metadata context.

METADATA CONTEXT:

1. Document Details (Document ID -> {{category_id, date, quarter}}):
{documents_metadata}

2. Category Mappings (Category ID -> List of associated Document IDs):
{categories_metadata}

3. Availability of Pre-computed Summaries:
   - Document IDs with Individual Summaries: {doc_ids_with_summaries}
   - Category IDs with Synthesized Summaries: {categories_with_summaries}

USER QUERY: {query}

Based ONLY on the User Query and the METADATA CONTEXT provided, perform the following steps:
1. Identify the primary Category ID (e.g., company ticker like 'MSFT', 'AAPL') mentioned or implied in the User Query. If none, use null.
2. Scan the 'Document Details' context. Use the 'category_id', 'date' (YYYY-MM-DD), and 'quarter' (e.g., 'Q3 2020') fields to find documents matching the identified Category ID and any time period mentioned in the User Query.
3. If the query asks for 'most recent', use the 'date' field to select the document(s) with the latest date(s) for the relevant category.
4. Select up to 5 of the most relevant Document IDs based on the category and time period matching. Prioritize exact matches for quarter/year if specified.
5. Check if a synthesized Category Summary is available for the identified Category ID (from step 1) by seeing if it's in the 'Category IDs with Synthesized Summaries' list.
6. Create a list of the selected relevant Document IDs (from step 4) for which individual summaries are available by checking against the 'Document IDs with Individual Summaries' list.

Format your response strictly as a JSON object containing the following keys:
- "relevant_category_id": [string|null]
- "relevant_doc_ids": [list of strings]
- "category_summary_available": [boolean]
- "doc_ids_with_summaries": [list of strings]
"""

    return prompt_template.format(
        documents_metadata=documents_str,
        categories_metadata=categories_str,
        doc_ids_with_summaries=doc_ids_with_summaries_str,
        categories_with_summaries=categories_with_summaries_str,
        query=query
    )

def format_metadata_prompt_structured(query: str, structured_index: Dict[str, Any]) -> str:
    """Format the improved single-prompt approach using the structured index."""
    # Convert structured index to compact JSON
    structured_index_str = json.dumps(structured_index, separators=(',', ':'))
    
    # Improved prompt template with structured index
    prompt_template = """You are a metadata analysis assistant. Your task is to identify relevant information resources based on a user query and a structured metadata index.

STRUCTURED METADATA INDEX:
{structured_index}

USER QUERY: {query}

The structured index is organized as:
- Category ID/Ticker -> Company information including:
  - "name": The company name
  - "has_category_summary": Whether a synthesized summary exists for this company
  - "time_periods": Object mapping time periods (quarters/dates) to documents
    - Each time period contains a "documents" array with:
      - "document_id": Unique document identifier
      - "date": Document date (YYYY-MM-DD format)
      - "has_summary": Whether this document has a summary available

Based ONLY on the User Query and the STRUCTURED METADATA INDEX provided, perform the following steps:
1. Identify the primary Category ID (e.g., company ticker like 'MSFT', 'AAPL') mentioned or implied in the User Query. If none, use null.
2. For the identified category, examine the time periods to find documents matching any time period mentioned in the User Query.
3. If the query asks for 'most recent', use the first documents in the time periods (they are already sorted by recency).
4. Select up to 5 of the most relevant Document IDs based on the category and time period matching. Prioritize exact matches for quarter/year if specified.
5. Check if a synthesized Category Summary is available for the identified Category ID by checking "has_category_summary".
6. Create a list of the selected relevant Document IDs for which individual summaries are available by checking "has_summary" for each document.

Format your response strictly as a JSON object containing the following keys:
- "relevant_category_id": [string|null]
- "relevant_doc_ids": [list of strings]
- "category_summary_available": [boolean]
- "doc_ids_with_summaries": [list of strings]

Example Response:
{{
  "relevant_category_id": "MSFT",
  "relevant_doc_ids": ["doc-id-q3-2020", "doc-id-q3-2020-alt"],
  "category_summary_available": true,
  "doc_ids_with_summaries": ["doc-id-q3-2020"]
}}

CRITICAL: Your response MUST be a single valid JSON object enclosed in ```json\\n...\\n``` blocks, containing only the specified keys and value types. Do not include any other text, comments, or explanations outside the JSON structure.
"""

    return prompt_template.format(
        structured_index=structured_index_str,
        query=query
    )

# --- LLM Testing and Token Usage Measurement ---
def count_tokens(prompt_text: str) -> int:
    """Count tokens in the prompt text.
    This is a simple approximation - actual token counts may vary by model."""
    # Approximation: 1 token is roughly 4 characters for English text
    # For a more accurate count, you would use a tokenizer specific to your model
    return len(prompt_text) // 4

def test_with_llm(api_key: str, query: str, original_prompt: str, structured_prompt: str) -> Dict[str, Any]:
    """Test both approaches with an LLM and measure token usage."""
    try:
        if not api_key:
            print("No API key provided, skipping LLM test.")
            return {
                "original_tokens": count_tokens(original_prompt),
                "structured_tokens": count_tokens(structured_prompt),
                "original_result": None,
                "structured_result": None,
                "error": "No API key provided"
            }
        
        # Initialize Claude for semantic search
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            temperature=0,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Test original approach
        print(f"Testing original two-prompt approach...")
        original_start = time.time()
        original_response = llm.invoke([HumanMessage(content=original_prompt)])
        original_time = time.time() - original_start
        original_tokens = count_tokens(original_prompt)
        
        # Test structured approach
        print(f"Testing structured index approach...")
        structured_start = time.time()
        structured_response = llm.invoke([HumanMessage(content=structured_prompt)])
        structured_time = time.time() - structured_start
        structured_tokens = count_tokens(structured_prompt)
        
        # Parse responses to verify they work
        def extract_json(response):
            content = response.content if hasattr(response, 'content') else str(response)
            # Look for JSON within code blocks
            json_start = content.find("```json")
            if json_start != -1:
                json_start = content.find("\n", json_start) + 1
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                try:
                    return json.loads(json_str)
                except:
                    print(f"Error parsing JSON: {json_str}")
                    return {"error": "Failed to parse JSON"}
            else:
                # Try to parse whole response as JSON
                try:
                    return json.loads(content)
                except:
                    return {"error": "No JSON found in response"}
        
        original_result = extract_json(original_response)
        structured_result = extract_json(structured_response)
        
        return {
            "original_tokens": original_tokens,
            "structured_tokens": structured_tokens,
            "token_reduction": original_tokens - structured_tokens,
            "token_reduction_percentage": round((original_tokens - structured_tokens) / original_tokens * 100, 2),
            "original_time": original_time,
            "structured_time": structured_time,
            "time_reduction_percentage": round((original_time - structured_time) / original_time * 100, 2),
            "original_result": original_result,
            "structured_result": structured_result
        }
        
    except Exception as e:
        print(f"Error during LLM testing: {e}")
        return {
            "original_tokens": count_tokens(original_prompt),
            "structured_tokens": count_tokens(structured_prompt),
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Optimize metadata lookup tool")
    parser.add_argument("--test", action="store_true", 
                        help="Test with LLM and measure token usage")
    parser.add_argument("--query", default="What did Microsoft say about cloud services in their most recent earnings call?",
                       help="Query to test with")
    args = parser.parse_args()
    
    start_time = time.time()
    
    # 1. Connect to MongoDB and fetch metadata
    db = init_db()
    if db is None:
        print("Failed to connect to database. Exiting.")
        return
    
    # 2. Fetch all metadata
    metadata = fetch_all_metadata(db)
    if not metadata:
        print("Failed to fetch metadata. Exiting.")
        return
    
    # 3. Create structured index
    print("\nCreating structured metadata index...")
    structured_index = create_structured_metadata_index(metadata)
    print(f"Created structured index with {len(structured_index)} categories.")
    
    # 4. Generate both prompts for comparison
    query = args.query
    print(f"\nUsing test query: '{query}'")
    
    original_prompt = format_metadata_prompt_original(query, metadata)
    structured_prompt = format_metadata_prompt_structured(query, structured_index)
    
    # Calculate and display token usage comparison
    original_tokens = count_tokens(original_prompt)
    structured_tokens = count_tokens(structured_prompt)
    token_reduction = original_tokens - structured_tokens
    token_reduction_pct = token_reduction / original_tokens * 100 if original_tokens > 0 else 0
    
    print("\n--- TOKEN USAGE COMPARISON ---")
    print(f"Original approach (two prompts): {original_tokens} tokens")
    print(f"Structured index approach: {structured_tokens} tokens")
    print(f"Token reduction: {token_reduction} tokens ({token_reduction_pct:.2f}%)")
    
    # 5. Test with LLM if requested
    if args.test:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\nWarning: ANTHROPIC_API_KEY environment variable not set. Skipping LLM test.")
            print("To run the test, set the ANTHROPIC_API_KEY environment variable.")
        else:
            print("\nTesting both approaches with Claude...")
            test_results = test_with_llm(api_key, query, original_prompt, structured_prompt)
            
            print("\n--- LLM TEST RESULTS ---")
            print(f"Original approach response time: {test_results.get('original_time', 'N/A'):.2f} seconds")
            print(f"Structured approach response time: {test_results.get('structured_time', 'N/A'):.2f} seconds")
            print(f"Time reduction: {test_results.get('time_reduction_percentage', 'N/A')}%")
            
            print("\nOriginal approach result:")
            print(json.dumps(test_results.get('original_result'), indent=2))
            
            print("\nStructured approach result:")
            print(json.dumps(test_results.get('structured_result'), indent=2))
    
    # 6. Save structured index to file
    index_file = "structured_metadata_index.json"
    with open(index_file, "w") as f:
        json.dump(structured_index, f, indent=2)
    print(f"\nSaved structured index to {index_file}")
    
    elapsed_time = time.time() - start_time
    print(f"\nScript completed in {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main() 