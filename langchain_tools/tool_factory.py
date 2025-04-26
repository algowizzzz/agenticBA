"""
Factory for creating and configuring tools with consistent interfaces.
"""

import os
import logging
from typing import Callable, Dict, Any, Optional, Tuple, List
import json
from langchain_anthropic import ChatAnthropic
from datetime import datetime
import re

# Import utility modules
from .config import sanitize_json_response
# from .tool3_document import get_tool as get_document_tool # REMOVE Import for deleted tool
from .tool4_metadata_lookup import get_tool as get_metadata_lookup_tool
# from .tool3_document_analysis import get_tool as get_document_analysis_tool # REMOVE Import
# from .tool5_simple_llm import get_tool as get_simple_llm_tool # Import new tool
from .tool5_transcript_analysis import get_transcript_analysis_tool # Import renamed transcript analysis tool

# Added imports for SQL Tool
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain # Changed import
from langchain.tools import Tool
from langchain_core.language_models import BaseChatModel # Correct import path
from langchain_core.prompts import PromptTemplate # <--- Added import
from langchain.agents import AgentExecutor, create_react_agent # <--- Added create_react_agent
import sqlite3 # Added for specific error handling
import traceback # Added for detailed error logging

# Configure logging
logger = logging.getLogger(__name__)

def create_llm(api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20240620", temperature: float = 0) -> ChatAnthropic:
    """
    Create an instance of the ChatAnthropic LLM.
    
    Args:
        api_key (str, optional): Anthropic API key. If None, uses environment variable.
        model (str): Model name to use
        temperature (float): Temperature for generation
        
    Returns:
        ChatAnthropic: Configured LLM instance
    """
    # Use provided API key or try environment variable
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not provided and not found in environment")
    
    logger.info(f"Initializing ChatAnthropic with model: {model}")
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        anthropic_api_key=api_key
    )

def create_tool_with_validation(tool_fn: Callable, tool_name: str, response_validator: Callable) -> Callable:
    """Create a tool with validation and metadata handling."""
    def validated_tool(*args, **kwargs) -> Dict[str, Any]:
        try:
            # Execute the tool
            result = tool_fn(*args, **kwargs)
            
            # Validate the response
            is_valid, errors = response_validator(result)
            if not is_valid:
                logger.error(f"Invalid {tool_name} response: {errors}")
                return {
                    "thought": f"Tool response validation failed: {errors}",
                    "answer": "Error: Tool response did not meet requirements",
                    "confidence": 0,
                    "metadata": {
                        "tool_name": tool_name,
                        "validation_errors": errors,
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": False
                    }
                }
            
            # Add metadata if not present
            if "metadata" not in result:
                result["metadata"] = {}
            result["metadata"].update({
                "tool_name": tool_name,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {tool_name}: {e}")
            return {
                "thought": f"Error in {tool_name}: {str(e)}",
                "answer": f"An error occurred while using {tool_name}",
                "confidence": 0,
                "metadata": {
                    "tool_name": tool_name,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False
                }
            }
    
    return validated_tool

def create_department_tool(api_key: Optional[str] = None) -> Callable:
    """Create department tool with validation."""
    from langchain_tools.tool1_department import department_summary_tool
    
    def department_tool(query: str) -> Dict[str, Any]:
        """
        Analyze department-level summaries to determine if a query can be answered
        at the high level or identify which specific category (company) to explore next.
        
        Args:
            query (str): User query about companies or trends
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        return department_summary_tool(query, api_key)
    
    # Copy attributes for better display
    department_tool.__name__ = "department_summary_tool"
    department_tool.__doc__ = department_summary_tool.__doc__
    
    return create_tool_with_validation(
        department_tool,
        "department_tool",
        validate_department_response
    )

def create_category_tool() -> Callable:
    """Create category tool with validation."""
    from .tool2_category import category_summary_tool
    
    # Modify to accept single string input and parse
    def category_tool_wrapper(input_str: str) -> Dict[str, Any]:
        """
        Analyze category-level summaries. Input format: "<query>, category=<CATEGORY_ID>"
        """
        # Parse query and category_id from the input string
        query = input_str
        category_id = None
        match = re.search(r"category=([\w\-]+)", input_str, re.IGNORECASE)
        if match:
            category_id = match.group(1)
            # Remove the category part from the query string if desired
            query = re.sub(r"\\s*category=[\w\-]+", "", query, flags=re.IGNORECASE).strip().rstrip(',') # Remove tag and potential trailing comma
        else:
            # Handle cases where category_id might be missing in the input
            # Option 1: Raise an error
            # raise ValueError("Input string must contain 'category=<CATEGORY_ID>'")
            # Option 2: Log a warning and proceed without category_id (might fail later)
            logger.warning(f"Category ID not found in input: '{input_str}'. Tool might fail.")
            # Option 3: Attempt to infer category if possible (complex)
            # For now, we proceed but expect category_summary_tool to handle None category_id if applicable

        if not category_id:
             # Return an error if category_id is essential and wasn't found
             return {"error": "Category ID missing in input format 'query, category=<ID>'"}
        
        # Remove api_key argument as it's not accepted by category_summary_tool
        # return category_summary_tool(query, category_id, api_key)
        return category_summary_tool(query, category_id)
    
    # Copy attributes for better display
    category_tool_wrapper.__name__ = "category_summary_tool"
    category_tool_wrapper.__doc__ = category_summary_tool.__doc__ # Keep original tool doc? Or use wrapper's?
    
    return create_tool_with_validation(
        category_tool_wrapper,
        "category_tool",
        validate_category_response
    )

def create_metadata_lookup_tool() -> Callable:
    """Create metadata lookup tool with validation."""
    # Get the actual tool function by calling its factory
    metadata_lookup_fn = get_metadata_lookup_tool()

    # Define a simple wrapper if needed (optional, could use fn directly)
    def metadata_lookup_wrapper(query_term: str) -> Dict[str, Any]:
         return metadata_lookup_fn(query_term)

    # Copy attributes for better display
    metadata_lookup_wrapper.__name__ = getattr(metadata_lookup_fn, '__name__', "metadata_lookup_tool")
    metadata_lookup_wrapper.__doc__ = getattr(metadata_lookup_fn, '__doc__', "Finds category/document IDs by metadata term.")

    return create_tool_with_validation(
        metadata_lookup_wrapper,
        "metadata_lookup_tool",
        validate_metadata_lookup_response
    )

def create_transcript_analysis_tool(api_key: Optional[str] = None) -> Callable:
    """Create transcript analysis tool with validation."""
    # Import renamed factory function
    transcript_analysis_fn = get_transcript_analysis_tool(api_key)

    # Wrapper to parse single string input from agent: "query, document_name=<name>"
    def transcript_analysis_wrapper(input_str: str) -> Dict[str, Any]:
        """Wrapper for transcript analysis tool. Input format: '<query>, document_name=<name>'"""
        query = input_str
        doc_name = None
        # Look for the mandatory document_name parameter
        match = re.search(r"document_name=([\w\.\-]+)", input_str, re.IGNORECASE)
        if match:
            doc_name = match.group(1)
            # Remove the parameter part from the query string
            query = re.sub(r",?\s*document_name=[\w\.\-]+$", "", query, flags=re.IGNORECASE).strip().rstrip(',')
            logger.debug(f"Transcript analysis wrapper parsed query='{query}', doc_name='{doc_name}'")
            # Call the actual tool function with parsed args
            return transcript_analysis_fn(query=query, document_name=doc_name)
        else:
            # Document name is required by the underlying tool now
            logger.error(f"Transcript analysis wrapper failed: document_name missing in input: '{input_str}'")
            return {"answer": "Error: Input format requires 'document_name=<filename>'", "error": "Missing document_name"}

    # Use attributes from the actual tool function
    transcript_analysis_wrapper.__name__ = getattr(transcript_analysis_fn, '__name__', "transcript_analysis_tool")
    transcript_analysis_wrapper.__doc__ = getattr(transcript_analysis_fn, '__doc__', "Analyzes a specific document transcript.")

    return create_tool_with_validation(
        transcript_analysis_wrapper,
        "transcript_analysis_tool", # Tool name used in metadata/logging
        validate_transcript_analysis_response # Use renamed validation function
    )

# --- SQL Tool Factories ---

# Renamed and potentially slightly adjusted for clarity
def create_financial_sql_tool(db_path: str, llm: BaseChatModel) -> Tool:
    """
    Creates a tool to query the FINANCIAL database (stocks, historical financials).
    Includes database metadata in the prompt and returns structured output.
    Uses SQLDatabaseChain for direct query generation and execution.
    DB targeted: financial_data.db
    """
    db_uri = f"sqlite:///{db_path}"
    logger.info(f"[Financial Tool] Connecting to SQL Database: {db_uri}")

    # --- Metadata Helper for Financial DB ---
    def _get_financial_db_metadata(db_conn, db_object) -> str:
        """Queries Financial DB for metadata like date ranges and ALL tickers."""
        metadata_parts = []
        cursor = db_conn.cursor()
        try:
            metadata_parts.append("FINANCIAL Database Schema Overview:")
            usable_tables = db_object.get_usable_table_names()
            table_info = db_object.get_table_info(usable_tables)
            metadata_parts.append(table_info)
            metadata_parts.append("\nKey Financial Tables & Usage Hints:")

            # Companies Table - Fetch ALL tickers
            if 'companies' in usable_tables:
                try:
                    cursor.execute("SELECT DISTINCT ticker FROM companies ORDER BY ticker")
                    tickers = [row[0] for row in cursor.fetchall()]
                    if tickers:
                        # Include the full list in the hint (No explicit brace escaping)
                        metadata_parts.append(f"- `companies`: Company names and tickers. **Full list of known tickers: [{', '.join(tickers)}]**.")
                    else:
                         metadata_parts.append("- `companies`: Company names and tickers. (No tickers found).")
                except Exception as e:
                     logger.warning(f"[Financial Tool] Could not fetch full ticker list: {e}")
                     metadata_parts.append("- `companies`: Company names and tickers. Error fetching full list.")

            # Daily Stock Prices Table
            if 'daily_stock_prices' in usable_tables:
                try:
                    cursor.execute("SELECT MIN(date), MAX(date) FROM daily_stock_prices")
                    min_date, max_date = cursor.fetchone() or ('N/A', 'N/A')
                    metadata_parts.append(f"- `daily_stock_prices`: Daily OHLC prices/volume. Data available from {min_date} to {max_date}. Use 'YYYY-MM-DD'. Filter by `ticker`.")
                except Exception as e:
                     logger.warning(f"[Financial Tool] Could not fetch date range for daily_stock_prices: {e}")
                     metadata_parts.append("- `daily_stock_prices`: Daily OHLC prices/volume. Use 'YYYY-MM-DD'. Filter by `ticker`.")

            # Quarterly Income Statement Table
            if 'quarterly_income_statement' in usable_tables:
                try:
                    cursor.execute("SELECT MIN(report_date), MAX(report_date) FROM quarterly_income_statement")
                    min_date, max_date = cursor.fetchone() or ('N/A', 'N/A')
                    metadata_parts.append(f"- `quarterly_income_statement`: Quarterly income data (e.g., revenue, net_income). Data available from {min_date} to {max_date}. Use `report_date` 'YYYY-MM-DD'. Filter by `ticker`.")
                except Exception as e:
                     logger.warning(f"[Financial Tool] Could not fetch date range for quarterly_income_statement: {e}")
                     metadata_parts.append("- `quarterly_income_statement`: Quarterly income data. Use `report_date` 'YYYY-MM-DD'. Filter by `ticker`.")

            # Quarterly Balance Sheet Table
            if 'quarterly_balance_sheet' in usable_tables:
                try:
                    cursor.execute("SELECT MIN(report_date), MAX(report_date) FROM quarterly_balance_sheet")
                    min_date, max_date = cursor.fetchone() or ('N/A', 'N/A')
                    metadata_parts.append(f"- `quarterly_balance_sheet`: Quarterly balance sheet data. Data available from {min_date} to {max_date}. Use `report_date` 'YYYY-MM-DD'. Filter by `ticker`.")
                except Exception as e:
                     logger.warning(f"[Financial Tool] Could not fetch date range for quarterly_balance_sheet: {e}")
                     metadata_parts.append("- `quarterly_balance_sheet`: Quarterly balance sheet data. Use `report_date` 'YYYY-MM-DD'. Filter by `ticker`.")
            
            # Dividends Table Hint (Optional)
            if 'dividends' in usable_tables:
                 metadata_parts.append("- `dividends`: Historical dividend payment amounts and dates. Filter by `ticker`.")
            
            # Stock Splits Table Hint (Optional)
            if 'stock_splits' in usable_tables:
                 metadata_parts.append("- `stock_splits`: Historical stock split dates and ratios. Filter by `ticker`.")

            metadata_parts.append("\nFinancial Querying Tips:")
            metadata_parts.append("- **Always** filter by `ticker` using the known tickers list provided above.")
            metadata_parts.append("- Use 'YYYY-MM-DD' format for dates (`date` in daily_stock_prices, `report_date` in quarterly tables, `ex_dividend_date` in dividends). ")
            metadata_parts.append("- Price data is in `daily_stock_prices`.")
            metadata_parts.append("- Quarterly financial data is in `quarterly_income_statement` and `quarterly_balance_sheet`.")

        except Exception as e:
            logger.error(f"[Financial Tool] Error generating DB metadata: {e}")
            metadata_parts.append("\nError: Could not dynamically generate full metadata hints.")
        finally:
            cursor.close()

        return "\n".join(metadata_parts)
    # --- End Metadata Helper ---

    try:
        # Establish connections
        conn = sqlite3.connect(db_path)
        db = SQLDatabase.from_uri(db_uri)
        logger.info(f"[Financial Tool] SQLDatabase connection successful. Tables: {db.get_usable_table_names()}")

        db_metadata_string = _get_financial_db_metadata(conn, db)
        conn.close()
        logger.info("[Financial Tool] Generated DB Metadata Hints for LLM.")

        sql_chain = SQLDatabaseChain.from_llm(llm, db, verbose=False, return_intermediate_steps=False)
        logger.info("[Financial Tool] SQLDatabaseChain created successfully.")

        # --- Tool Execution Wrapper (Refactored) ---
        def _run_financial_sql_wrapper(query: str) -> Dict[str, str]:
            """Wraps SQL execution for financial data: generates SQL, executes, formats answer."""
            
            # Define template as a regular string with distinct placeholders
            sql_generation_prompt_template_base = """
Given the FINANCIAL database schema and hints below, generate a SQL query to answer the user's question.
**IMPORTANT INSTRUCTIONS**:
1.  **ONLY** return the raw SQL query. Do NOT include explanations, markdown formatting, or anything else.
2.  Use the **Full list of known tickers** provided in the hints to map user query names/IDs correctly.
3.  Use the provided schema, hints, and examples below accurately.

Schema and Hints:
%%DB_METADATA%%

**Examples (Financial DB):**

Example 1 (Specific Stock Price):
User Query: What was the closing price for MSFT on 2020-05-15?
SQL Query: SELECT close FROM daily_stock_prices WHERE ticker = 'MSFT' AND date = '2020-05-15'

Example 2 (Dividend Check):
User Query: Did GOOG pay dividends in 2019?
SQL Query: SELECT date, dividend_amount FROM dividends WHERE ticker = 'GOOG' AND date BETWEEN '2019-01-01' AND '2019-12-31' LIMIT 1

Example 3 (Multiple Columns / Range):
User Query: Show the high and low prices for AAPL between 2020-03-01 and 2020-03-05.
SQL Query: SELECT date, high, low FROM daily_stock_prices WHERE ticker = 'AAPL' AND date BETWEEN '2020-03-01' AND '2020-03-05' ORDER BY date

Example 4 (Quarterly Financials):
User Query: What was the net income for MSFT reported around March 2020?
SQL Query: SELECT report_date, net_income FROM quarterly_income_statement WHERE ticker = 'MSFT' AND report_date BETWEEN '2020-01-01' AND '2020-03-31' ORDER BY report_date DESC LIMIT 1

Example 5 (Aggregation / Range):
User Query: What was the highest closing price for AMZN in Q1 2020?
SQL Query: SELECT MAX(close) FROM daily_stock_prices WHERE ticker = 'AMZN' AND date BETWEEN '2020-01-01' AND '2020-03-31'

Example 6 (Comparison / Multiple Tickers):
User Query: Compare the quarterly revenue reported by GOOG and MSFT around December 2019.
SQL Query: SELECT ticker, report_date, total_revenue FROM quarterly_income_statement WHERE ticker IN ('GOOG', 'MSFT') AND report_date BETWEEN '2019-10-01' AND '2019-12-31' ORDER BY ticker, report_date

Example 7 (Relative Date / Subquery):
User Query: give me historical 1 week price data for aapl, it will use latest date for that
SQL Query: SELECT date, close FROM daily_stock_prices WHERE ticker = 'AAPL' AND date >= (SELECT DATE(MAX(date), '-6 days') FROM daily_stock_prices WHERE ticker = 'AAPL') ORDER BY date

**(End of Examples)**

User Query: {query}

SQL Query: """
            
            # Step 1: Replace metadata placeholder after escaping braces in the metadata itself
            escaped_metadata = db_metadata_string.replace("{", "{{").replace("}", "}}")
            prompt_with_metadata = sql_generation_prompt_template_base.replace("%%DB_METADATA%%", escaped_metadata)
            
            # DEBUG: Log the prompt just before formatting (keep for now)
            logger.debug(f"[Financial Tool] Prompt before final format:\n{prompt_with_metadata}")
            
            # Step 2: Format with the actual query using .format()
            sql_generation_prompt = prompt_with_metadata.format(query=query)

            logger.info(f"[Financial Tool] Running query: {query}")

            try:
                # 1. Generate SQL Query
                sql_query_raw = llm.invoke(sql_generation_prompt).content
                sql_query_cleaned = sql_query_raw.strip().removeprefix("```sql").removesuffix("```").strip()
                
                if not sql_query_cleaned or not sql_query_cleaned.upper().startswith(("SELECT", "WITH")):
                    logger.error(f"[Financial Tool] LLM did not return a valid SQL query. Raw response: {sql_query_raw}")
                    return {"status": "error", "result": "LLM failed to generate a valid SQL query."}

                logger.info(f"[Financial Tool] Generated SQL (cleaned): {sql_query_cleaned}")

                # 2. Execute SQL Query
                chain_result = db.run(sql_query_cleaned)
                logger.info(f"[Financial Tool] Raw execution result: {chain_result}")

                # 3. Prepare Result for Final Answer Generation
                processed_result = None
                if isinstance(chain_result, (list, tuple)) and not chain_result:
                    processed_result = None
                elif isinstance(chain_result, str) and not chain_result.strip():
                    processed_result = None
                else:
                    processed_result = chain_result

                sql_result_for_prompt = "The SQL query returned no matching data." if processed_result is None else str(processed_result)
                if processed_result is None:
                    logger.warning(f"[Financial Tool] Query returned no data. Original query: {query}")

                # 4. Generate Final Answer
                answer_prompt = f"""Based on the SQL query '{sql_query_cleaned}' and its result:

{sql_result_for_prompt}

Please provide a concise, natural language answer to the original user query: '{query}'. State clearly whether the requested data was found or not based on the provided SQL result."""
                final_answer = llm.invoke(answer_prompt).content
                logger.info(f"[Financial Tool] Final Answer: {final_answer}")
                
                return {"status": "success", "result": final_answer}

            except sqlite3.Error as db_err:
                error_msg = f"Database Error: {type(db_err).__name__} - {str(db_err)}"
                logger.error(f"[Financial Tool] Failed query '{query}'. {error_msg}") # Removed full traceback for brevity
                return {"status": "error", "result": error_msg}
            except Exception as e:
                error_msg = f"Execution Error: {type(e).__name__} - {str(e)}"
                logger.error(f"[Financial Tool] Failed unexpectedly for query '{query}'. {error_msg}") # Removed full traceback for brevity
                return {"status": "error", "result": error_msg}
        # --- End Wrapper ---

        tool_description = (
            "Useful for querying the FINANCIAL database for stock prices (daily data 2016-2020), historical quarterly financials (income/balance sheet, limited recent dates), "
            "dividends, stock splits, and company tickers. Input is a natural language question. "
            "Output is a JSON object with 'status' ('success', 'no_data', 'error') and 'result' (answer string or error details). "
            f"Key Tables: {', '.join(db.get_usable_table_names())}."
        )

        return Tool(
            name="financial_sql_query_tool", # Renamed tool
            description=tool_description,
            func=_run_financial_sql_wrapper
        )

    except Exception as e:
        logger.error(f"[Financial Tool] Failed setup: {e}\n{traceback.format_exc()}")
        def _error_tool_wrapper(query: str) -> Dict[str, str]:
             return {"status": "error", "result": f"Financial Tool Setup Error: {type(e).__name__}: {e}"}
        return Tool(
            name="financial_sql_query_tool_error",
            description=f"Error setting up Financial SQL query tool: {e}. Returns structured error.",
            func=_error_tool_wrapper
        )


# NEW Tool for CCR Reporting DB
def create_ccr_sql_tool(db_path: str, llm: BaseChatModel) -> Tool:
    """
    Creates a tool to query the CCR REPORTING database (counterparty risk).
    Includes database metadata in the prompt and returns structured output.
    Uses SQLDatabaseChain for direct query generation and execution.
    DB targeted: ccr_reporting.db
    """
    db_uri = f"sqlite:///{db_path}"
    logger.info(f"[CCR Tool] Connecting to SQL Database: {db_uri}")

    # --- Metadata Helper for CCR DB ---
    def _get_ccr_db_metadata(db_conn, db_object) -> str:
        """Queries CCR Reporting DB for metadata, reflecting the NEW schema (trades, securities, aggregated exposures)."""
        metadata_parts = []
        cursor = db_conn.cursor()
        try:
            # --- Basic Schema Info ---
            metadata_parts.append("CCR Reporting Database Schema Overview (NEW STRUCTURE):")
            usable_tables = db_object.get_usable_table_names()
            table_info = db_object.get_table_info(usable_tables) # Gets table structures (columns, types)
            metadata_parts.append(table_info)

            # --- Business Term Definitions (Updated) ---
            metadata_parts.append("\nKey Business Term Definitions:")
            metadata_parts.append("- **Exposure Columns (`report_daily_exposures`)**: These represent AGGREGATED risk values per counterparty for a given day.")
            metadata_parts.append("  - `net_mtm_exposure`: Net Mark-to-Market, aggregate value net of collateral.")
            metadata_parts.append("  - `gross_exposure`: Aggregate exposure before netting/collateral.")
            metadata_parts.append("  - `pfe_95_exposure`: Potential Future Exposure (95% conf), aggregate estimate.")
            metadata_parts.append("  - `settlement_risk_exposure`: Aggregate settlement risk.")
            metadata_parts.append("- **Collateral**: `collateral_value` in `report_daily_exposures` is aggregate collateral held. `collateral_agreement_id` in `report_counterparties` links to specific agreements (details not in DB).")
            metadata_parts.append("- **Risk Type**: Used in `report_limits` and `report_limit_utilization` (e.g., 'Net MTM', 'Settlement Risk', 'Gross Exposure'). Links conceptually to aggregate exposure columns.")
            metadata_parts.append("- **Asset Class**: Used in `report_limits` and `report_products` (e.g., 'FX', 'Equity', 'Rates', 'Securities Financing'). Limits are often set per asset class.")
            metadata_parts.append("- **Limit Breach Status**: In `report_limit_utilization`. 'OK', 'Advisory Breach', 'Hard Breach'.")

            # --- Key Table Hints (NEW SCHEMA) ---
            metadata_parts.append("\nKey CCR Tables & Usage Hints (NEW SCHEMA):")
            asset_classes = ['FX', 'Equity', 'Rates', 'Securities Financing'] # From query
            risk_types = ['Net MTM', 'Settlement Risk', 'Gross Exposure'] # From query
            sectors = ['Hedge Fund', 'Pension Fund', 'Bank', 'Sovereign Wealth Fund'] # From query
            breach_statuses = ['OK', 'Advisory Breach', 'Hard Breach'] # Expected values

            # Securities Table
            if 'securities' in usable_tables:
                 metadata_parts.append("- `securities`: Reference table for securities (e.g., stocks, bonds). PK: `security_ticker`.")

            # Products Table
            if 'report_products' in usable_tables:
                 metadata_parts.append(f"- `report_products`: Reference table for product classifications. PK: `product_id`. Links products to `asset_class`. Example `asset_class`: {', '.join(asset_classes)}.")

            # Counterparties Table
            if 'report_counterparties' in usable_tables:
                try:
                    cursor.execute("SELECT counterparty_id, short_name, counterparty_legal_name FROM report_counterparties ORDER BY counterparty_id")
                    all_counterparties = cursor.fetchall()
                    if all_counterparties:
                        cpty_list_str = ", ".join([f"({c[0]}, '{c[1]}', '{c[2]}')" for c in all_counterparties])
                        metadata_parts.append(f"- `report_counterparties`: Counterparty details (region, rating, sector, collateral agreement). PK: `counterparty_id`. Example `sector`: {', '.join(sectors)}. **Full list (ID, Short, Legal): [{cpty_list_str}]**")
                    else: metadata_parts.append("- `report_counterparties`: Counterparty details. PK: `counterparty_id`. (No counterparties found).")
                except Exception as e:
                     logger.warning(f"[CCR Tool] Could not fetch full counterparty list: {e}")
                     metadata_parts.append("- `report_counterparties`: Counterparty details. PK: `counterparty_id`. Error fetching full list.")

            # Trades Table
            if 'trades' in usable_tables:
                 metadata_parts.append("- `trades`: Core table linking counterparties, products, and optionally securities for each transaction. PK: `trade_id`. Contains `notional`, `currency`, `trade_date`.")

            # Limits Table
            if 'report_limits' in usable_tables:
                 metadata_parts.append(f"- `report_limits`: Defines risk limits (`limit_amount`) per counterparty (`counterparty_id`), `risk_type`, and `asset_class`. PK: `limit_id`. Example `risk_type`: {', '.join(risk_types)}. Example `asset_class`: {', '.join(asset_classes)}.")

            # Daily Exposures Table
            if 'report_daily_exposures' in usable_tables:
                try:
                    cursor.execute("SELECT MIN(report_date), MAX(report_date) FROM report_daily_exposures")
                    min_date, max_date = cursor.fetchone() or ('N/A', 'N/A')
                    metadata_parts.append(f"- `report_daily_exposures`: **AGGREGATED** daily risk snapshot per counterparty. PK: `daily_exposure_id`. Columns include `net_mtm_exposure`, `gross_exposure`, `pfe_95_exposure`, `settlement_risk_exposure`, `collateral_value`. Unique per `report_date`, `counterparty_id`. Data available from {min_date} to {max_date}. Use 'YYYY-MM-DD'.")
                except Exception as e:
                     logger.warning(f"[CCR Tool] Could not fetch date range for report_daily_exposures: {e}")
                     metadata_parts.append("- `report_daily_exposures`: **AGGREGATED** daily risk snapshot per counterparty. Use 'YYYY-MM-DD'.")

            # Utilization Table
            if 'report_limit_utilization' in usable_tables:
                try:
                    cursor.execute("SELECT MIN(report_date), MAX(report_date) FROM report_limit_utilization")
                    min_date, max_date = cursor.fetchone() or ('N/A', 'N/A')
                    metadata_parts.append(f"- `report_limit_utilization`: **AGGREGATED** daily limit utilization per counterparty and `risk_type`. PK: `limit_utilization_id`. Compares aggregate `exposure_amount` (from `report_daily_exposures`) against aggregate `limit_amount` (derived from `report_limits`), calculating `limit_utilization_percent` and `limit_breach_status`. Unique per `report_date`, `counterparty_id`, `risk_type`. Data available from {min_date} to {max_date}. Example `limit_breach_status`: {', '.join(breach_statuses)}.")
                except Exception as e:
                    logger.warning(f"[CCR Tool] Could not fetch date range for report_limit_utilization: {e}")
                    metadata_parts.append("- `report_limit_utilization`: **AGGREGATED** daily limit utilization per counterparty and risk type.")


            # --- Querying Tips (NEW SCHEMA) ---
            metadata_parts.append("\nCCR Querying Tips (NEW SCHEMA):")
            metadata_parts.append("- **Aggregate Exposures**: Query `report_daily_exposures` for overall risk figures (Net MTM, Gross, PFE, Settlement) for a counterparty on a specific `report_date`.")
            metadata_parts.append("- **Aggregate Utilization**: Query `report_limit_utilization` for overall utilization against `risk_type` limits (Net MTM, Settlement Risk, Gross Exposure).")
            metadata_parts.append("- **Limits by Asset Class**: Query `report_limits` to see specific limits set for a `counterparty_id`, `risk_type`, and `asset_class`.")
            metadata_parts.append("- **Trade Details**: Query `trades` for individual transaction details (notional, date, involved parties/products/securities).")
            metadata_parts.append("- **Joining**: Use `counterparty_id` to link most tables. Use `product_id` to link `trades` and `report_products`. Use `security_ticker` to link `trades` and `securities`.")
            metadata_parts.append("- **Dates**: Filter relevant tables by `report_date` or `trade_date` (YYYY-MM-DD). Current sample data centers around 2025-04-25.")

        except Exception as e:
            logger.error(f"[CCR Tool] Error generating DB metadata: {e}")
            metadata_parts.append("\nError: Could not dynamically generate full metadata hints for the new schema.")
        finally:
            cursor.close()

        return "\n".join(metadata_parts)
    # --- End Metadata Helper ---

    try:
        # Establish connections
        conn = sqlite3.connect(db_path)
        db = SQLDatabase.from_uri(db_uri)
        logger.info(f"[CCR Tool] SQLDatabase connection successful. Tables: {db.get_usable_table_names()}")

        db_metadata_string = _get_ccr_db_metadata(conn, db)
        conn.close()
        logger.info("[CCR Tool] Generated DB Metadata Hints for LLM.")

        sql_chain = SQLDatabaseChain.from_llm(llm, db, verbose=False, return_intermediate_steps=False)
        logger.info("[CCR Tool] SQLDatabaseChain created successfully.")

        # --- Tool Execution Wrapper ---
        def _run_ccr_sql_wrapper(query: str) -> Dict[str, str]:
            """Wraps the SQL chain for CCR data (NEW SCHEMA), adds metadata, handles errors, returns structured output."""
            # **MODIFIED Prompt for SQL Generation ONLY (NEW SCHEMA & EXAMPLES)**
            sql_generation_prompt_template = f"""
Given the database schema and hints below (reflecting the NEW schema with trades, aggregated exposures, etc.), generate a SQL query to answer the user's question.
**IMPORTANT INSTRUCTIONS**:
1.  **ONLY** return the raw SQL query. Do NOT include explanations, markdown formatting, or anything else.
2.  Refer to the **Full list of known counterparties** provided in the hints to map user query names/IDs correctly.
3.  If the user query refers to a counterparty ambiguously (e.g., 'Alpha') and multiple counterparties in the known list might match, generate SQL to retrieve data for **ALL potentially matching** counterparties (e.g., using `counterparty_id IN (...)` or `LIKE`).
4.  Pay attention to the **AGGREGATED** nature of `report_daily_exposures` and `report_limit_utilization`. Trade-level detail is in `trades`.
5.  Use the provided schema, hints, definitions, and examples below accurately.

Schema and Hints:
{db_metadata_string}

**Examples (NEW SCHEMA):**

Example 1 (Security Lookup):
User Query: What sector is MSFT in?
SQL Query: SELECT issuer_sector FROM securities WHERE security_ticker = 'MSFT'

Example 2 (Filtering Trades):
User Query: List trades for Alpha Hedge Fund.
SQL Query: SELECT trade_id, product_id, security_ticker, trade_date, notional, currency FROM trades WHERE counterparty_id = 101 ORDER BY trade_date

Example 3 (Joining Trades/Products):
User Query: Show FX trades for Gamma European Bank.
SQL Query: SELECT t.trade_id, p.product_name, t.trade_date, t.notional, t.currency FROM trades t JOIN report_products p ON t.product_id = p.product_id WHERE t.counterparty_id = 103 AND p.asset_class = 'FX'

Example 4 (Querying Aggregate Exposure):
User Query: What is the Net MTM exposure for Beta Pension Plan on 2025-04-25?
SQL Query: SELECT net_mtm_exposure, currency FROM report_daily_exposures WHERE counterparty_id = 102 AND report_date = '2025-04-25'

Example 5 (Querying Limits):
User Query: What is the Equity Net MTM limit for AlphaHF?
SQL Query: SELECT limit_amount, limit_currency FROM report_limits WHERE counterparty_id = 101 AND risk_type = 'Net MTM' AND asset_class = 'Equity'

Example 6 (Querying Aggregate Utilization):
User Query: Show Net MTM utilization status for GammaEB today.
SQL Query: SELECT limit_utilization_percent, limit_breach_status FROM report_limit_utilization WHERE counterparty_id = 103 AND risk_type = 'Net MTM' AND report_date = '2025-04-25'

Example 7 (Complex Join / Trade Detail):
User Query: What counterparties traded AAPL options?
SQL Query: SELECT DISTINCT rc.short_name FROM trades t JOIN report_counterparties rc ON t.counterparty_id = rc.counterparty_id JOIN report_products p ON t.product_id = p.product_id WHERE t.security_ticker = 'AAPL' AND p.product_category = 'Equity Option'

**(End of Examples)**

User Query: {query}

SQL Query: """
            sql_generation_prompt = sql_generation_prompt_template.format(query=query)
            
            logger.info(f"[CCR Tool] Running query: {query}")

            try:
                # Generate the SQL query first
                sql_query_raw = llm.invoke(sql_generation_prompt).content
                
                # Strip potential minor leading/trailing whitespace or artifacts (like ```sql)
                # Although the prompt requests ONLY SQL, add minor cleanup just in case.
                sql_query_cleaned = sql_query_raw.strip().removeprefix("```sql").removesuffix("```").strip()
                
                # Check if the cleaned query is empty or looks like not-SQL (basic check)
                if not sql_query_cleaned or not sql_query_cleaned.upper().startswith("SELECT"):
                    logger.error(f"[CCR Tool] LLM did not return a valid SQL query. Raw response: {sql_query_raw}")
                    return {"status": "error", "result": "LLM failed to generate a valid SQL query."}

                logger.info(f"[CCR Tool] Generated SQL (cleaned): {sql_query_cleaned}")

                # Now execute the cleaned SQL query using the database connection
                chain_result = db.run(sql_query_cleaned)

                logger.info(f"[CCR Tool] Raw execution result: {chain_result}")

                # Check for no data / empty result and prepare context for final LLM
                processed_result = None
                if isinstance(chain_result, (list, tuple)) and not chain_result:
                    processed_result = None # Explicitly None for empty list/tuple
                elif isinstance(chain_result, str) and not chain_result.strip():
                    processed_result = None # Explicitly None for empty string
                else:
                    processed_result = chain_result # Keep the result if it seems to contain data

                # Prepare the input string for the final answer LLM
                if processed_result is None:
                    sql_result_for_prompt = "The SQL query returned no matching data."
                    logger.warning(f"[CCR Tool] Query returned no data. Original query: {query}")
                else:
                    sql_result_for_prompt = str(processed_result) # Use string representation of the result

                # Always call the final LLM to formulate the response based on the SQL outcome
                answer_prompt = f"""Based on the SQL query '{sql_query_cleaned}' and its result:

{sql_result_for_prompt}

Please provide a concise, natural language answer to the original user query: '{query}'. State clearly whether the requested data was found or not based on the provided SQL result.""" # Prompt emphasizes clarity on data presence
                final_answer = llm.invoke(answer_prompt).content
                logger.info(f"[CCR Tool] Final Answer: {final_answer}")

                # Return success, as the process completed; the answer conveys data presence/absence
                return {"status": "success", "result": final_answer}

            except sqlite3.Error as db_err:
                error_msg = f"Database Error: {type(db_err).__name__} - {str(db_err)}"
                logger.error(f"[CCR Tool] Failed query '{query}'. {error_msg}\n{traceback.format_exc()}")
                return {"status": "error", "result": error_msg}
            except Exception as e:
                error_msg = f"Execution Error: {type(e).__name__} - {str(e)}"
                logger.error(f"[CCR Tool] Failed unexpectedly for query '{query}'. {error_msg}\n{traceback.format_exc()}")
                return {"status": "error", "result": error_msg}
        # --- End Wrapper ---

        tool_description = (
            "Useful for querying the Counterparty Credit Risk (CCR) REPORTING database for daily limit utilization, "
            "breach status, calculated exposures (e.g., Net MTM, Gross Exposure, PFE), and current limits. "
            "Input is a natural language question about counterparties (use counterparty_id if known) and report dates (YYYY-MM-DD). "
            "Output is a JSON object with 'status' ('success', 'no_data', 'error') and 'result' (answer string or error details). "
            f"Key Tables: {', '.join(db.get_usable_table_names())}."
        )

        return Tool(
            name="ccr_sql_query_tool", # New tool name
            description=tool_description,
            func=_run_ccr_sql_wrapper
        )

    except Exception as e:
        logger.error(f"[CCR Tool] Failed setup: {e}\n{traceback.format_exc()}")
        def _error_tool_wrapper(query: str) -> Dict[str, str]:
             return {"status": "error", "result": f"CCR Tool Setup Error: {type(e).__name__}: {e}"}
        return Tool(
            name="ccr_sql_query_tool_error",
            description=f"Error setting up CCR SQL query tool: {e}. Returns structured error.",
            func=_error_tool_wrapper
        )

def validate_department_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate department tool response."""
    errors = []
    required_fields = ["thought", "answer", "category", "confidence"]
    
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")
    
    if "confidence" in response and not isinstance(response["confidence"], (int, float)):
        errors.append("Confidence must be a number")
    
    return len(errors) == 0, errors

def validate_category_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate category tool response (simplified JSON)."""
    errors = []
    # Require 'thought' and 'answer' field now
    required_fields = ["thought", "answer"]
    
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")
    
    # Check for internal error reported by the tool
    if "error" in response and response["error"]:
         logger.warning(f"Category tool reported an internal error: {response['error']}")
         # Still counts as a valid *structure* for the validator
         pass

    return len(errors) == 0, errors

def validate_metadata_lookup_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate metadata lookup tool response."""
    errors = []
    # Check for the new required keys
    required_fields = ["category_name", "transcript_names"] # Changed to plural
    # Optional error field

    if not isinstance(response, dict):
        return False, ["Response is not a dictionary."]

    # Validate presence of required fields
    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")

    # Validate type of category_name (string or None)
    if "category_name" in response and not (isinstance(response["category_name"], str) or response["category_name"] is None):
        errors.append(f"Field 'category_name' must be a string or None, but got {type(response['category_name'])}.")

    # Validate type of transcript_names (must be a list of strings)
    if "transcript_names" in response:
        if not isinstance(response["transcript_names"], list):
            errors.append(f"Field 'transcript_names' must be a list, but got {type(response['transcript_names'])}.")
        else:
            # Check each item in the list is a string
            for item in response["transcript_names"]:
                if not isinstance(item, str):
                    errors.append(f"Items in 'transcript_names' list must be strings, but found {type(item)}.")
                    break # Only report first type error in list

    # Check for internal error reported by the tool itself
    if response.get("error"):
         logger.warning(f"Metadata lookup tool reported an internal error: {response['error']}")
         pass # Still counts as a valid *structure* for the validator

    return len(errors) == 0, errors

def validate_transcript_analysis_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate transcript analysis tool response."""
    errors = []
    required_fields = ["answer"] # Expecting at least an answer field

    for field in required_fields:
        if field not in response:
            errors.append(f"Missing required field: {field}")

    # Check for internal error reported by the tool itself
    if "error" in response and response["error"]:
         logger.warning(f"Transcript Analysis tool reported an internal error: {response['error']}")
         # Still counts as a valid *structure* for the validator, the agent needs to see the error message
         pass

    return len(errors) == 0, errors 

# NEW: Function to create the Transcript Search/Summary Agent as a Tool
def create_transcript_agent_tool(llm: BaseChatModel, api_key: Optional[str] = None) -> Tool:
    """
    Creates a Tool that encapsulates a dedicated agent for searching and summarizing transcripts.
    This agent uses category, metadata, and transcript analysis tools internally.
    """
    logger.info("[Transcript Agent Tool] Initializing internal tools...")
    try:
        # 1. Initialize internal tools required by the transcript agent
        category_tool_func = create_category_tool()
        metadata_lookup_tool_func = create_metadata_lookup_tool()
        transcript_analysis_tool_func = create_transcript_analysis_tool(api_key)

        # Convert internal functions to LangChain Tools with appropriate descriptions *for this agent*
        internal_tools = [
            Tool(
                name="category_tool",
                func=category_tool_func,
                description="Identifies relevant document categories (like earnings calls) for a specific company/ticker based on user query context. Input is 'ticker, query'."
            ),
             Tool(
                name="metadata_lookup_tool",
                func=metadata_lookup_tool_func,
                description="Finds relevant document transcript filenames based on company ticker, category, and date/quarter context from the query. Input is 'ticker, category, date/quarter context'."
            ),
             Tool(
                name="transcript_analysis_tool",
                func=transcript_analysis_tool_func,
                description="Analyzes the content of specific document transcripts (provided by filename) to answer a user query. Input MUST be in the format 'query, document_name=<filename>'. Provide only ONE document_name per call."
            )
        ]
        logger.info(f"[Transcript Agent Tool] Internal tools created: {[t.name for t in internal_tools]}")

        # 2. Define the prompt for the Transcript Agent (with context + formatting guidance + analyst persona)
        TRANSCRIPT_AGENT_PROMPT = """
You are an expert **Equity Research Analyst** specializing in analyzing company earnings call transcripts.
Your primary goal is to answer the user's query by producing a **concise analytical summary/report** based *only* on the information found within the relevant documents (primarily earnings call transcripts).
(Note: Your focus is deep document analysis; you do not perform high-level query classification or use external data.)

You have access to the following tools to help you find and analyze relevant documents:

{tools}

Use the following format:

Question: the input question you must answer
Thought: As an analyst, I need to break down the question. First, identify the company/timeframe. Then, find the relevant transcript(s) using the tools. Finally, analyze the transcript(s) content to address the specific aspects of the query.
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action. **CRITICAL: Ensure the input strictly matches the format specified in the tool's description.** Examples:
    - For 'category_tool': `ticker, query` (e.g., `AAPL, summarize performance`)
    - For 'metadata_lookup_tool': `ticker, category, date/quarter context` (e.g., `MSFT, earnings call, Q4 2019`)
    - For 'transcript_analysis_tool': `query, document_name=<filename>` (e.g., `What was revenue growth?, document_name=2018-Jan-30-MSFT.txt`) --- **Provide only ONE filename per call.**
Observation: the result of the action (e.g., list of filenames, summary of one transcript excerpt)
... (this Thought/Action/Action Input/Observation can repeat N times as you gather information from different tools/transcripts)
Thought: I have gathered and analyzed the necessary information from the transcript(s) using the tools. Now I will synthesize these findings into a concise analyst report answering the original question.
Final Answer: **[Analyst Report Format]**
Synthesize the key findings from the 'Observation' steps above into a clear, concise report that directly answers the user's original 'Question'. Structure the report logically (e.g., by quarter, by theme). Focus on the aspects relevant to an equity analyst (e.g., financial performance, guidance, strategy shifts, management commentary). Cite transcript filenames where appropriate. If the documents do not contain sufficient information to answer fully, state that clearly.

Begin!

Question: {input}
Thought:{agent_scratchpad}
"""

        prompt = PromptTemplate.from_template(TRANSCRIPT_AGENT_PROMPT)
        logger.debug("[Transcript Agent Tool] Prompt template created.")

        # 3. Create the internal Agent specific for transcripts
        # Using ReAct agent again for this sub-agent
        transcript_react_agent = create_react_agent(llm, internal_tools, prompt)
        logger.debug("[Transcript Agent Tool] Internal ReAct agent created.")

        # 4. Create the AgentExecutor for the internal agent
        # Note: Add error handling? Maybe use the main agent's handler? For now, default.
        transcript_agent_executor = AgentExecutor(
            agent=transcript_react_agent,
            tools=internal_tools,
            verbose=True, # Make sub-agent verbose for debugging
            max_iterations=10, # Allow more steps for document search/analysis
            handle_parsing_errors="Check your output and make sure it conforms to the expected format!", # Simple handler
        )
        logger.info("[Transcript Agent Tool] Internal AgentExecutor created.")

        # Wrapper function to adapt input for invoke
        def _transcript_agent_wrapper(query_string: str) -> str:
            try:
                # Invoke the sub-agent executor with the input in the expected dict format
                result = transcript_agent_executor.invoke({"input": query_string})
                # Extract the final output string
                return result.get("output", "Transcript agent did not return a final answer.")
            except Exception as sub_agent_error:
                logger.error(f"[Transcript Agent Tool] Error during sub-agent execution: {sub_agent_error}", exc_info=True)
                return f"Error executing transcript analysis: {type(sub_agent_error).__name__}: {sub_agent_error}"

        # 5. Wrap the AgentExecutor in a Tool for the Master Agent
        transcript_agent_tool = Tool(
            name="transcript_search_summary_tool",
            func=_transcript_agent_wrapper, # Use the wrapper function
            description=("Answers questions about company performance, statements, strategies, or specific events by searching and analyzing historical earnings call transcripts and related documents. Use this for queries requiring textual analysis of documents, NOT for direct structured financial data (use financial_sql_query_tool) or counterparty risk data (use ccr_sql_query_tool). Input should be the original user query.")
        )
        logger.info("[Transcript Agent Tool] Tool object created successfully.")
        return transcript_agent_tool

    except Exception as e:
        error_message_for_tool = f"Error setting up Transcript Agent Tool: {type(e).__name__}: {e}" # Capture error message here
        logger.error(f"[Transcript Agent Tool] Failed setup: {e}\n{traceback.format_exc()}")
        # Return a dummy tool that reports the error
        def _error_tool_wrapper(query: str) -> str: # Return string for compatibility
             # Use the captured error message
             return error_message_for_tool
        return Tool(
            name="transcript_search_summary_tool_error",
            description=f"Error setting up Transcript Agent Tool: {e}. Returns error message.", # Keep original description using e
            func=_error_tool_wrapper
        ) 