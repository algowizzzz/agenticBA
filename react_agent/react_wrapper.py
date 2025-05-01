"""
ReAct Agent Wrapper for Enterprise Internal Agent

This module implements a ReAct (Reasoning + Acting) agent wrapper around the
existing Enterprise Internal Agent pipeline. It allows for more conversational
and dynamic handling of user queries while leveraging the robust financial
data processing capabilities of the existing agent.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

# Setup logging
logger = logging.getLogger(__name__)

class ReactAgentWrapper:
    """
    A ReAct agent wrapper that can enhance the existing Enterprise Internal Agent
    with more conversational capabilities and dynamic reasoning.
    """
    
    def __init__(self, 
                llm,
                tools_map: Dict,
                db_paths: Dict,
                api_key: str,
                max_iterations: int = 10):
        """
        Initialize the ReAct agent wrapper.
        
        Args:
            llm: The language model to use for reasoning
            tools_map: Map of tool names to their callable functions
            db_paths: Dictionary of database paths
            api_key: API key for external services
            max_iterations: Maximum number of reasoning iterations
        """
        self.llm = llm
        self.tools_map = tools_map
        self.db_paths = db_paths
        self.api_key = api_key
        self.max_iterations = max_iterations
        self.conversation_history = []
    
    def run(self, query: str) -> str:
        """
        Run the ReAct agent on a user query.
        
        Args:
            query: The user's query
            
        Returns:
            The agent's response
        """
        # Initialize the system prompt with conversation history
        system_prompt = self._create_system_prompt(query)
        
        # Initialize messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Track the full ReAct trace for logging
        react_trace = []
        
        # Main ReAct Loop
        for i in range(self.max_iterations):
            logger.info(f"[ReAct] Iteration {i+1}/{self.max_iterations}")
            
            # Get the next reasoning step from the LLM
            response = self.llm.invoke(messages)
            response_text = response.content
            react_trace.append(response_text)
            
            # Check if we've reached a final answer
            if "Final Answer:" in response_text:
                final_answer = response_text.split("Final Answer:")[1].strip()
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": final_answer})
                
                logger.info(f"[ReAct] Found final answer after {i+1} iterations")
                return final_answer
            
            # Extract thought and action
            tool_name = None
            tool_input = None
            
            if "Action:" in response_text:
                # Parse the action
                action_text = response_text.split("Action:")[1].split("\n")[0].strip()
                
                # Extract tool name and parameters
                tool_match = re.match(r"(\w+)\((.+)\)", action_text)
                if tool_match:
                    tool_name = tool_match.group(1)
                    tool_input = tool_match.group(2).strip()
                    
                    # Execute the tool
                    observation = self._execute_tool(tool_name, tool_input)
                    
                    # Add to the message chain
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": observation})
                    react_trace.append(observation)
        
        # If we reach here, we've hit max iterations without a final answer
        logger.warning(f"[ReAct] Reached maximum iterations ({self.max_iterations}) without final answer")
        return "I apologize, but I wasn't able to reach a definitive answer to your query after multiple attempts. Please try rephrasing your question or breaking it down into smaller parts."
    
    def _create_system_prompt(self, query: str) -> str:
        """Create the system prompt for the ReAct agent."""
        # Format conversation history
        formatted_history = ""
        if self.conversation_history:
            for msg in self.conversation_history[-6:]:  # Last 3 turns
                role = "User" if msg["role"] == "user" else "Assistant"
                formatted_history += f"{role}: {msg['content']}\n"
        
        # Format tools description
        tools_desc = self._format_tools_description()
        
        return f"""
You are an Enterprise Financial Assistant that helps with financial data queries using a combination of reasoning and acting.

You have access to the following tools:
{tools_desc}

Follow this format:
Thought: your reasoning about what to do next
Action: tool_name(parameters)
Observation: result of the action
... (this Thought/Action/Observation can repeat multiple times)
Thought: I now know the final answer
Final Answer: the response to the user's query

Previous conversation:
{formatted_history}

Begin working on: {query}
"""
    
    def _format_tools_description(self) -> str:
        """Format the tools description for the system prompt."""
        tools_desc = [
            "enterprise_agent: A powerful tool for retrieving and analyzing financial data. Use this for specific data queries about companies, stocks, credit ratings, etc. Parameters: (query: str)",
            "conversation_handler: Used to respond to general questions, provide explanations, and handle follow-ups without using external tools. Parameters: (query: str)",
            "clarification_request: Used to ask the user for clarification when the query is ambiguous or more information is needed. Parameters: (question: str)"
        ]
        return "\n".join(tools_desc)
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool and return the observation."""
        logger.info(f"[ReAct] Executing tool: {tool_name} with input: {tool_input[:100]}...")
        
        try:
            if tool_name == "enterprise_agent":
                # Call the full Enterprise Internal Agent pipeline
                result = self._execute_enterprise_agent(tool_input)
                return f"Observation: {result}"
            
            elif tool_name == "conversation_handler":
                # Direct conversation handling through the LLM
                result = self._handle_conversation(tool_input)
                return f"Observation: {result}"
            
            elif tool_name == "clarification_request":
                # This would typically prompt the user, but for now just return what would be asked
                return f"Observation: The user would be asked: '{tool_input}'. For this simulation, assume they have not yet responded."
            
            else:
                return f"Observation: Unknown tool '{tool_name}'. Available tools are: enterprise_agent, conversation_handler, clarification_request"
        
        except Exception as e:
            logger.error(f"[ReAct] Error executing tool '{tool_name}': {e}", exc_info=True)
            return f"Observation: Error executing {tool_name}: {str(e)}"
    
    def _execute_enterprise_agent(self, query: str) -> str:
        """Execute the full Enterprise Internal Agent pipeline."""
        # This would call into the existing agent pipeline
        # For now, this is a placeholder
        return "Enterprise Agent result would appear here"
    
    def _handle_conversation(self, query: str) -> str:
        """Handle conversational queries directly through the LLM."""
        # This would handle general conversation without external tools
        # For now, this is a placeholder
        return "Direct conversation response would appear here"
