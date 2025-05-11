#!/usr/bin/env python3
"""
Mock test script for the two-layer earnings call analysis approach
"""

import json
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockLLM:
    """Mock LLM class that returns predefined responses"""
    
    def __init__(self, model="claude-3-haiku-20240307"):
        self.model = model
        self.call_count = 0
        
    def invoke(self, messages):
        """Return mock responses based on message content"""
        self.call_count += 1
        query = messages[0].content if messages else "No query provided"
        
        # For specific query types
        if "AMZN" in query and "AAPL" in query and "computing growth" in query:
            return {
                "content": self._generate_comparison_response()
            }
        
        # Default generic response
        return {
            "content": f"This is a mock response for query: {query[:50]}..."
        }
    
    def _generate_comparison_response(self):
        """Generate a mock comparison between AMZN and AAPL computing growth"""
        return """
# Comparative Analysis: Amazon vs. Apple Computing Growth in 2018

## Amazon (AMZN) Computing Growth
- AWS continued to be a key growth driver with revenue increasing by approximately 47% year-over-year in 2018
- AWS reached a $30 billion annual run rate by the end of 2018
- Expanded AWS to new geographic regions including Bahrain and Sweden
- Introduced over 1,800 new AWS services and features in 2018
- Key areas of growth included machine learning services, database solutions, and serverless computing

## Apple (AAPL) Computing Growth
- Mac revenue grew by approximately 3% in fiscal 2018
- iPad revenue increased after several quarters of decline, growing approximately 6% 
- Services segment (includes iCloud, App Store) was the fastest growing segment at around 24% growth
- Apple continued investing in its custom silicon with the A12 Bionic chip
- Growth in enterprise adoption of Apple products, particularly in mobile computing

## Key Differences
- Amazon's computing growth was primarily cloud-focused (B2B) while Apple remained consumer-hardware focused
- AWS showed much higher growth rates (40%+) compared to Apple's single-digit hardware growth
- Apple's computing services grew faster than its hardware segments
- Amazon invested heavily in AI/ML infrastructure, while Apple focused on on-device AI

## Outlook
- Both companies were well-positioned for continued computing growth, though in different segments
- AWS expected to remain a dominant cloud provider with continued strong growth
- Apple's services segment expected to drive future computing growth more than traditional hardware
"""
    
    def completion(self, prompt):
        """Legacy format completion method"""
        self.call_count += 1
        return {"choices": [{"text": f"Mock response for: {prompt[:50]}..."}]}

# Mock functions for the two-layer approach
def mock_document_summaries_analysis(query: str, document_ids: List[str]) -> Dict[str, Any]:
    """Mock function for document summaries analysis"""
    logger.info(f"[Mock Summaries] Analyzing documents: {document_ids} for query: {query}")
    
    if "AMZN" in query or "Amazon" in query:
        company = "Amazon"
        growth = "AWS grew by 47% in 2018, reached $30B annual run rate, added 1,800+ new services"
    elif "AAPL" in query or "Apple" in query:
        company = "Apple"
        growth = "Mac grew 3%, iPad 6%, Services 24% in 2018; focus on custom silicon with A12 Bionic"
    else:
        company = "Unknown"
        growth = "No specific growth data found"
    
    return {
        "answer": f"{company} computing growth in 2018: {growth}",
        "error": None,
        "documents_analyzed": document_ids,
        "document_metadata": [{"document_id": doc_id, "ticker": doc_id[:4]} for doc_id in document_ids]
    }

def mock_full_document_analysis(query: str, document_id: str, chunk_index: Optional[int] = None) -> Dict[str, Any]:
    """Mock function for full document analysis"""
    logger.info(f"[Mock Full Doc] Analyzing document {document_id}, chunk {chunk_index} for query: {query}")
    
    if "AMZN" in document_id or "Amazon" in query:
        company = "Amazon"
        details = """
        AWS continued strong growth in 2018:
        - Q1: 49% YoY growth
        - Q2: 48% YoY growth
        - Q3: 46% YoY growth
        - Q4: 45% YoY growth
        Key product launches included new database services, machine learning capabilities, and serverless computing options.
        """
    elif "AAPL" in document_id or "Apple" in query:
        company = "Apple"
        details = """
        Apple's computing segments in 2018:
        - Mac: $25.5B revenue, 3% YoY growth
        - iPad: $18.8B revenue, 6% YoY growth
        - Services (including computing services): $39.7B, 24% YoY growth
        The company focused on premium positioning and integration across its computing ecosystem.
        """
    else:
        company = "Unknown"
        details = "No detailed information available for this document."
    
    return {
        "answer": f"Detailed {company} computing growth analysis: {details}",
        "error": None,
        "document_id": document_id,
        "document_name": f"{company} 2018 Annual Report",
        "current_chunk": chunk_index or 0,
        "total_chunks": 1,
        "has_more_chunks": False,
        "next_chunk": None
    }

def simulate_two_layer_analysis(query: str) -> Dict[str, Any]:
    """Simulate the two-layer analysis approach"""
    logger.info(f"[Simulation] Starting two-layer analysis for query: {query}")
    
    # Step 1: Determine relevant companies
    companies = []
    if "AMZN" in query or "Amazon" in query:
        companies.append("AMZN")
    if "AAPL" in query or "Apple" in query:
        companies.append("AAPL")
    
    # If no companies specified, default to both for this demo
    if not companies:
        companies = ["AMZN", "AAPL"]
    
    logger.info(f"[Simulation] Identified companies: {companies}")
    
    # Step 2: Generate mock document IDs
    document_ids = [f"{company}-2018-Q4-REPORT" for company in companies]
    logger.info(f"[Simulation] Using document IDs: {document_ids}")
    
    # Step 3: First layer - analyze document summaries
    summaries_result = mock_document_summaries_analysis(query, document_ids)
    logger.info(f"[Simulation] Summaries analysis complete, extracted key information")
    
    # Step 4: Second layer - analyze full documents only if necessary
    # For demo purposes, we'll analyze one document fully
    if "detailed" in query.lower() or "in-depth" in query.lower():
        logger.info(f"[Simulation] Detailed information requested, proceeding to full document analysis")
        full_doc_results = [mock_full_document_analysis(query, doc_id) for doc_id in document_ids]
        detailed_info = "\n\n".join([result["answer"] for result in full_doc_results])
    else:
        logger.info(f"[Simulation] Summary information sufficient, skipping full document analysis")
        detailed_info = None
    
    # Step 5: Generate final response
    if "AMZN" in companies and "AAPL" in companies:
        llm = MockLLM()
        final_response = llm._generate_comparison_response()
    else:
        company = "Amazon" if "AMZN" in companies else "Apple"
        final_response = f"{company} computing growth in 2018: {summaries_result['answer']}"
        if detailed_info:
            final_response += f"\n\nDetailed analysis:\n{detailed_info}"
    
    return {
        "query": query,
        "companies_analyzed": companies,
        "documents_analyzed": document_ids,
        "used_full_documents": "detailed" in query.lower(),
        "response": final_response
    }

def main():
    """Run the simulation with multiple test queries"""
    test_queries = [
        "amzn vs aapl 2018 computing growth",
        "detailed analysis of amzn vs aapl 2018 computing growth"
    ]
    
    for i, test_query in enumerate(test_queries):
        print(f"\n\n===== TEST QUERY {i+1}: {test_query} =====")
        
        result = simulate_two_layer_analysis(test_query)
        
        print("\n--- ANALYSIS PROCESS ---")
        print(f"Companies analyzed: {', '.join(result['companies_analyzed'])}")
        print(f"Documents used: {', '.join(result['documents_analyzed'])}")
        print(f"Full document analysis performed: {'Yes' if result['used_full_documents'] else 'No - summaries were sufficient'}")
        
        print("\n--- FINAL RESPONSE ---")
        print(result["response"])
        
        print("\n" + "="*80)

if __name__ == "__main__":
    main() 