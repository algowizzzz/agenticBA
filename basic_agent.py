#!/usr/bin/env python3
"""
Phase 3: Basic Agent with Multiple Tools & Confirmation
"""

import os
import sys # Add sys for path append if needed outside main
import logging
import inspect # Needed for argument inspection
import json # Potentially for plan parsing
import re # For plan parsing
from typing import Dict, Any, Callable, List, Tuple # Add types for memory

from dotenv import load_dotenv

# Langchain components
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

# Add Anthropic import to fix error
import anthropic

# --- Import Tool Functions --- 
sys.path.append(os.path.dirname(os.path.abspath(__file__))) # Ensure tools are importable
from tools.ccr_sql_tool import run_ccr_sql
from tools.financial_sql_tool import run_financial_sql
from tools.financial_news_tool import run_financial_news_search
from tools.earnings_call_tool import run_transcript_agent
from tools.control_analysis_tool import run_control_analyzer_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class BasicAgent:
    """Agent implementing Guardrail -> Plan -> Confirm -> Execute -> Synthesize flow."""

    def __init__(self):
        """Initializes the agent, LLM, tools, and DB paths."""
        logger.info("Initializing BasicAgent (Phase 3)...")
        # Explicitly load .env from the script's directory and override existing vars
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path=dotenv_path, override=True)
        logger.info(f"Environment variables loaded from {dotenv_path} with override.")

        try:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")

            # Initialize LLM
            model_name = "claude-3-5-sonnet-20240620" 
            self.llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=self.anthropic_api_key)
            logger.info(f"LLM Initialized: {getattr(self.llm, 'model', model_name)}")
            
            # Define DB Paths
            project_root = os.path.abspath(os.path.dirname(__file__))
            self.db_paths = {
                "financial": os.path.join(project_root, "scripts", "data", "financial_data.db"),
                "ccr": os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
            }
            logger.info(f"DB Paths Initialized: {self.db_paths}")
            # Add DB existence checks if desired
            if not os.path.exists(self.db_paths["financial"]):
                logger.warning(f"Financial DB not found at {self.db_paths['financial']}")
            if not os.path.exists(self.db_paths["ccr"]):
                logger.warning(f"CCR DB not found at {self.db_paths['ccr']}")
            
            # Define available tools for this phase
            self.tools_map: Dict[str, Callable] = {
                "CCRSQL": run_ccr_sql,
                "FinancialSQL": run_financial_sql,
                "FinancialNewsSearch": run_financial_news_search,
                "EarningsCallSummary": run_transcript_agent,
                "ControlDescriptionAnalysis": run_control_analyzer_agent,
            }
            logger.info(f"Tools map initialized with: {list(self.tools_map.keys())}")
            
            # Add conversation memory
            self.memory: List[Tuple[str, str]] = []  # List of (query, response) tuples
            logger.info("Conversation memory initialized.")
            
            # Initialize thinking steps collection
            self.thinking_steps: List[str] = []
            logger.info("Thinking steps tracking initialized.")

        except Exception as e:
            logger.error(f"Agent Initialization Failed: {e}", exc_info=True)
            raise 

        logger.info("BasicAgent initialized successfully.")

    # --- Agent Methods --- 

    def _add_thinking_step(self, step: str) -> None:
        """Add a simplified thinking step to track agent reasoning."""
        logger.info(f"[Thinking] {step}")
        self.thinking_steps.append(step)

    def _format_conversation_history(self, max_turns=3):
        """Format recent conversation history for inclusion in prompts."""
        if not self.memory:
            return ""
            
        # Get last few turns, limited by max_turns
        recent_memory = self.memory[-max_turns:]
        
        formatted_history = "Recent conversation history:\n"
        for i, (user_query, assistant_response) in enumerate(recent_memory):
            # Truncate very long responses
            if len(assistant_response) > 500:
                assistant_response = assistant_response[:500] + "..."
                
            formatted_history += f"User {i+1}: {user_query}\n"
            formatted_history += f"Assistant {i+1}: {assistant_response}\n\n"
            
        return formatted_history

    def _guardrail_check(self, query: str, override_llm=None) -> Dict[str, Any]:
        """
        Pre-processes the user query through a guardrail to check for:
        - Safety/appropriateness
        - Query within system's capabilities
        - Content policy compliance
        
        Returns:
            Dict with:
            - "pass": bool indicating if query passes guardrails
            - "query": potentially modified query if needed
            - "message": explanation if query is rejected
        """
        logger.info("[Guardrail] Checking query against guardrails...")
        
        # Use the provided LLM or default to self.llm
        llm_to_use = override_llm if override_llm else self.llm
        
        system_prompt = """You are a helpful but cautious AI assistant. Your role is to evaluate incoming user queries for:

1. Safety: No harmful, illegal, unethical or dangerous content
2. Appropriateness: No obscene, offensive or discriminatory content
3. Capabilities: Only financial analysis, data lookup, and business research are within scope
4. Specificity: Ensure the query is clear and specific enough to be processed

For EACH query, FIRST determine if it should be:
- PASSED: The query is safe, appropriate, within scope and specific enough
- MODIFIED: The query needs minor adjustments to be processable (e.g., clarification, rewording)
- REJECTED: The query violates guidelines and should not be processed

THEN respond in the following JSON format ONLY:
{
  "decision": "PASSED|MODIFIED|REJECTED",
  "modified_query": "Only include if decision is MODIFIED, otherwise null",
  "explanation": "Brief explanation of your decision",
  "pass": true|false
}

The "pass" field should be true for both PASSED and MODIFIED decisions, and false for REJECTED.
"""
        
        human_prompt = f"Please evaluate this user query: \"{query}\""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = llm_to_use.invoke(messages)
            
            # Parse the response
            try:
                result = json.loads(response.content.strip())
                
                # Log the guardrail decision
                if result.get("pass", False):
                    if result.get("decision") == "MODIFIED":
                        modified_query = result.get("modified_query", query)
                        logger.info(f"[Guardrail] Query modified: '{query}' -> '{modified_query}'")
                        return {"pass": True, "query": modified_query, "message": result.get("explanation", "")}
                    else:
                        logger.info(f"[Guardrail] Query passed: '{query}'")
                        return {"pass": True, "query": query, "message": ""}
                else:
                    logger.warning(f"[Guardrail] Query rejected: '{query}', Reason: {result.get('explanation', 'No reason provided')}")
                    return {"pass": False, "query": query, "message": result.get("explanation", "This query cannot be processed.")}
                    
            except json.JSONDecodeError:
                logger.error(f"[Guardrail] Failed to parse guardrail response: {response.content[:100]}...")
                # Fail open - if we can't parse the guardrail response, let the query through
                return {"pass": True, "query": query, "message": ""}
                
        except anthropic.BadRequestError as e:
            # Handle API credit issues
            if "credit balance is too low" in str(e) or "billing" in str(e).lower():
                logger.warning(f"[Guardrail] API credit issue: {e}")
            else:
                logger.error(f"[Guardrail] API error: {e}")
            # Fail open - if the API fails, let the query through
            return {"pass": True, "query": query, "message": ""}
        except anthropic.AuthenticationError as e:
            logger.error(f"[Guardrail] Authentication error: {e}")
            # Fail open
            return {"pass": True, "query": query, "message": ""}
        except Exception as e:
            logger.error(f"[Guardrail] Error during guardrail check: {e}", exc_info=True)
            # Fail open
            return {"pass": True, "query": query, "message": ""}
    
    def _generate_plan(self, query: str, override_llm=None) -> str:
        """Generates a plan outlining which tool(s) are needed."""
        logger.info("[Planner] Generating plan for multiple tools...")
        
        # Use the provided LLM or default to self.llm
        llm_to_use = override_llm if override_llm else self.llm
        
        # --- Define NEW Detailed Tool Descriptions ---
        # Descriptions now include data source, scope, and input hints.
        tool_descriptions = (
            "*   EarningsCallSummary: Analyzes company earnings call transcripts (primarily tech companies, ~2016-2020, from MongoDB) for qualitative insights. Use this to understand management's discussion of trends, strategic direction, product performance, market sentiment, and Q&A details. Especially useful for understanding the 'why' behind numbers or for comparative qualitative analysis over time or between companies. Input should specify company (e.g., 'MSFT') and period (e.g., 'Q1 2019', 'Full Year 2018 summary'). For direct quantitative figures like revenue numbers, prefer FinancialSQL.\\n"
            "*   FinancialSQL: Queries a SQL database (`financial_data.db`) containing quantitative financial data (quarterly income statements, balance sheets, daily stock prices, dividends). Use for specific financial figures like revenue, net income, EPS, assets, liabilities, stock price on a specific date, etc. Input is a natural language question about financial data.\\n"
            "*   FinancialNewsSearch: Searches for recent financial news articles (may be slightly outdated, as this is a demonstration capability). Use when seeking news about companies, markets, or economic events. Input is a search query about financial news.\\n"
            "*   CCRSQL: Queries a SQL database (`ccr_reporting.db`) containing counterparty credit risk data (exposures, limits, risk ratings, etc.). Use for credit risk analysis, exposure assessment, and limit monitoring. Input is a natural language question about counterparty risk.\\n"
            "*   ControlDescriptionAnalysis: Analyzes operational or non-financial control descriptions. This tool can perform a 5Ws (Who, What, When, Where, Why) coverage analysis, suggest improvements to the control wording, and generate test scripts for design and operating effectiveness. Input should be the control description and a clear statement of the desired action (e.g., 'full analysis of control: [description]', 'create test script for control: [description]', 'analyze 5Ws for control: [description]'). If the action is unclear, it defaults to a full analysis."
        )

        # --- Add Business Information ---
        system_prompt_content = f"""You are a business analysis agent planning tool usage for financial analysis and operational risk.
Your goal is to break down a complex financial, business, or control-related query into a sequence of tool calls.

First, analyze the query to deeply understand what information or analysis is needed.
Then, outline a plan using only the necessary tools to answer the query.

AVAILABLE TOOLS:
{tool_descriptions}

FORMAT YOUR RESPONSE AS A PLAN USING THE FOLLOWING FORMAT:
Tool: [Tool Name]
Input: [Input for the tool]

Tool: [Tool Name]
Input: [Input for the tool]

IMPORTANT GUIDELINES:
1. Only include tools that are NECESSARY to answer the query. Do not include extra tools.
2. If no tool is needed to answer the query, simply respond with "No tool needed" followed by a brief explanation.
3. For each tool, provide specific inputs that will yield the most relevant results. Make sure the input for ControlDescriptionAnalysis clearly states the desired action and includes the full control description.
4. When comparing companies or time periods, include separate tool calls for each entity or period.
5. Keep the plan concise - only include tools that directly contribute to answering the query.
6. For stock price queries, use FinancialSQL with a specific date.
7. For revenue, profit, or financial metrics, use FinancialSQL for quantitative data.
8. For earnings calls insights, use EarningsCallSummary with specific company ticker and period.
9. For credit risk analysis, use CCRSQL.
10. For recent news, use FinancialNewsSearch.
11. For analyzing control descriptions (5Ws, improvements, test scripts), use ControlDescriptionAnalysis.
"""

        human_prompt_content = f"Generate a plan using the necessary tools to answer this query: {query}"

        try:
            messages = [
                SystemMessage(content=system_prompt_content),
                HumanMessage(content=human_prompt_content)
            ]
            response = llm_to_use.invoke(messages)
            plan_text = response.content.strip()
            logger.info(f"[Planner] Raw plan text:\n{plan_text}")
            
            # Validate that there are at least some recognized tool names in the plan
            recognized_tools = ["FinancialSQL", "CCRSQL", "EarningsCallSummary", "FinancialNewsSearch", "ControlDescriptionAnalysis", "No tool needed"]
            if not any(tool in plan_text for tool in recognized_tools):
                logger.warning("[Planner] Generated plan does not contain recognized tools. Using 'No tool needed' fallback.")
                plan_text = "No tool needed for this query, as it can be answered with general knowledge."
            
            return plan_text
            
        except anthropic.BadRequestError as e:
            # Handle API credit issues
            if "credit balance is too low" in str(e) or "billing" in str(e).lower():
                logger.warning(f"[Planner] API credit issue: {e}")
                return f"Error generating plan: {str(e)}"
            else:
                logger.error(f"[Planner] API error: {e}")
                return f"Error generating plan: {str(e)}"
        except anthropic.AuthenticationError as e:
            logger.error(f"[Planner] Authentication error: {e}")
            return f"Error generating plan: {str(e)}"
        except Exception as e:
            logger.error(f"[Planner] Error during plan generation: {e}", exc_info=True)
            return f"Error generating plan: {str(e)}"

    def _execute_plan(self, plan: str) -> Dict[str, Any]:
        """Parses the plan and executes the specified tool steps sequentially."""
        logger.info(f"[Executor] Executing full plan:\n{plan}")
        results = {} # Store results with unique keys
        # Track tool usage counts for unique keys
        tool_usage_counters = {}
        planned_steps = []

        # --- Parse the plan text into steps --- 
        # Assumes format: Tool: [Name]\nInput: [Input] potentially repeated
        lines = plan.strip().split('\n')
        current_tool = None
        current_input_lines = []
        for line in lines:
            line_strip = line.strip()
            tool_match = re.match(r"Tool:\s*(.*)", line_strip)
            input_match = re.match(r"Input:\s*(.*)", line_strip)

            if tool_match:
                # If we were gathering input for a previous tool, store it
                if current_tool and current_input_lines:
                    planned_steps.append({"tool": current_tool, "input": "\n".join(current_input_lines).strip()})
                    current_input_lines = [] # Reset for next input
                current_tool = tool_match.group(1).strip()
            elif input_match and current_tool: # Start gathering input for the current tool
                current_input_lines = [input_match.group(1).strip()]
            elif current_tool and current_input_lines: # Continue gathering multi-line input
                 current_input_lines.append(line) # Append the raw line to preserve formatting
        
        # Add the last step if any
        if current_tool and current_input_lines:
            planned_steps.append({"tool": current_tool, "input": "\n".join(current_input_lines).strip()})
        
        logger.info(f"[Executor] Parsed {len(planned_steps)} steps from plan.")
        if not planned_steps:
            logger.warning("[Executor] No valid steps parsed from plan.")
            self._add_thinking_step("Unable to parse execution steps from plan...")
            return {"error": "No valid execution steps could be parsed from the plan."}

        # --- Execute each step --- 
        print("\nExecuting steps. Press Ctrl+C at any time to interrupt processing.")
        for i, step in enumerate(planned_steps):
            tool_name = step["tool"]
            tool_input = step["input"]
            step_num = i + 1
            logger.info(f"[Executor] Executing Step {step_num}/{len(planned_steps)}: Tool='{tool_name}', Input='{tool_input[:100]}...'")
            
            # Add specific thinking step for each tool execution
            if tool_name == "FinancialSQL":
                self._add_thinking_step(f"Querying financial database: '{tool_input[:50]}...'")
            elif tool_name == "CCRSQL":
                self._add_thinking_step(f"Analyzing credit risk data: '{tool_input[:50]}...'")
            elif tool_name == "FinancialNewsSearch":
                self._add_thinking_step(f"Searching for financial news: '{tool_input[:50]}...'")
            elif tool_name == "EarningsCallSummary":
                self._add_thinking_step(f"Analyzing earnings call transcripts: '{tool_input[:50]}...'")
            elif tool_name == "ControlDescriptionAnalysis":
                self._add_thinking_step(f"Analyzing control description: '{tool_input[:50]}...'")
            else:
                self._add_thinking_step(f"Executing {tool_name}: '{tool_input[:50]}...'")
            
            tool_function = self.tools_map.get(tool_name)
            if not tool_function:
                logger.warning(f"[Executor] Step {step_num}: Unknown tool '{tool_name}' found in plan.")
                self._add_thinking_step(f"Error: Unknown tool '{tool_name}' specified in plan...")
                results[f"Error_Step{step_num}_{tool_name}"] = f"Unknown tool '{tool_name}' specified in plan step {step_num}."
                continue # Skip to next step

            try:
                # Prepare arguments using introspection
                kwargs = {"query": tool_input} # Default
                # Adjust primary input key if needed (e.g., DirectAnswer)
                # if tool_name == "DirectAnswer": kwargs = {"instruction": tool_input}

                sig = inspect.signature(tool_function)
                tool_params = sig.parameters
                
                if "llm" in tool_params: kwargs["llm"] = self.llm
                if "db_path" in tool_params:
                    db_key = "ccr" # Default assumption
                    if tool_name == "FinancialSQL": db_key = "financial"
                    kwargs["db_path"] = self.db_paths.get(db_key)
                
                # For emergency stop
                try:
                    logger.info(f"[Executor] Step {step_num}: Calling tool '{tool_name}' with input: '{tool_input[:100]}...'")
                    # Actually execute the tool function with appropriate kwargs
                    tool_result = tool_function(**kwargs)
                    logger.info(f"[Executor] Step {step_num}: Tool '{tool_name}' executed successfully.")
                    
                    # Add result thinking step
                    if isinstance(tool_result, dict):
                        if tool_result.get("error"):
                            self._add_thinking_step(f"Tool execution failed: {tool_result.get('error')[:50]}...")
                        elif "sql_result" in tool_result:
                            result_preview = str(tool_result["sql_result"])[:30].replace("\n", " ")
                            self._add_thinking_step(f"Database returned results: '{result_preview}...'")
                        else:
                            self._add_thinking_step(f"Tool execution completed successfully...")
                    else:
                        self._add_thinking_step(f"Tool returned result: '{str(tool_result)[:30]}...'")
                    
                    # Create a unique key for this tool call
                    if tool_name not in tool_usage_counters:
                        tool_usage_counters[tool_name] = 1
                    else:
                        tool_usage_counters[tool_name] += 1
                    unique_key = f"{tool_name}_{tool_usage_counters[tool_name]}"
                    
                    # Store with unique key
                    results[unique_key] = tool_result
                    
                except KeyboardInterrupt:
                    logger.warning(f"[Executor] Step {step_num}: Tool execution interrupted by user.")
                    self._add_thinking_step("Tool execution interrupted by user...")
                    results[f"Error_Step{step_num}_{tool_name}"] = "Tool execution interrupted by user."
                    break # Exit the loop early
                    
            except Exception as e:
                logger.error(f"[Executor] Step {step_num}: Error executing tool '{tool_name}': {e}", exc_info=True)
                self._add_thinking_step(f"Error during tool execution: {str(e)[:50]}...")
                results[f"Error_Step{step_num}_{tool_name}"] = f"Error executing tool: {str(e)}"
                continue # Try to continue with other steps
        
        logger.info(f"[Executor] Plan execution completed with {len(results)} results.")
        return results

    def _format_sql_results(self, results_str: str, max_rows=10) -> str:
        """Format SQL results in a more readable way.
        
        Args:
            results_str: String representation of SQL results, typically in the form "[('val1', val2), ...]"
            max_rows: Maximum number of rows to include in formatted output
            
        Returns:
            Formatted string representation of the results
        """
        if not results_str or not isinstance(results_str, str):
            return "No results found."
            
        try:
            # Parse the results string (assuming it's like "[('col1', val1), ('col2', val2)]")
            data = eval(results_str)
            
            if not data:
                return "Query executed successfully but returned no data."
                
            # Handle empty result set
            if isinstance(data, list) and len(data) == 0:
                return "Query returned an empty result set."
                
            # Count rows and apply limit if needed
            row_count = len(data)
            if row_count > max_rows:
                formatted = f"Showing first {max_rows} of {row_count} rows:\n"
                data = data[:max_rows]
            else:
                formatted = f"Results ({row_count} rows):\n"
                
            # Format as a simple table
            if isinstance(data, list) and all(isinstance(row, tuple) for row in data):
                # For single row with a single value (scalar result)
                if len(data) == 1 and len(data[0]) == 1:
                    value = data[0][0]
                    return f"Result: {value}"
                    
                # For multiple rows or columns
                for i, row in enumerate(data):
                    row_formatted = ", ".join([str(col) for col in row])
                    formatted += f"Row {i+1}: {row_formatted}\n"
                    
            else:
                # Fallback for unexpected formats
                formatted += str(data)
                
            return formatted.strip()
            
        except Exception as e:
            logger.warning(f"Error formatting SQL results: {e}")
            return results_str  # Return original if parsing fails

    def _synthesize_answer(self, query: str, execution_results: Dict[str, Any], override_llm=None) -> str:
        """Generates a final answer based on the query and execution results."""
        logger.info("[Synthesizer] Synthesizing final answer...")
        llm_to_use = override_llm if override_llm else self.llm

        # Format the results for the prompt
        result_context = ""
        empty_results = True
        if not execution_results:
             result_context = "No tool was executed or planned."
        elif "error" in execution_results and len(execution_results) == 1: # Check if the only key is 'error'
             result_context = f"Error during plan parsing or initial execution: {execution_results['error']}"
        else:
            formatted_results = []
            for tool_name, result_data in execution_results.items():
                # Extract base tool name (removing the unique identifier)
                base_tool_name = tool_name.split("_")[0] if "_" in tool_name and not tool_name.startswith("Error_Step") else tool_name
                if tool_name.startswith("Error_Step"):
                    formatted_results.append(f"Error during step {tool_name}: {result_data}")
                elif isinstance(result_data, dict):
                    # Nicely format known dict structures (like SQL)
                    if "sql_query" in result_data:
                        sql_result = result_data.get('sql_result', 'N/A')
                        # Use the new formatter for SQL results if available
                        if sql_result != 'N/A':
                            formatted_sql_result = self._format_sql_results(sql_result)
                            # Check if data was actually returned
                            if "(None,)" in str(sql_result) or "empty result set" in formatted_sql_result.lower():
                                formatted_results.append(f"Tool: {base_tool_name}\\nSQL Query: {result_data.get('sql_query', 'N/A')}\\nResult: NO DATA FOUND\\nError: {result_data.get('error', 'None')}")
                            else:
                                empty_results = False
                                formatted_results.append(f"Tool: {base_tool_name}\\nSQL Query: {result_data.get('sql_query', 'N/A')}\\nResult: {formatted_sql_result}\\nError: {result_data.get('error', 'None')}")
                        else:
                            formatted_results.append(f"Tool: {base_tool_name}\\nSQL Query: {result_data.get('sql_query', 'N/A')}\\nResult: {sql_result}\\nError: {result_data.get('error', 'None')}")
                    elif "error" in result_data: # Tool execution error
                        formatted_results.append(f"Tool: {base_tool_name}\\nError: {result_data['error']}")
                    elif "answer" in result_data and "No relevant information" in str(result_data.get("answer", "")):
                        # For transcript tools that found no relevant information
                        formatted_results.append(f"Tool: {base_tool_name}\\nResult: NO RELEVANT DATA FOUND")
                    else: # Generic dict
                        # Check if the result is empty or indicates no data
                        result_str = json.dumps(result_data, indent=2)
                        if "no data" in result_str.lower() or "not found" in result_str.lower():
                            formatted_results.append(f"Tool: {base_tool_name}\\nResult: NO DATA FOUND")
                        else:
                            empty_results = False
                            formatted_results.append(f"Tool: {base_tool_name}\\nResult: {result_str}")
                else: # Other data types
                    # Check if result is empty or indicates no data
                    result_str = str(result_data)
                    if "no data" in result_str.lower() or "not found" in result_str.lower() or "none" == result_str.lower():
                        formatted_results.append(f"Tool: {base_tool_name}\\nResult: NO DATA FOUND")
                    else:
                        empty_results = False
                        formatted_results.append(f"Tool: {base_tool_name}\\nResult: {result_str}")
            result_context = "\\n\\n".join(formatted_results)

        logger.debug(f"[Synthesizer] Context for synthesis prompt:\n{result_context}")

        system_prompt_content = """You are a helpful financial and business analysis assistant. Your goal is to provide the MOST USEFUL and VALUABLE answer to the user's query based on the available information, even if that information is incomplete.

IMPORTANT GUIDELINES:
1. When no data was found by the tools or the tools failed, you MUST CLEARLY STATE AT THE START of your answer that you are providing information based on general knowledge rather than specific data from the tools.
2. Begin your response with "NOTICE: I could not retrieve specific data from the databases..." when no actual data was returned.
3. Focus on what you CAN answer based on the available information, not what you can't.
4. If specific documents or data were not found, don't dwell on these limitations. Instead, provide general insights on the topic based on available context.
5. When documents from one company are missing but another company's information is available, provide helpful comparative analysis when possible.
6. Synthesize all available information to provide a coherent, helpful response.
7. Use clear, confident language and structure your response with headings and bullet points when appropriate.
8. If data is sparse, you may draw reasonable inferences or provide general domain knowledge about the financial/business topic, clearly indicating when you're doing so.
9. Always aim to provide ACTIONABLE INSIGHTS even with limited information.
10. NEVER invent or fabricate specific financial data (revenue figures, growth rates, etc.) when they're not in the context.

Remember, your goal is to be as helpful as possible while remaining accurate with the information you have."""

        # Add conversation history to the prompt if available
        conversation_context = self._format_conversation_history()
        if conversation_context:
            system_prompt_content = system_prompt_content + "\n\n" + conversation_context
        
        human_prompt_content = f"""Original User Query: "{query}"

Tool Execution Results Context:
--- START CONTEXT ---
{result_context}
--- END CONTEXT ---

Based on the provided context, formulate a USEFUL and COMPREHENSIVE answer to the Original User Query. If specific documents or data were not found, provide general insights about the topic and focus on what value you CAN provide based on the available information. 

IMPORTANT: If the tools returned NO DATA or NO RELEVANT DATA, begin your response with a clear notice to the user explaining that your answer is based on general knowledge, not specific data from the tools."""

        try:
            messages = [ 
                SystemMessage(content=system_prompt_content),
                HumanMessage(content=human_prompt_content) 
            ]
            response = llm_to_use.invoke(messages)
            final_answer = response.content.strip()
            
            # Double check - if all results were empty but the response doesn't make it clear, add a prefix
            if empty_results and not any(x in final_answer[:200] for x in ["NOTICE:", "I could not retrieve", "Based on general knowledge", "I don't have specific data"]):
                final_answer = "NOTICE: I could not retrieve specific data from the databases for your query. The following response is based on general knowledge rather than specific tool results.\n\n" + final_answer
                
            logger.info(f"[Synthesizer] Synthesized answer: {final_answer[:500]}...")
            return final_answer
        except Exception as e:
            logger.error(f"[Synthesizer] Error during answer synthesis: {e}", exc_info=True)
            return f"Error synthesizing answer: {str(e)}"

    def run(self, query: str, override_llm=None) -> Dict[str, str]:
        """Runs the Guardrail -> Plan -> [Confirm] -> Execute -> Synthesize flow.
        Returns a dictionary with 'thinking_steps_str' and 'final_answer_str'.
        """
        logger.info(f'--- Running query: "{query}" ---')
        
        # Use the provided override_llm or default to self.llm
        llm_to_use = override_llm if override_llm else self.llm
        
        # Clear previous thinking steps
        self.thinking_steps = [] 
        # Initial thinking step will be added by guardrail, plan, etc.

        # --- 0. Guardrail Check ---
        logger.info("--- Step 0: Guardrail Check ---")
        self._add_thinking_step("Validating query against safety and capability guardrails...")
        
        try:
            guardrail_result = self._guardrail_check(query, override_llm=llm_to_use)
        except Exception as e:
            logger.error(f"Guardrail check failed: {e}")
            guardrail_result = {"pass": True, "query": query, "message": ""}
            self._add_thinking_step("Guardrail check encountered an error, proceeding with original query.")
        
        if not guardrail_result["pass"]:
            logger.info(f"Query rejected by guardrail: {guardrail_result['message']}")
            self._add_thinking_step(f"Query rejected: {guardrail_result['message'][:50]}...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            # Return dict on failure
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": f"I'm unable to process this query: {guardrail_result['message']}"
            }
        
        if guardrail_result["query"] != query:
            logger.info(f"Query modified by guardrail: '{query}' -> '{guardrail_result['query']}'")
            self._add_thinking_step(f"Clarifying query to: '{guardrail_result['query']}'")
            query = guardrail_result["query"]
        
        contextual_query = query
        # ... (rest of the follow-up logic remains the same)
        followup_indicators = ["what about", "tell me more", "and what", "how about", "what is", "can you explain"]
        if self.memory and any(query.lower().startswith(indicator) for indicator in followup_indicators):
            prev_query, prev_response = self.memory[-1]
            contextual_query = f"{query} (Context from previous query: '{prev_query}')"
            logger.info(f"Follow-up detected. Enhanced query: {contextual_query}")
            self._add_thinking_step(f"Recognizing follow-up question related to previous query...")
        
        logger.info("--- Step 1: Generating Plan ---")
        self._add_thinking_step("Planning which tools are needed to answer your question...")
        
        try:
            plan = self._generate_plan(contextual_query, override_llm=llm_to_use)
            logger.info(f"Generated Plan:\n{plan}")
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            self._add_thinking_step("Error occurred during planning phase...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": f"Planning failed: {str(e)}"
            }

        if plan.startswith("Error:"):
            self._add_thinking_step("Error occurred during planning phase...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": f"Planning failed: {plan}"
            }

        if "No tool needed" in plan:
            logger.info("Plan indicates no tool needed. Attempting direct LLM response.")
            self._add_thinking_step("No specialized tools needed, answering from general knowledge...")
            try:
                 system_content = "You are a helpful assistant answering based on general knowledge as no specific tools were deemed necessary."
                 if self.memory:
                     memory_context = "\n".join([f"Previous query: {q}\nYour response: {r}\n" 
                                               for q, r in self.memory[-3:]])
                     system_content += f"\n\nRecent conversation history:\n{memory_context}"
                 
                 direct_messages = [
                     SystemMessage(content=system_content),
                     HumanMessage(content=query),
                 ]
                 response = llm_to_use.invoke(direct_messages)
                 final_answer = response.content.strip()
                 logger.info(f"Direct LLM Response: {final_answer[:500]}...")
                 self._add_thinking_step("Synthesizing answer from general knowledge...")
                 
                 self.memory.append((query, final_answer))
                 if len(self.memory) > 5: self.memory.pop(0)
                     
                 thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
                 return {
                    "thinking_steps_str": thinking_output,
                    "final_answer_str": final_answer
                 }
            except Exception as e:
                logger.error(f"Error during direct LLM invocation: {e}", exc_info=True)
                self._add_thinking_step("Error occurred while generating direct response...")
                thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
                return {
                    "thinking_steps_str": thinking_output,
                    "final_answer_str": f"Sorry, an error occurred while trying to answer directly: {str(e)}"
                }

        if "FinancialSQL" in plan: self._add_thinking_step("Preparing to search financial database for relevant data...")
        if "CCRSQL" in plan: self._add_thinking_step("Preparing to query counterparty credit risk database...")
        if "FinancialNewsSearch" in plan: self._add_thinking_step("Planning to search for recent financial news and market information...")
        if "EarningsCallSummary" in plan: self._add_thinking_step("Will analyze earnings call transcripts for relevant insights...")
        if "ControlDescriptionAnalysis" in plan: self._add_thinking_step("Preparing to analyze the provided control description...")

        logger.info("--- Step 2: Confirming Plan ---")
        self._add_thinking_step("Awaiting confirmation of proposed execution plan...")
        print(f"\nProposed Plan:\n{plan}")
        confirmation = input("Proceed with this plan? [Y/n]: ").strip().lower()
        
        if confirmation == "" or confirmation.startswith('y'):
            logger.info("Plan confirmed by user.")
            self._add_thinking_step("Plan confirmed, proceeding with execution...")
        else:
            logger.info("Plan rejected by user.")
            self._add_thinking_step("Plan rejected by user, halting execution...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": "Plan execution cancelled by user."
            }

        logger.info(f"--- Step 3: Executing Confirmed Plan ---")
        self._add_thinking_step("Executing tools according to plan...")
        try:
            execution_results = self._execute_plan(plan) 
            logger.info(f"Execution Results: {str(execution_results)[:500]}...")
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            self._add_thinking_step(f"Error during execution phase: {str(e)[:50]}...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": f"Execution failed: {str(e)}"
            }
        
        logger.info("--- Step 4: Synthesizing Answer ---")
        self._add_thinking_step("Synthesizing comprehensive answer from all gathered information...")
        try:
            final_answer_str = self._synthesize_answer(query, execution_results, override_llm=llm_to_use)
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            self._add_thinking_step("Error during synthesis phase...")
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return {
                "thinking_steps_str": thinking_output,
                "final_answer_str": f"Synthesis failed: {str(e)}"
            }
        
        self.memory.append((query, final_answer_str)) # Store the clean answer in memory
        if len(self.memory) > 5: self.memory.pop(0)
        
        # Construct thinking_output string here before returning
        thinking_output_str = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
        
        # Internal logging of the final answer (can be removed if too verbose)
        logger.info("--- Final Answer (from agent.run internal log) ---")
        logger.info(final_answer_str)
        
        return {
            "thinking_steps_str": thinking_output_str, 
            "final_answer_str": final_answer_str
        }

def main():
    """Main function to run the agent with test queries or command-line input."""
    logger.info("--- Basic Agent (Phase 3) Starting ---")
    agent = BasicAgent()

    # --- Main Execution ---
    if len(sys.argv) > 1:
        query = sys.argv[1]
        logger.info(f'--- Running query from command line: "{query}" --- ') # Slightly changed log
        
        # agent.run() now returns a dictionary
        response_dict = agent.run(query)
        
        thinking_steps_output = response_dict.get("thinking_steps_str", "No thinking steps provided.")
        final_answer_output = response_dict.get("final_answer_str", "No final answer provided.")

        # Log the structured response from main
        logger.info("--- Thinking Steps (from main log) ---")
        # Avoid logging the raw list if it's already formatted in thinking_steps_output
        # For clarity, just log the string that agent.run() prepared
        for line in thinking_steps_output.split('\n'):
            if line.strip(): # Avoid empty lines if any
                logger.info(line)

        logger.info("--- Final Answer (from main log) ---")
        logger.info(final_answer_output)

        # Print to standard output for the user
        print("\n--- Thinking Steps ---")
        print(thinking_steps_output) # This string already starts with "Thinking..."
        
        print("\n--- Agent Response ---")
        print(final_answer_output)

    else:
        # Fallback to test queries or interactive mode
        logger.info("--- No command line query provided. Please provide a query as a command line argument. ---")
        logger.info("Example: python basic_agent.py \"What was Apple's revenue in 2020?\"")
        # ... (interactive mode example can be updated similarly if revived)

if __name__ == "__main__":
    main() 