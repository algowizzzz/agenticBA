# Wrapper for earnings call transcript search/summary 
import logging
import os
from typing import Dict, Any, Optional, List
import datetime

from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

# Import the actual tool implementations
from langchain_tools.tool1_department import department_summary_tool
from langchain_tools.tool2_category import category_summary_tool
from langchain_tools.doc_level_search_tool import get_doc_level_search_tool

# Replace single document analysis tool with our two new tools
from langchain_tools.summaries_analysis_tool import get_document_summaries_analysis_tool
from langchain_tools.full_document_analysis_tool import get_full_document_analysis_tool

# Add the new category search tool
from langchain_tools.category_search_tool import get_category_search_tool

logger = logging.getLogger(__name__)

# Define department summary for context awareness
DEPARTMENT_SUMMARY = """
This document base provides transcripts of earnings calls for major technology companies including Apple (AAPL), 
Microsoft (MSFT), Amazon (AMZN), Google (GOOGL), NVIDIA (NVDA), and other tech firms. The data spans from 
approximately 2016 to 2020. 

The information is organized in a hierarchical structure of summaries:
1. Department level: High-level overview of the tech sector and available data
2. Category level: Company-specific summaries (by ticker symbol)
3. Document level: Individual earnings call transcripts

Each level provides increasing detail, allowing for efficient investigation from broad context to specific statements.
"""

# Implement proper wrapper functions that use the actual tools
def create_department_tool_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for department tool. Provides high-level context about the database.
    Input is just the natural language query.
    Output is a structured overview of data scope and available companies.
    """
    # We can either use a static summary or fetch from database
    # For now, using the static DEPARTMENT_SUMMARY for consistency
    return {
        "result": DEPARTMENT_SUMMARY,
        "available_companies": ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "INTC", "AMD", "CSCO"],
        "data_timespan": "2016-2020",
        "workflow_steps": [
            "Start with department overview to understand data scope",
            "Identify relevant companies/categories",
            "Search for specific documents",
            "Analyze document summaries",
            "Deep dive into full documents when needed"
        ]
    }

def create_category_tool_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for category tool. Input format: '<query>, category: <category_id>'
    Example: 'What are the business segments?, category: 8ba26d53'
    """
    # Try to parse the input
    parts = input_str.split('category:')
    if len(parts) != 2:
        return {
            "error": f"Invalid input format: {input_str}. Expected format: '<query>, category: <category_id>'"
        }

    query = parts[0].strip().strip(",")
    category_id = parts[1].strip()

    # Call the actual tool with API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    result = category_summary_tool(query, category_id, api_key)
    return result


def create_doc_level_search_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for document-level search tool. Accepts a natural language query.
    Example: 'Find earnings calls discussing NVIDIA AI strategy in 2020'
    """
    # Call the document-level search tool
    doc_level_search_tool = get_doc_level_search_tool()
    result = doc_level_search_tool(input_str)

    # Return the results with proper formatting
    return {"result": result}


# New wrapper for document summaries analysis tool
def create_document_summaries_analysis_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for document summaries analysis tool. Analyzes multiple document summaries at once.
    Input format: '<query>, documents: <document_id1>,<document_id2>,<document_id3>,<document_id4>,<document_id5>'
    Example: 'Compare revenue growth, documents: ae5e9f7b-f64a,7e538606-f18b,e64e6c04-9a86,docid4,docid5'
    """
    # Try to parse the input
    parts = input_str.split("documents:")
    if len(parts) != 2:
        return {
            "error": f"Invalid input format: {input_str}. Expected format: '<query>, documents: <document_id1>,<document_id2>,...'"
        }

    query = parts[0].strip().strip(",")
    document_ids_str = parts[1].strip()
    document_ids = [doc_id.strip() for doc_id in document_ids_str.split(",")]

    # Filter out empty document IDs
    document_ids = [doc_id for doc_id in document_ids if doc_id]

    # Limit to 5 documents to prevent context window issues
    document_ids = document_ids[:5]

    # Call the actual summary analysis tool
    summary_analysis_tool = get_document_summaries_analysis_tool()
    result = summary_analysis_tool(query, document_ids)
    return result


# New wrapper for full document analysis tool
def create_full_document_analysis_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for full document analysis tool. Analyzes a full document, with optional chunking.
    Input format: '<query>, document: <document_id>, chunk: <chunk_number>'
    Example: 'Find detailed revenue breakdown, document: ae5e9f7b-f64a'
    Example with chunk: 'Continue reading document, document: 7e538606-f18b, chunk: 2'
    """
    # Try to parse the input
    parts = input_str.split("document:")
    if len(parts) != 2:
        return {
            "error": f"Invalid input format: {input_str}. Expected format: '<query>, document: <document_id>, chunk: <chunk_number>'"
        }

    query = parts[0].strip().strip(",")
    remaining = parts[1].strip()

    # Check for chunk parameter
    chunk_index = None
    if "chunk:" in remaining:
        doc_parts = remaining.split("chunk:")
        document_id = doc_parts[0].strip().strip(",")
        try:
            chunk_index = int(doc_parts[1].strip())
        except ValueError:
            return {"error": f"Invalid chunk number format in: {input_str}"}
    else:
        document_id = remaining.strip()

    # Call the actual full document analysis tool
    full_document_tool = get_full_document_analysis_tool()
    result = full_document_tool(query, document_id, chunk_index)
    return result


# Add wrapper for the new CategorySearch tool
def create_category_search_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for category search tool. Maps a user query to relevant tickers.
    Example: 'Which companies discussed AI strategies in 2019?'
    """
    # Call the actual search tool
    category_search_tool = get_category_search_tool()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    result = category_search_tool(input_str, api_key)
    
    return result


# Create the Earnings Call Tool
def create_earnings_call_toolset(llm: BaseChatModel) -> List[Tool]:
    """Creates the tools for earnings call analysis"""

    tools = [
        Tool(
            name="DepartmentOverview",
            func=create_department_tool_wrapper,
            description="""
            Use this tool FIRST to understand the scope of the database and available data.
            This provides high-level context about what companies are covered, time period of data,
            and the structure of information available.
            
            Input is simply your natural language query.
            
            Example inputs:
            - "What data is available in this database?"
            - "Give me an overview of the database"
            - "What companies and time periods are covered?"
            """,
        ),
        Tool(
            name="CategorySearch",
            func=create_category_search_wrapper,
            description="""
            Use this tool to identify which companies/tickers are relevant to a query.
            This should be your second step after getting the department overview.
            Input is simply the natural language query about what companies to analyze.
            
            Example inputs:
            - "Which companies had the strongest AI adoption in 2018?"
            - "Compare Amazon and Apple's cloud strategies"
            - "Find semiconductor manufacturers discussing supply chain issues"
            """,
        ),
        Tool(
            name="DocumentLevelSearch",
            func=create_doc_level_search_wrapper,
            description="""
            Use this tool to search across all earnings call transcripts without filtering.
            Input should be a detailed natural language query describing what you're looking for.
            This tool performs semantic search to find the most relevant documents based on meaning.
            
            Example inputs:
            - "Find earnings calls discussing NVIDIA AI chip strategy"
            - "Which companies mentioned supply chain issues in Q1 2020?"
            - "Find earnings calls where Apple discusses iPhone revenue growth"
            - "Which semiconductor companies discussed manufacturing challenges in 2019?"
            """,
        ),
        Tool(
            name="CategorySummary",
            func=create_category_tool_wrapper,
            description="""
            Use this tool to get summaries based on a specific category/company.
            Input format: '<query>, category: <category_id>'
            
            Example inputs:
            - "Summarize the business segments, category: AAPL"
            - "What were the key growth drivers?, category: MSFT"
            - "Explain their AI strategy, category: NVDA"
            """,
        ),
        Tool(
            name="DocumentSummariesAnalysis",
            func=create_document_summaries_analysis_wrapper,
            description="""
            Use this tool to analyze multiple document summaries at once (up to 5).
            This tool provides a comprehensive answer based on the information from all provided summaries.
            Input format: '<query>, documents: <document_id1>,<document_id2>,<document_id3>,<document_id4>,<document_id5>'
            
            Example inputs:
            - "Compare revenue growth, documents: ae5e9f7b-f64a,7e538606-f18b,e64e6c04-9a86,docid4,docid5"
            - "Analyze AI strategy, documents: 123e4567-e89b,docid2,docid3,docid4,docid5"
            - "Summarize key financial metrics, documents: ae5e9f7b-f64a,7e538606-f18b,docid3,docid4,docid5"
            """,
        ),
        Tool(
            name="FullDocumentAnalysis",
            func=create_full_document_analysis_wrapper,
            description="""
            Use this tool to analyze the full text of a specific document when summaries aren't sufficient.
            For large documents, it supports reading in chunks (pages).
            Input format: '<query>, document: <document_id>, chunk: <chunk_number>' (chunk is optional)
            
            Example inputs:
            - "Find detailed revenue breakdown, document: ae5e9f7b-f64a"
            - "Continue reading document, document: 7e538606-f18b, chunk: 2"
            """,
        ),
    ]

    return tools


# Define the prompt for the Transcript Agent with updated workflow
TRANSCRIPT_AGENT_PROMPT_TEMPLATE = """You are an expert **Equity Research Analyst** specializing in analyzing company earnings calls and related documents.
Your primary goal is to answer the user's query by analyzing information found within relevant documents.
**(Note: Transcript data covers roughly 2016 to 2020).**

IMPORTANT: If the user query is phrased as a command (e.g., "amzn q1 2017 transcript summary"), treat it as an implicit question (e.g., "What is the summary of Amazon's Q1 2017 earnings call transcript?").

You have access to the following tools:

{tools}

Use the following format EXACTLY without ANY deviation:

Question: the input question you must answer
Thought: As an analyst, I need to break down the question and gather information step-by-step using a holistic, multi-level approach.

**STEP-BY-STEP WORKFLOW:**

1. **GET DATABASE OVERVIEW:**
   - ALWAYS start by using the `DepartmentOverview` tool to understand the scope of available data.
   - This will give you critical context about what companies are covered, the time period of data, and how information is structured.
   - Use this overview to guide your subsequent search strategy.

2. **IDENTIFY RELEVANT COMPANIES:**
   - Use the `CategorySearch` tool to identify which company categories (tickers like AAPL, MSFT, NVDA) are relevant to the question.
   - This tool will return tickers along with an explanation of why they're relevant.

3. **GET CATEGORY-LEVEL SUMMARIES:**
   - For each identified ticker, call the `CategorySummary` tool to get a high-level summary of the company.
   - The Action Input MUST be in the format: '<Brief query about category>, category: <CATEGORY_ID>' (e.g., 'Summarize recent growth, category: AAPL').
   - Review the results from all `CategorySummary` calls to understand the broad context.

4. **SEARCH FOR RELEVANT DOCUMENTS:**
   - Use the `DocumentLevelSearch` tool with specific parts of the original question to find precise document IDs.
   - Be as specific as possible in your search to find the most relevant documents.
   - If the first search doesn't yield ideal results, try refining your search terms and search again.

5. **ANALYZE DOCUMENT SUMMARIES:**
   - Use the `DocumentSummariesAnalysis` tool to analyze up to 5 document summaries at once.
   - The Action Input MUST be in the format: '<query>, documents: <document_id1>,<document_id2>,<document_id3>,<document_id4>,<document_id5>' using exact document IDs from search results.
   - Analyze the results to determine if they answer the question sufficiently.
   - If you need to analyze more than 5 documents, run this tool multiple times with different sets of documents.

6. **DEEP DIVE INTO FULL DOCUMENTS IF NEEDED:**
   - ONLY IF NECESSARY (if summaries don't provide enough detail), use the `FullDocumentAnalysis` tool on the most relevant documents.
   - The Action Input MUST be in the format: '<query>, document: <document_id>'.
   - For large documents that return partial information, continue reading by calling the tool again with 'chunk: <next_chunk_number>' added to the input.

7. **SYNTHESIZE COMPREHENSIVE ANALYSIS:**
   - After gathering sufficient information across multiple tiers (department, category, document summaries, full documents), synthesize all findings.
   - Focus on directly answering the core human question behind the query.

**IMPORTANT GUIDANCE:**
- Always follow the workflow in this order: DepartmentOverview → CategorySearch → CategorySummary → DocumentLevelSearch → DocumentSummariesAnalysis → FullDocumentAnalysis (if needed).
- Track your progress and avoid repeating the same searches or analyses.
- If your first search doesn't yield ideal results, try refining your search terms and search again.
- Be cognizant of timeframes mentioned in the query (like specific quarters or years).
- Proceed to full document analysis ONLY if document summaries don't provide sufficient detail.
- Always verify document relevance by checking metadata (document_id, quarter, year).
- Always work with what information is available. If some data points are missing, analyze what you have without complaining about gaps.
- You MUST provide a Final Answer at the end of your analysis, even if it's based on limited information.

IMPORTANT: When calling tools, use EXACTLY this format:

Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action

For example:
Action: DepartmentOverview
Action Input: What data is available in this database?

Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times as you gather information)
Thought: I have gathered sufficient information. Now I will synthesize these findings.
Final Answer: Your final answer here in plain text.

Begin!

Question: {input}
Thought:{agent_scratchpad}
"""
TRANSCRIPT_AGENT_PROMPT = PromptTemplate.from_template(TRANSCRIPT_AGENT_PROMPT_TEMPLATE)


def select_appropriate_model(task_complexity: str = "standard") -> str:
    """
    Select the appropriate model based on task complexity.
    Args:
        task_complexity: 'simple', 'standard', or 'complex'
    Returns:
        str: Model name to use
    """
    # Model selection based on task complexity
    if task_complexity == "simple":
        return "claude-3-haiku-20240307"  # Fastest, most cost-efficient
    elif task_complexity == "complex":
        return "claude-3-opus-20240229"  # Most capable for complex tasks
    else:
        return "claude-3-5-sonnet-20240620"  # Good balance of capability and efficiency


def run_transcript_agent(
    query: str,
    llm: BaseChatModel = None,
    api_key: Optional[str] = None,
    task_complexity: str = "standard",
    verbose: bool = True,
) -> str:
    """
    Runs the specialized transcript analysis agent.
    Handles initialization of internal tools and execution.

    Args:
        query: The user's query about earnings calls
        llm: Optional pre-configured LLM (will create one if not provided)
        api_key: Optional API key (will use env var if not provided)
        task_complexity: Complexity level ('simple', 'standard', 'complex')
        verbose: Whether to show verbose logging

    Returns:
        str: The final analysis as a string, or an error message string.
    """
    logger.info(f"[Transcript Agent Tool] Initializing for query: {query[:100]}...")

    # Start tracking workflow state
    workflow_state = {
        "query": query,
        "start_time": datetime.datetime.now(),
        "department_tools_used": 0,  # Added new counter
        "category_tools_used": 0,
        "search_tools_used": 0,
        "summary_tools_used": 0,
        "full_doc_tools_used": 0,
        "companies_identified": [],
        "documents_analyzed": [],
        "error": None,
        "completed": False,
    }

    try:
        # Create a Claude LLM if none is provided
        if llm is None:
            from langchain_anthropic import ChatAnthropic

            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("No Anthropic API key found for transcript agent")
                workflow_state["error"] = "API key missing"
                return format_agent_response(
                    error="Anthropic API key is required for transcript analysis",
                    workflow_state=workflow_state,
                )

            # Select appropriate model based on task complexity
            model = select_appropriate_model(task_complexity)
            logger.info(f"[Transcript Agent Tool] Using model: {model}")

            llm = ChatAnthropic(model=model, temperature=0, anthropic_api_key=api_key)

        # --- Instantiate Internal Tools with actual implementations ---
        document_level_search_tool_instance = create_doc_level_search_wrapper

        # Create wrapped tool versions that update workflow state
        def department_tool_with_tracking(input_str: str) -> Dict[str, Any]:
            workflow_state["department_tools_used"] += 1
            result = create_department_tool_wrapper(input_str)
            return result
            
        def category_tool_with_tracking(input_str: str) -> Dict[str, Any]:
            workflow_state["category_tools_used"] += 1
            
            # Extract category/company from input
            if "category:" in input_str:
                parts = input_str.split("category:")
                if len(parts) == 2:
                    category = parts[1].strip()
                    # Add to companies identified if not already there
                    if category not in workflow_state["companies_identified"]:
                        workflow_state["companies_identified"].append(category)
            
            result = create_category_tool_wrapper(input_str)
            return result

        def search_tool_with_tracking(input_str: str) -> Dict[str, Any]:
            workflow_state["search_tools_used"] += 1
            result = document_level_search_tool_instance(input_str)
            
            # Extract company tickers from search results
            if "identified_documents" in result and isinstance(result["identified_documents"], list):
                for doc in result["identified_documents"]:
                    if "ticker" in doc and doc["ticker"]:
                        ticker = doc["ticker"]
                        if ticker not in workflow_state["companies_identified"]:
                            workflow_state["companies_identified"].append(ticker)
            
            return result

        def summaries_tool_with_tracking(input_str: str) -> Dict[str, Any]:
            workflow_state["summary_tools_used"] += 1
            result = create_document_summaries_analysis_wrapper(input_str)
            
            # Extract document IDs analyzed
            if "documents_analyzed" in result:
                for doc_id in result.get("documents_analyzed", []):
                    if doc_id not in workflow_state["documents_analyzed"]:
                        workflow_state["documents_analyzed"].append(doc_id)
            
            return result

        def full_doc_tool_with_tracking(input_str: str) -> Dict[str, Any]:
            workflow_state["full_doc_tools_used"] += 1
            result = create_full_document_analysis_wrapper(input_str)
            
            # Add document ID to analyzed list
            if "document_id" in result:
                doc_id = result.get("document_id")
                if doc_id not in workflow_state["documents_analyzed"]:
                    workflow_state["documents_analyzed"].append(doc_id)
            
            return result

        # Create the internal tools using our updated tools
        internal_tools = [
            Tool(
                name="department_overview_tool",
                func=department_tool_with_tracking,
                description="Provides a high-level overview of the database structure, available companies, and time periods covered. Use this tool first to understand the scope and limitations of the data. Input is just your natural language query.",
            ),
            Tool(
                name="category_tool",
                func=category_tool_with_tracking,
                description="Analyzes summaries for a specific category (company ticker) to answer high-level queries or determine if deeper analysis is needed. Input format: 'query, category: <CATEGORY_ID>' (e.g., 'Summarize performance, category: AAPL')",
            ),
            Tool(
                name="document_level_search_tool",
                func=search_tool_with_tracking,
                description="Finds relevant documents using pure semantic search without metadata filtering. This tool searches across all documents and uses document-level semantic understanding to find the most relevant matches for your query. Input is just the natural language query. Output is a structured JSON with 'identified_documents', each containing document ID, name, and company ticker.",
            ),
            Tool(
                name="document_summaries_analysis_tool",
                func=summaries_tool_with_tracking,
                description="Analyzes multiple document summaries (up to 3) at once to answer a query. Input MUST be in the format: '<query>, documents: <document_id1>,<document_id2>,<document_id3>'. Use this as your primary document analysis tool to get a comprehensive answer based on multiple documents.",
            ),
            Tool(
                name="full_document_analysis_tool",
                func=full_doc_tool_with_tracking,
                description="Analyzes the full text of a specific document when summaries aren't sufficient. Supports chunking for large documents. Input MUST be in the format: '<query>, document: <document_id>, chunk: <chunk_number>' (chunk is optional). Use this only when summaries don't provide enough detail.",
            ),
        ]
        logger.info(
            f"[Transcript Agent Tool] Internal tools created: {[t.name for t in internal_tools]}"
        )

        # --- Create React Agent and Executor ---
        react_agent = create_react_agent(llm, internal_tools, TRANSCRIPT_AGENT_PROMPT)
        agent_executor = AgentExecutor(
            agent=react_agent,
            tools=internal_tools,
            handle_parsing_errors=True,  # Changed to True to be more forgiving of parsing errors
            verbose=verbose,  # Good for debugging this sub-agent
            max_iterations=15,  # Prevent infinite loops
            early_stopping_method="force",  # Changed from "generate" to "force" which is more widely supported
        )

        # --- Execute the Sub-Agent ---
        logger.info("[Transcript Agent Tool] Executing sub-agent...")
        try:
            result = agent_executor.invoke({"input": query})
            output = result.get(
                "output", "Transcript agent finished but provided no output."
            )
            logger.info(
                f"[Transcript Agent Tool] Execution finished. Output: {output[:200]}..."
            )

            # Update workflow state
            workflow_state["completed"] = True
            workflow_state["end_time"] = datetime.datetime.now()
            workflow_state["execution_time"] = (
                workflow_state["end_time"] - workflow_state["start_time"]
            ).total_seconds()

            return format_agent_response(content=output, workflow_state=workflow_state)
        except TypeError as e:
            # Handle the specific NoneType and int calculation error in the Anthropic library
            if (
                "NoneType" in str(e)
                and "int" in str(e)
                and "_create_usage_metadata" in str(e)
            ):
                logger.warning(
                    f"[Transcript Agent Tool] Handled known token usage calculation error: {e}"
                )
                # Update workflow state
                workflow_state["error"] = f"Token usage calculation error: {str(e)}"
                workflow_state["end_time"] = datetime.datetime.now()
                workflow_state["execution_time"] = (
                    workflow_state["end_time"] - workflow_state["start_time"]
                ).total_seconds()

                # Return a helpful message about the error without crashing
                return format_agent_response(
                    error="The transcript analysis encountered a known issue with token usage calculation in the Anthropic library. Unfortunately, this prevented successful completion of your query. This is a technical issue and not related to the availability of data.",
                    workflow_state=workflow_state,
                )
            else:
                # Re-raise other TypeError exceptions
                raise

    except Exception as e:
        logger.error(
            f"[Transcript Agent Tool] Error during execution: {e}", exc_info=True
        )
        # Update workflow state
        workflow_state["error"] = f"{type(e).__name__}: {str(e)}"
        workflow_state["end_time"] = datetime.datetime.now()
        workflow_state["execution_time"] = (
            workflow_state["end_time"] - workflow_state["start_time"]
        ).total_seconds()

        return format_agent_response(
            error=f"Transcript analysis failed. Details: {type(e).__name__}: {e}",
            workflow_state=workflow_state,
        )


def format_agent_response(
    content: str = None, error: str = None, workflow_state: Dict = None
) -> str:
    """
    Format the agent response in a standardized way.

    Args:
        content: The content of the response (if successful)
        error: Error message (if any)
        workflow_state: Current workflow state for debugging

    Returns:
        str: Formatted response
    """
    if error:
        return error

    # For successful responses, add prompt monitor info if workflow_state is available
    if workflow_state:
        # Extract relevant information about the process
        companies = workflow_state.get("companies_identified", [])
        companies_str = ", ".join(companies) if companies else "relevant companies"
        docs_analyzed = len(workflow_state.get("documents_analyzed", []))
        exec_time = workflow_state.get("execution_time", 0)
        
        # Create a narrative Prompt Monitor section
        monitor_info = "\n\n--- Analysis Journey ---\n"
        
        # Build a narrative based on the workflow
        narrative = f"I analyzed your question about {companies_str}. "
        
        if workflow_state.get("department_tools_used", 0) > 0:
            narrative += f"First, I understood the scope and limitations of the data. "
            
        if workflow_state.get("category_tools_used", 0) > 0:
            narrative += f"Then, I identified the most relevant companies to your query. "
            
        if workflow_state.get("search_tools_used", 0) > 0:
            narrative += f"I searched through the earnings call database to find the most relevant transcripts. "
            
        if docs_analyzed > 0:
            narrative += f"I found {docs_analyzed} relevant document{'' if docs_analyzed == 1 else 's'} that contained the information you needed. "
            
        if workflow_state.get("summary_tools_used", 0) > 0 or workflow_state.get("full_doc_tools_used", 0) > 0:
            tools_used = []
            if workflow_state.get("summary_tools_used", 0) > 0:
                tools_used.append("analyzed document summaries")
            if workflow_state.get("full_doc_tools_used", 0) > 0:
                tools_used.append("performed deep dives into the full transcripts")
            
            narrative += f"I {' and '.join(tools_used)} to extract the most relevant information. "
        
        if exec_time > 0:
            # Make the time more human-readable
            if exec_time < 60:
                time_str = f"{exec_time:.1f} seconds"
            else:
                minutes = int(exec_time // 60)
                seconds = int(exec_time % 60)
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
                
            narrative += f"The entire analysis took me {time_str} to complete."
        
        monitor_info += narrative
            
        # Return the content followed by the prompt monitor narrative
        return content + monitor_info
    
    # For successful responses without workflow state, just return the content
    return content
