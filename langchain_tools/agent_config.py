"""
Configuration for the multi-tool hierarchical retrieval agent (Financial and Risk Analyst).
Dynamically fetches examples for tool descriptions.
"""

import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# --- Constants ---
# Assuming DBs are in the project root or a standard 'data' subfolder
# Adjust these relative paths if DBs are located elsewhere
FINANCIAL_DB_RELATIVE_PATH = "financial_data.db"
CCR_DB_RELATIVE_PATH = "ccr_reporting.db"

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- Helper Functions ---

# Basic project root finding (adjust if needed)
def _get_project_root() -> str:
    """Find the project root based on this file's location."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _get_db_path(relative_path: str) -> Optional[str]:
    """Construct absolute path for DB, return None if not found."""
    project_root = _get_project_root()
    # Prefer path from .env if set, otherwise try relative path
    env_var_name = "FINANCIAL_DB_PATH" if "financial" in relative_path else "CCR_DB_PATH"
    load_dotenv(os.path.join(project_root, '.env')) # Ensure .env is loaded
    db_path_env = os.getenv(env_var_name)

    if db_path_env:
        if os.path.exists(db_path_env):
            logger.info(f"Using DB path from env var {env_var_name}: {db_path_env}")
            return db_path_env
        else:
            logger.warning(f"DB path from env var {env_var_name} does not exist: {db_path_env}")

    # Fallback to relative path calculation
    potential_paths = [
        os.path.join(project_root, relative_path),
        os.path.join(project_root, 'data', relative_path),
        os.path.join(project_root, 'scripts', 'data', relative_path)
    ]

    for path in potential_paths:
        if os.path.exists(path):
            logger.info(f"Using DB path: {path}")
            return path
        else:
            logger.debug(f"Tried DB path (not found): {path}")

    logger.warning(
        f"Database file not found. Tried:\n"
        f"1. Environment variable '{env_var_name}': {db_path_env or 'not set'}\n"
        f"2. Relative paths:\n   " + "\n   ".join(potential_paths)
    )
    return None


def _fetch_db_examples(db_rel_path: str, query: str, limit: int = 3) -> List[str]:
    """Connects to DB, runs query to fetch examples, handles errors."""
    db_path = _get_db_path(db_rel_path)
    if not db_path:
        return [] # Return empty list if DB not found

    examples = []
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query) # Query already includes LIMIT
        results = cursor.fetchall()
        examples = [str(row[0]) for row in results] # Get first column as string
        logger.info(f"Fetched {len(examples)} examples from {db_rel_path} using query: {query}")
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch examples from {db_rel_path}: {e}")
        # Optionally return empty list or re-raise
    finally:
        if conn:
            conn.close()
    return examples


# --- Agent Configuration ---
AGENT_CONFIG = {
    "max_iterations": 5,
    "verbose": True,
    "agent_type": "zero_shot_react_description",
    "early_stopping_method": "generate",
}

# --- Base Tool Descriptions (Templates) ---
BASE_TOOL_DESCRIPTIONS = {
    "financial_sql_query_tool": (
        "Queries a database containing structured financial market data. Use this for specific questions about historical stock prices (daily OHLC data **available for 2016-2020** for tickers like **{financial_examples}**, etc.), "
        "historical quarterly financials (income/balance sheet, limited dates), dividends, or stock splits. Input is a natural language question about specific data points."
        " Persona: SQL Database Expert (Financial Data)."
    ),
    "ccr_sql_query_tool": (
        "Queries a database containing structured Counterparty Credit Risk (CCR) reporting data. Use this for specific questions about daily limit utilization, breach status, "
        "calculated aggregate exposures (Net MTM, Gross Exposure, PFE, Settlement Risk), collateral, current limits per risk type/asset class, or specific trades related to counterparties (using identifiers like **{ccr_examples}**, etc.). Input is a natural language question about specific CCR metrics."
        " Persona: SQL Database Expert (CCR Data)."
    ),
    "transcript_search_summary_tool": (
         "Answers questions requiring qualitative analysis, summaries, or context from **earnings call transcripts**. Use for queries about company performance narratives, strategies, management commentary, outlook, or specific events discussed in calls (e.g., queries like **'What was management\'s outlook for cloud growth in the MSFT Q4 2020 call?'**). Input should be the original user query."
         " Persona: Equity Research Analyst (Transcript Specialist)."
    ),
}

# --- Dynamic Tool Description Generation ---
def get_tool_descriptions() -> Dict[str, str]:
    """
    Generates tool descriptions, dynamically fetching examples from databases.
    Falls back to generic examples if DB fetching fails.
    """
    # Fetch examples
    fin_examples = _fetch_db_examples(
        FINANCIAL_DB_RELATIVE_PATH,
        "SELECT DISTINCT ticker FROM daily_stock_prices WHERE ticker IS NOT NULL ORDER BY ticker LIMIT 3"
    )
    ccr_examples = _fetch_db_examples(
        CCR_DB_RELATIVE_PATH,
        "SELECT DISTINCT short_name FROM report_counterparties WHERE short_name IS NOT NULL ORDER BY short_name LIMIT 3"
    )

    # Format examples or use fallbacks
    fin_examples_str = ', '.join(f"'{ex}'" for ex in fin_examples) if fin_examples else "'AAPL', 'MSFT', 'GOOG'"
    ccr_examples_str = ', '.join(f"'{ex}'" for ex in ccr_examples) if ccr_examples else "'HF Alpha', 'Pension B', 'EuroBank G'" # Fallback examples from schema script

    # Populate templates
    final_descriptions = {}
    for tool_name, template in BASE_TOOL_DESCRIPTIONS.items():
        try:
            final_descriptions[tool_name] = template.format(
                financial_examples=fin_examples_str,
                ccr_examples=ccr_examples_str
                # Add other placeholders if needed
            )
        except KeyError:
            # If a template doesn't need formatting, use it directly
            final_descriptions[tool_name] = template

    return final_descriptions


# --- Master Agent Prompt ---
MASTER_AGENT_PROMPT = """You are a diligent **Financial and Risk Analyst**. Your primary function is to understand user queries and route them accurately to the appropriate specialized tool based on the type of information required. You must be careful to attribute information to its source.

You have access to the following specialized tools:

{tools}

Based on the user's query, determine the most appropriate data source and tool:
- For specific, quantitative facts about **historical stock market data or company financials** likely in a structured database (prices, dividends, quarterly revenue/income figures from 2016-2020), use the 'financial_sql_query_tool'.
- For specific, quantitative facts about **Counterparty Credit Risk (CCR)** data (exposures, limits, utilization) likely in a structured database, use the 'ccr_sql_query_tool'.
- For **qualitative analysis, summaries, context, management commentary, strategy discussions, or performance narratives** requiring interpretation of **earnings call transcripts** or other documents, use the 'transcript_search_summary_tool'.

Use the following format precisely:

Question: The input question you must answer.
Thought: As a Financial and Risk Analyst, I must first analyze the query to identify the core information need. Is it asking for specific structured data (financial markets, CCR) or for qualitative analysis/summary of unstructured text (transcripts)? Based on this, I will select the single best specialized tool. I need to explain my reasoning for choosing this tool, referencing the type of query and the tool's specialization using its description.
Action: The name of the single most appropriate tool to use (must be one of [{tool_names}]).
Action Input: The input required for the selected tool (usually the original user query, unless the tool description specifies otherwise).
Observation: The direct result received from the specialized tool.
Thought: I have received the response from the specialized tool ([Tool Name]). This tool acts as a specialist ([Tool Persona mentioned in its description]). I will now present this information clearly, attributing it directly to the specialist tool's analysis.
Final Answer: Based on the analysis performed by the specialized [Tool Name] ([Tool Persona]), here is the response to your query: [Insert the full Observation received from the tool here].

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

# --- Custom Output Parser Configuration ---
OUTPUT_PARSER_CONFIG = {
    "required_fields": ["thought", "action", "action_input"],
    "optional_fields": ["observation", "final_answer"],
    "output_format": {
        "status": "success",
        "result": "<final_answer>"
    }
}

# --- Getter Functions ---
def get_agent_config() -> Dict[str, Any]:
    """Get the agent configuration"""
    return AGENT_CONFIG

# get_tool_descriptions() is now defined above

def get_agent_prompt() -> str:
    """Get the agent prompt template"""
    return MASTER_AGENT_PROMPT

def category_tool_response_structure() -> Dict[str, Any]:
    """Get the expected response structure for category tool (might be deprecated for main agent)."""
    return {
        "summary": "comprehensive analysis...",
        "relevant_doc_ids": [],
        "confidence": 0
    } 