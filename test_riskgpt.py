#!/usr/bin/env python3
"""
Test script for BasicAgent with RiskGPT persona.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def color_print(text, color):
    """Print colored text to terminal."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def main():
    """
    Test the BasicAgent with RiskGPT persona.
    """
    color_print("===== TESTING RISKGPT PERSONA =====", "blue")

    # Import the BasicAgent
    try:
        from basic_agent import BasicAgent
        color_print("Successfully imported BasicAgent", "green")
    except ImportError as e:
        color_print(f"ERROR: Failed to import BasicAgent: {e}", "red")
        sys.exit(1)
    
    # Test queries
    code_query = "Write a Python script to analyze credit risk data. The script should calculate exposure by counterparty, sort by exposure amount, and output a risk report."
    
    color_print("\n----- Testing RiskGPT with Code Creation Query -----\n", "cyan")
    
    try:
        # Create the agent
        agent = BasicAgent()
        
        # Get display names for tools if persona is available
        if hasattr(agent, 'persona') and agent.persona:
            tool_display_names = [agent.persona.get_tool_display_name(tool) for tool in agent.tools_map.keys()]
            color_print(f"Initialized with tool display names: {tool_display_names}", "green")
        else:
            color_print("No persona available, using default tool names", "yellow")
        
        # Run the query
        color_print(f"\nQuery: '{code_query}'", "yellow")
        result = agent.run(code_query)
        
        # Print thinking steps
        color_print("\nThinking Steps:", "magenta")
        print(result.get("thinking_steps_str", "No thinking steps provided"))
        
        # Print the result
        color_print("\nResponse:", "green")
        print(result.get("final_answer_str", "No response provided"))
        
    except Exception as e:
        color_print(f"ERROR: {type(e).__name__}: {e}", "red")
    
    color_print("\n===== TEST COMPLETE =====\n", "blue")

if __name__ == "__main__":
    main() 