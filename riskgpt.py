#!/usr/bin/env python3
"""
RiskGPT - A comprehensive risk analysis agent with multiple tools.
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any, Optional, List, Tuple

# Core components
from agent_core.config import AgentConfig
from agent_core.llm_providers import LLMProviderFactory, LLMManager
from agent_core.memory import ConversationMemory
from agent_core.tool_registry import ToolRegistry

# Agent steps
from agent_steps.guardrails import Guardrails
from agent_steps.planning import Planner
from agent_steps.execution import Executor
from agent_steps.synthesis import Synthesizer
from agent_steps.confirmation import Confirmation

# Utilities
from utils.logging_utils import setup_logging
from utils.enhanced_thinking import EnhancedThinkingStepTracker

# Import persona if available
try:
    from riskgpt_persona import RiskGPTPersona
    HAS_PERSONA = True
except ImportError:
    HAS_PERSONA = False
    print("WARNING: RiskGPT persona module not found. Using default behavior.")

# Try to import orchestrator if available
try:
    from tool_orchestrator import TwoLayerOrchestrator
    HAS_ORCHESTRATOR = True
except ImportError:
    HAS_ORCHESTRATOR = False
    print("WARNING: TwoLayerOrchestrator not found. Enhanced tool selection will not be available.")

class RiskGPT:
    """Main RiskGPT agent with the refactored component-based architecture."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the RiskGPT agent.
        
        Args:
            config: Optional pre-configured AgentConfig instance
        """
        # Initialize logging
        setup_logging(log_level="INFO")
        self.logger = logging.getLogger("riskgpt.agent")
        self.logger.info("Initializing RiskGPT agent...")
        
        # Set up config
        self.config = config if config else AgentConfig()
        
        # Initialize thinking steps tracker
        self.thinking = EnhancedThinkingStepTracker()
        
        # Initialize persona if available
        if HAS_PERSONA:
            self.persona = RiskGPTPersona()
            self.logger.info(f"Initialized {self.persona.name} persona")
        else:
            self.persona = None
            self.logger.warning("RiskGPT persona not available. Using default behavior.")
        
        # Initialize LLM
        self._init_llm()
        
        # Initialize tool registry
        self._init_tools()
        
        # Initialize conversation memory
        self.memory = ConversationMemory(max_turns=5)
        
        # Initialize orchestrator if available
        if HAS_ORCHESTRATOR and self.llm and self.persona:
            self.orchestrator = TwoLayerOrchestrator(self)
            self.logger.info("Initialized two-layer orchestrator")
        else:
            self.orchestrator = None
            if HAS_ORCHESTRATOR:
                self.logger.warning("Orchestrator not initialized due to missing LLM or persona")
        
        # Initialize agent steps
        self._init_agent_steps()
        
        self.logger.info("RiskGPT agent initialized successfully")
    
    def _init_llm(self) -> None:
        """Initialize the LLM based on configuration."""
        try:
            api_key = self.config.get("anthropic_api_key")
            model_name = self.config.get("model_name")
            temperature = self.config.get("temperature", 0)
            
            llm = LLMProviderFactory.create_llm(
                provider="anthropic",
                model_name=model_name,
                api_key=api_key,
                temperature=temperature
            )
            
            if llm:
                self.llm_manager = LLMManager(llm)
                self.llm = llm  # For backward compatibility
                self.logger.info(f"LLM initialized with model: {model_name}")
            else:
                self.llm_manager = None
                self.llm = None
                self.logger.warning("Failed to initialize LLM")
        except Exception as e:
            self.llm_manager = None
            self.llm = None
            self.logger.error(f"Error initializing LLM: {e}")
    
    def _init_tools(self) -> None:
        """Initialize the tool registry and tools."""
        try:
            self.tool_registry = ToolRegistry(tools_dir="tools", load_profiles=True)
            self.tool_registry.register_default_tools()
            
            # Store tools_map for backward compatibility
            self.tools_map = self.tool_registry.get_all_tools()
            
            self.logger.info(f"Initialized tool registry with {len(self.tools_map)} tools")
        except Exception as e:
            self.tool_registry = None
            self.tools_map = {}
            self.logger.error(f"Error initializing tool registry: {e}")
    
    def _init_agent_steps(self) -> None:
        """Initialize the agent step components."""
        try:
            # Initialize guardrails
            self.guardrails = Guardrails(
                llm_manager=self.llm_manager,
                persona=self.persona,
                thinking_tracker=self.thinking
            )
            
            # Initialize planner
            self.planner = Planner(
                llm_manager=self.llm_manager,
                tool_registry=self.tool_registry,
                persona=self.persona,
                orchestrator=self.orchestrator,
                thinking_tracker=self.thinking
            )
            
            # Initialize executor
            self.executor = Executor(
                tool_registry=self.tool_registry,
                thinking_tracker=self.thinking,
                persona=self.persona
            )
            
            # Initialize synthesizer
            self.synthesizer = Synthesizer(
                llm_manager=self.llm_manager,
                thinking_tracker=self.thinking,
                persona=self.persona
            )
            
            # Initialize confirmation handler
            self.confirmation = Confirmation(
                thinking_tracker=self.thinking
            )
            
            self.logger.info("All agent step components initialized")
        except Exception as e:
            self.logger.error(f"Error initializing agent steps: {e}")
    
    def run(self, query: str) -> Dict[str, str]:
        """
        Process a user query through the agent pipeline.
        
        Args:
            query: The user query
            
        Returns:
            Dict with 'thinking_steps_str' and 'final_answer_str'
        """
        self.logger.info(f'--- Running query: "{query}" ---')
        self.thinking.clear()
        
        # --- 1. Guardrail Check ---
        self.logger.info("--- Step 1: Guardrail Check ---")
        self.thinking.add_step("Validating query against safety and capability guardrails...")
        
        try:
            guardrail_result = self.guardrails.check_query(query)
        except Exception as e:
            self.logger.error(f"Guardrail check failed: {e}")
            guardrail_result = {"pass": True, "query": query, "message": ""}
            self.thinking.add_step("Guardrail check encountered an error, proceeding with original query.")
        
        if not guardrail_result["pass"]:
            self.logger.info(f"Query rejected by guardrail: {guardrail_result['message']}")
            self.thinking.add_step(f"Query rejected: {guardrail_result['message'][:50]}...")
            return self._create_response(f"I'm unable to process this query: {guardrail_result['message']}")
        
        if guardrail_result["query"] != query:
            self.logger.info(f"Query modified by guardrail: '{query}' -> '{guardrail_result['query']}'")
            self.thinking.add_step(f"Clarifying query to: '{guardrail_result['query']}'")
            query = guardrail_result["query"]
        
        # Check for follow-up and context enhancement
        if self.memory.is_followup_question(query):
            contextual_query = self.memory.enhance_query_with_context(query)
            self.thinking.add_step("Recognizing follow-up question related to previous query...")
        else:
            contextual_query = query
        
        # --- 2. Planning ---
        self.logger.info("--- Step 2: Planning ---")
        self.thinking.add_step("Planning which tools are needed to answer your question...")
        
        try:
            plan = self.planner.generate_plan(contextual_query)
            self.logger.info(f"Generated Plan:\n{plan}")
        except Exception as e:
            self.logger.error(f"Plan generation failed: {e}")
            self.thinking.add_step("Error occurred during planning phase...")
            return self._create_response(f"Planning failed: {str(e)}")

        if plan.startswith("Error:"):
            self.thinking.add_step("Error occurred during planning phase...")
            return self._create_response(f"Planning failed: {plan}")
            
        # Record thinking steps for tools in the plan
        self.executor.record_thinking_step_for_tools(plan)
        
        # --- 3. Confirmation ---
        self.logger.info("--- Step 3: Confirming Plan ---")
        confirmed, message = self.confirmation.confirm_plan(plan)
        
        if not confirmed:
            self.logger.info("Plan rejected by user")
            return self._create_response(message)
        
        # --- 4. Execution ---
        self.logger.info("--- Step 4: Executing Plan ---")
        
        try:
            # Check for direct response
            if "No tool needed" in plan:
                self.logger.info("Using direct response based on plan")
                execution_results = self.executor.execute_direct_response(query, self.llm_manager)
            else:
                execution_results = self.executor.execute_plan(plan, llm_manager=self.llm_manager)
                
            self.logger.info(f"Execution completed with {len(execution_results)} results")
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            self.thinking.add_step(f"Error during execution phase: {str(e)[:50]}...")
            return self._create_response(f"Execution failed: {str(e)}")
        
        # --- 5. Synthesis ---
        self.logger.info("--- Step 5: Synthesizing Answer ---")
        
        try:
            final_answer = self.synthesizer.synthesize_answer(query, execution_results)
        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}")
            self.thinking.add_step("Error during synthesis phase...")
            return self._create_response(f"Synthesis failed: {str(e)}")
        
        # Add to memory
        self.memory.add_interaction(query, final_answer)
        
        return self._create_response(final_answer)
    
    def _create_response(self, final_answer: str) -> Dict[str, str]:
        """
        Create the final response dictionary.
        
        Args:
            final_answer: The final answer text
            
        Returns:
            Dict with 'thinking_steps_str' and 'final_answer_str'
        """
        return {
            "thinking_steps_str": self.thinking.get_formatted_steps(),
            "final_answer_str": final_answer
        }

def main():
    """Main CLI entry point for RiskGPT."""
    parser = argparse.ArgumentParser(description="RiskGPT - A comprehensive risk analysis agent")
    parser.add_argument("query", nargs="?", help="Query to process")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    
    # Create agent
    agent = RiskGPT()
    
    if args.interactive:
        print("\nRiskGPT Interactive Mode. Type 'exit' or 'quit' to exit.\n")
        while True:
            query = input("\nEnter your question: ")
            if query.lower() in ["exit", "quit"]:
                break
                
            response = agent.run(query)
            
            print("\n--- Thinking Steps ---")
            print(response["thinking_steps_str"])
            
            print("\n--- Agent Response ---")
            print(response["final_answer_str"])
    elif args.query:
        response = agent.run(args.query)
        
        print("\n--- Thinking Steps ---")
        print(response["thinking_steps_str"])
        
        print("\n--- Agent Response ---")
        print(response["final_answer_str"])
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 