"""
Configuration for the multi-tool hierarchical retrieval agent.
"""

from typing import Dict, Any

# Agent configuration
AGENT_CONFIG = {
    "max_iterations": 10,
    "verbose": True,
    "agent_type": "zero_shot_react_description",
    "early_stopping_method": "force",
}

# Tool descriptions for the agent
TOOL_DESCRIPTIONS = {
    "department_tool": """Use this tool first to analyze high-level information and identify relevant categories or topics.
Input: User query about any topic
Output: Initial analysis and suggested categories/topics to explore further
This tool helps understand the broad context and identifies which specific areas to investigate.
Example: For query "MU revenue", this will identify that MU (Micron) is the relevant category.""",
    
    "category_tool": """Use this tool second to analyze specific information about the company/category based on its summary.
Input should be in format: \"<query>, category=<CATEGORY_ID>\"
Example: \"how has MU revenue grown over the past 5 years, category=MU\"
Output: Text analysis based on the summary.""",

    "metadata_lookup_tool": """Use this tool to map user queries or specific terms to the most relevant Category Name and/or Transcript Filename available in the metadata.
Input: A natural language query, or a specific term like a category ticker (e.g., 'AMZN'), a date (e.g., 'Q2 2022', '2023-10-26'), or a partial/full filename (e.g., '2023-Oct-26-AMZN.txt').
Output: A dictionary containing 'category_name' (the single most relevant category string or None) and 'transcript_name' (the single most relevant filename string or None).
How to use:
- If the query is general (e.g., 'Amazon cloud growth'), the tool finds the most likely relevant category/transcript.
- If the query is specific (e.g., 'AMZN', '2023-Oct-26-AMZN.txt'), the tool confirms and returns the exact match from metadata if found.
- Use the output 'category_name' for the 'category_tool' and 'transcript_name' for the 'transcript_analysis_tool'.""",

    "document_analysis_tool": """Use this tool to analyze a specific document. Input should be in the format: \"<query>, document_id=<UUID>\". Output includes the analysis of the document.""",

    "transcript_analysis_tool": """Use this tool ONLY when you need to answer a specific question using the content of a KNOWN document (e.g., an earnings call transcript identified by metadata_lookup_tool). Input MUST be in the format: \"<query>, document_name=<filename.txt>\". The tool fetches the document content and uses an LLM to answer the query based *only* on that document. Do NOT use this for general queries or if you don't know the exact filename."""
}

# Agent prompt template
AGENT_PROMPT = """You are a hierarchical information retrieval agent. Your goal is to answer user queries, primarily about company financial performance based on available summaries and documents.

AVAILABLE CONTEXT:

**TECH Department Summary Overview:**
Over the period from 2016 to mid-2020, the tech department (AAPL, AMZN, MU, NVDA) showed strong performance driven by cloud, AI, 5G, and IoT. Key themes included robust revenue growth, expansion into new markets, heavy R&D, and margin improvement from mix shifts. Risks include cyclicality, geopolitical tensions (especially US-China), and competition.

**Database Schema Overview:**
- Database: earnings_transcripts
  - Collection: `transcripts` (Main store for earnings call transcripts)
    - Key Fields: `_id` (ObjectId), `document_id` (UUID String, used for linking), `category_id` (e.g., "AAPL"), `date` (datetime), `filename` (string), `quarter` (int), `fiscal_year` (int), `transcript_text` (string)
  - Collection: `category_summaries` (Stores pre-generated summaries for categories)
    - Key Fields: `_id` (ObjectId), `category_id` (string), `document_ids` (List of UUID Strings from `transcripts`), summary_text (string)
  - Collection: `department_summaries` (Stores pre-generated summaries for departments)
    - Key Fields: `_id` (ObjectId), `department_id` (string, e.g., "TECH"), `category_ids` (List of strings), summary_text (string)

AVAILABLE TOOLS:
{tools}

You have access to the following tools:
{tool_names}

GENERAL WORKFLOW GUIDANCE:
1. Start Broad: Use 'department_tool' first for queries about specific sectors or companies if unsure about the category.
2. Identify Category/Transcript: Use 'metadata_lookup_tool'. Provide the most specific term you can extract from the user query (e.g., ticker, date, partial filename) as input. If the query is general, use the core query topic. This tool will return the most relevant 'category_name' and/or 'transcript_name' found in the metadata.
3. Analyze Category Info: If 'metadata_lookup_tool' returned a valid 'category_name', use 'category_tool' to get insights from its summary. Format: \"<query>, category=<category_name>\"
4. Analyze Specific Transcript: If 'metadata_lookup_tool' returned a valid 'transcript_name' AND the query requires details *from that specific transcript*, use 'transcript_analysis_tool'. Format: \"<query>, document_name=<transcript_name>\"
5. Synthesize and Answer: Combine the information gathered from the tools used to formulate the final answer.

Follow the ReAct format strictly:
Thought: Explain your reasoning and plan for the next step. Clearly state which tool you are using and why. Specify *what* you are providing as input to metadata_lookup_tool. Check its output ('category_name', 'transcript_name') to decide the next step.
Action: The name of the tool to use (from the list {tool_names}).
Action Input: The input required for the selected tool, formatted EXACTLY as specified in the tool description (e.g., \"AMZN Q2 2022\" for metadata_lookup_tool, \"revenue growth?, category=AMZN\" for category_tool, \"details on AWS?, document_name=XYZ.txt\" for transcript_analysis_tool).
Observation: The result returned from the tool.

If you have enough information to answer the question:
Final Answer: Your final answer.

Begin!

Question: {input}
{agent_scratchpad}"""

# Custom output parser configuration
OUTPUT_PARSER_CONFIG = {
    "required_fields": ["thought", "action", "action_input"],
    "optional_fields": ["observation", "final_answer"],
    "output_format": {
        "status": "success",
        "result": "<final_answer>"
    }
}

def get_agent_config() -> Dict[str, Any]:
    """Get the agent configuration"""
    return AGENT_CONFIG

def get_tool_descriptions() -> Dict[str, str]:
    """Get the tool descriptions"""
    return TOOL_DESCRIPTIONS

def get_agent_prompt() -> str:
    """Get the agent prompt template"""
    return AGENT_PROMPT 

def category_tool_response_structure() -> Dict[str, Any]:
    """Get the expected response structure for category tool"""
    return {
        "summary": "comprehensive analysis...",
        "relevant_doc_ids": [],  # Explicit parameter for next layer
        "confidence": 0
    } 