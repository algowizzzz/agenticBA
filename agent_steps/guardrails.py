#!/usr/bin/env python3
"""
Query guardrails for RiskGPT agent system.
"""

import json
import logging
from typing import Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from utils.parsing_utils import parse_json_response

logger = logging.getLogger("riskgpt.guardrails")

class Guardrails:
    """Implements safety and capability guardrails for user queries."""
    
    def __init__(self, llm_manager, persona=None, thinking_tracker=None):
        """
        Initialize guardrails with LLM and optional persona.
        
        Args:
            llm_manager: LLM manager instance for guardrail checking
            persona: Optional persona instance for persona-specific checks
            thinking_tracker: Optional thinking step tracker
        """
        self.llm_manager = llm_manager
        self.persona = persona
        self.thinking_tracker = thinking_tracker
        logger.info("Guardrails initialized")
    
    def check_query(self, query: str) -> Dict[str, Any]:
        """
        Check if a query passes safety and capability guardrails.
        
        Args:
            query: The query to check
            
        Returns:
            Dictionary with pass/fail status, modified query, and message
        """
        logger.info(f"[Guardrails] Checking query: {query}")
        
        if self.thinking_tracker:
            self.thinking_tracker.add_objective_understanding("Analyzing question to understand core information needs")
        
        # Check for empty query
        if not query or not query.strip():
            logger.info("[Guardrails] Empty query rejected")
            return {
                "pass": False,
                "query": query,
                "message": "Please provide a non-empty query."
            }
        
        if not self.llm_manager or not self.llm_manager.llm:
            logger.warning("[Guardrail] LLM not available, allowing query by default")
            return {"pass": True, "query": query, "message": ""}
        
        try:
            # Generate guardrail system prompt
            system_prompt = self._generate_guardrail_prompt()
            
            # Create human prompt for guardrail check
            human_prompt = f"Please evaluate this user query: \"{query}\""
            
            # Get response from LLM
            response = self.llm_manager.query(system_prompt, human_prompt)
            
            # Parse the response
            try:
                result = parse_json_response(response)
                
                if not result:
                    logger.error(f"[Guardrail] Failed to parse guardrail response: {response[:100]}...")
                    return {"pass": True, "query": query, "message": ""}
                
                # Log the guardrail decision
                decision = result.get("decision", "UNKNOWN")
                explanation = result.get("explanation", "")
                should_pass = result.get("pass", False)
                
                if should_pass:
                    if decision == "MODIFIED":
                        modified_query = result.get("modified_query", query)
                        logger.info(f"[Guardrail] Query modified: '{query}' -> '{modified_query}'")
                        return {"pass": True, "query": modified_query, "message": explanation}
                    else:
                        logger.info(f"[Guardrail] Query passed: '{query}'")
                        return {"pass": True, "query": query, "message": ""}
                else:
                    logger.warning(f"[Guardrail] Query rejected: '{query}', Reason: {explanation}")
                    return {"pass": False, "query": query, "message": explanation}
                    
            except Exception as e:
                logger.error(f"[Guardrail] Error parsing guardrail response: {e}")
                # Fail open - if we can't parse the guardrail response, let the query through
                return {"pass": True, "query": query, "message": ""}
                
        except Exception as e:
            logger.error(f"[Guardrail] Error during guardrail check: {e}")
            # Fail open
            return {"pass": True, "query": query, "message": ""}
    
    def _generate_guardrail_prompt(self) -> str:
        """
        Generate the guardrail prompt, incorporating persona if available.
        
        Returns:
            Guardrail system prompt
        """
        # Base guardrail prompt with persona injection if available
        if self.persona:
            system_prompt = f"""
{self.persona.get_persona_preamble()}

{self.persona.get_persona_injection("guardrails")}

For EACH query, FIRST determine if it should be:
- PASSED: The query is safe, appropriate, and specific enough to be processed
- MODIFIED: The query needs minor adjustments to be processable (e.g., clarification, rewording)
- REJECTED: The query violates guidelines and should not be processed

THEN respond in the following JSON format ONLY:
{{
  "decision": "PASSED|MODIFIED|REJECTED",
  "modified_query": "Only include if decision is MODIFIED, otherwise null",
  "explanation": "Brief explanation of your decision",
  "pass": true|false
}}

The "pass" field should be true for both PASSED and MODIFIED decisions, and false for REJECTED.
"""
        else:
            # Fall back to original guardrail prompt if persona not available
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
        
        return system_prompt 