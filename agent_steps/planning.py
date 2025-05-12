#!/usr/bin/env python3
"""
Planning module for RiskGPT agent system.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("riskgpt.planning")

class Planner:
    """Generates plans for tool execution based on user queries."""
    
    def __init__(self, llm_manager, tool_registry, persona=None, orchestrator=None, thinking_tracker=None):
        """
        Initialize the planner.
        
        Args:
            llm_manager: LLM manager for plan generation
            tool_registry: Tool registry for tool information
            persona: Optional persona instance for persona-specific planning
            orchestrator: Optional orchestrator for two-layer planning
            thinking_tracker: Optional thinking step tracker
        """
        self.llm_manager = llm_manager
        self.tool_registry = tool_registry
        self.persona = persona
        self.orchestrator = orchestrator
        self.thinking_tracker = thinking_tracker
        logger.info("Planner initialized")
    
    def generate_plan(self, query: str) -> str:
        """
        Generate a plan for answering the query.
        
        Args:
            query: The query to plan for
            
        Returns:
            The generated plan
        """
        logger.info(f"[Planner] Generating plan for query: {query}")
        
        if self.thinking_tracker:
            self.thinking_tracker.add_step("Analyzing query to determine required information sources and tools...", "planning")
        
        # If orchestrator is available, use it for enhanced planning
        if self.orchestrator:
            logger.info("[Planner] Using orchestrator for enhanced planning")
            
            if self.thinking_tracker:
                self.thinking_tracker.add_step("Using advanced planning to select optimal tools and execution sequence...", "planning")
                
            try:
                plan = self.orchestrator.generate_plan(query)
                
                # Extract tools from the plan for thinking steps
                self._add_tool_selection_steps(plan, query)
                
                return plan
            except Exception as e:
                logger.error(f"[Planner] Orchestrator planning failed: {e}")
                # Fall back to standard planning
                if self.thinking_tracker:
                    self.thinking_tracker.add_step("Advanced planning failed, falling back to standard planning...", "error")
        
        # Standard planning approach
        try:
            # Generate system prompt for planning
            system_prompt = self._generate_planning_prompt()
            
            # Create human prompt for planning
            human_prompt = f"""Generate a plan to answer the following query:

Query: "{query}"

Your plan should specify which tools to use (if any) and what input to provide to each tool.
"""
            
            # Get response from LLM
            plan = self.llm_manager.query(system_prompt, human_prompt)
            
            # Extract tools from the plan for thinking steps
            self._add_tool_selection_steps(plan, query)
            
            return plan
            
        except Exception as e:
            logger.error(f"[Planner] Error generating plan: {e}")
            return f"Error: Failed to generate plan: {str(e)}"
    
    def _add_tool_selection_steps(self, plan: str, query: str) -> None:
        """
        Add thinking steps for the tools selected in the plan.
        
        Args:
            plan: The generated plan
            query: The original query
        """
        if not self.thinking_tracker:
            return
            
        # Define some common tool selection reasons
        tool_reasons = {
            "FinancialSql": "financial metrics and quantitative data analysis is needed",
            "CcrSql": "counterparty credit risk data and exposure information is required",
            "JsonNews": "recent market news and financial intelligence would provide context",
            "EarningsCall": "management commentary and earnings call insights would be valuable",
            "ControlAnalysis": "evaluation of control effectiveness is needed",
        }
        
        # Check for direct response (no tools)
        if "No tool needed" in plan or "no tools are required" in plan.lower():
            self.thinking_tracker.add_tool_selection("Direct response", "the question can be answered with general knowledge")
            return
            
        # Look for tools in the plan
        for tool, reason in tool_reasons.items():
            if tool in plan:
                # Create a more specific reason based on the query
                specific_reason = reason
                if "financials" in query.lower() and tool == "FinancialSql":
                    specific_reason = "we need to retrieve specific financial metrics from the database"
                elif "risk" in query.lower() and tool == "CcrSql":
                    specific_reason = "we need to analyze counterparty credit risk data for risk assessment"
                elif "news" in query.lower() and tool == "JsonNews":
                    specific_reason = "we need to check recent news articles for market developments"
                elif "earnings" in query.lower() and tool == "EarningsCall":
                    specific_reason = "we need to analyze management commentary from earnings calls"
                elif "control" in query.lower() and tool == "ControlAnalysis":
                    specific_reason = "we need to evaluate control effectiveness based on the description"
                    
                self.thinking_tracker.add_tool_selection(tool, specific_reason)
    
    def _generate_planning_prompt(self) -> str:
        """
        Generate the planning prompt based on available tools and persona.
        
        Returns:
            System prompt for planning
        """
        # Create tool descriptions with display names if persona is available
        if self.persona:
            tool_descriptions = []
            for tool_name in self.tool_registry.get_all_tools().keys():
                display_name = self.persona.get_tool_display_name(tool_name)
                profile = self.tool_registry.get_tool_profile(tool_name)
                capabilities = ", ".join(profile.get("capabilities", []))
                
                tool_descriptions.append(f"*   {display_name}: {capabilities}")
            
            tool_descriptions_text = "\n".join(tool_descriptions)
            
            # Planning prompt with persona injection
            system_prompt = f"""
{self.persona.get_persona_preamble()}

{self.persona.get_persona_injection("planning")}

Your goal is to break down a query into a sequence of tool calls, or determine if it can be answered directly.

AVAILABLE TOOLS:
{tool_descriptions_text}

FORMAT YOUR RESPONSE AS A PLAN:
For tool-based plans:
Tool: [Tool Name]
Input: [Input for the tool]

Or, for queries that can be answered directly:
No tool needed. Reason: [Brief explanation of why built-in capabilities are sufficient]

IMPORTANT GUIDELINES:
1. Only include tools that are NECESSARY to answer the query.
2. Many queries can be answered with your built-in capabilities (coding, content creation, general knowledge).
3. For each tool, provide specific inputs that will yield relevant results.
4. Keep the plan concise and focused on direct value to the user.
"""
        else:
            # Fall back to generic tool descriptions
            tool_names = list(self.tool_registry.get_all_tools().keys())
            tool_descriptions = "\n".join([f"*   {name}" for name in tool_names])
            
            # Fall back to original planning prompt
            system_prompt = f"""You are a business analysis agent planning tool usage for financial analysis and operational risk.
Your goal is to break down a complex financial, business, or control-related query into a sequence of tool calls.

First, analyze the query to deeply understand what information or analysis is needed.
Then, outline a plan using only the necessary tools to answer the query.

AVAILABLE TOOLS:
{tool_descriptions}

FORMAT YOUR RESPONSE AS A PLAN USING THE FOLLOWING FORMAT:
Tool: [Tool Name]
Input: [Input for the tool]

IMPORTANT GUIDELINES:
1. Only include tools that are NECESSARY to answer the query. Do not include extra tools.
2. If no tool is needed to answer the query, simply respond with "No tool needed" followed by a brief explanation.
3. For each tool, provide specific inputs that will yield the most relevant results.
4. When comparing companies or time periods, include separate tool calls for each entity or period.
5. Keep the plan concise - only include tools that directly contribute to answering the query.
"""
        
        return system_prompt
    
    def _validate_plan(self, plan_text: str) -> bool:
        """
        Validate that a generated plan contains recognized tools.
        
        Args:
            plan_text: The plan text to validate
            
        Returns:
            Boolean indicating whether the plan is valid
        """
        if "No tool needed" in plan_text:
            return True
        
        # Get all tool names, including display names if persona is available
        recognized_tools = list(self.tool_registry.get_all_tools().keys())
        
        if self.persona:
            for tool in list(recognized_tools):  # Create a copy to avoid modifying during iteration
                display_name = self.persona.get_tool_display_name(tool)
                if display_name != tool:
                    recognized_tools.append(display_name)
        
        # Check if the plan contains any recognized tools
        return any(tool in plan_text for tool in recognized_tools) 