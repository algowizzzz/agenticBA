import json
import os
from pathlib import Path
from typing import Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

def load_tool_prompts_config():
    """
    Load the tool prompts configuration from a JSON file.
    
    Returns:
        dict: The tool prompts configuration dictionary
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Path to the tool prompts config file
    config_path = script_dir / "tool_prompts_config.json"
    
    # Check if the file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Tool prompts configuration file not found at {config_path}")
    
    # Load the configuration
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing tool prompts configuration: {e}")

def get_department_tool_config() -> Dict[str, Any]:
    """Get the department tool configuration"""
    config = load_tool_prompts_config()
    return config.get("department_tool", {})

def get_category_tool_config() -> Dict[str, Any]:
    """Get the category tool configuration"""
    config = load_tool_prompts_config()
    return config.get("category_tool", {})

def get_document_tool_config() -> Dict[str, Any]:
    """Get the document tool configuration"""
    config = load_tool_prompts_config()
    return config.get("document_tool", {})

def format_department_prompt(formatted_summary, query, category_summaries=""):
    """
    Format the department tool prompt using the template from the config.
    
    Args:
        formatted_summary (str): The formatted department summary
        query (str): The user query
        category_summaries (str, optional): Formatted summaries of available categories

    Returns:
        str: The formatted prompt ready to send to the LLM
    """
    # Get the department tool configuration
    dept_config = get_department_tool_config()
    
    # Get the prompt template from the config
    prompt_template = dept_config.get("prompt_template", "")
    
    # Replace the placeholders with the actual values
    prompt = prompt_template.replace("{formatted_summary}", formatted_summary)
    prompt = prompt.replace("{query}", query)
    prompt = prompt.replace("{category_summaries}", category_summaries)
    
    return prompt

def format_category_prompt(formatted_summary: str, query: str, category_id: str) -> str:
    """
    Format the category tool prompt with the given parameters.
    Requests plain text Thought/Answer output.
    """
    # Plain text prompt template
    prompt_template = """You are analyzing a category summary to answer a user's query.

Category Summary for {category_id}:
{formatted_summary}

User Query: {query}

Your task:
1. Analyze the Category Summary to see if it contains information to answer the User Query.
2. Explain your reasoning step-by-step.
3. Provide a concise answer based ONLY on the Category Summary.
4. If the summary does not contain enough information, you can infer BUT state that clearly.

Format your response as follows (PLAIN TEXT, NO JSON):
Thought: [Explain your reasoning step-by-step here]
Answer: [Provide your concise answer based ONLY on the summary, or state if infering or deducing]
"""

    return prompt_template.format(
        formatted_summary=formatted_summary,
        query=query,
        category_id=category_id 
    )

def format_document_prompt(query: str, documents: str) -> str:
    """
    Format the document tool prompt with the given parameters.
    Very simplified plain text version.
    
    Args:
        query (str): The user query (e.g., 'Summarize performance', 'What was revenue?')
        documents (str): Formatted document content (can be multiple documents concatenated)
        
    Returns:
        str: The formatted prompt ready to send to the LLM
    """
    # Very light prompt template
    prompt_template = """You are a helpful assistant analyzing earnings call transcripts.

User Query: {query}

Transcript(s):
{documents}

Based ONLY on the provided Transcript(s) text, provide a concise answer to the User Query.
If the transcripts don't contain the answer, simply state that the information is not available in the provided text.
Do not add any explanation or conversational filler unless the query specifically asks for it.

Answer:
"""
    
    prompt = prompt_template.format(query=query, documents=documents)
    
    return prompt

# Add these utility functions for handling other config types if needed
def get_summary_config():
    """
    Load the summary config if available
    
    Returns:
        dict: The summary configuration dictionary
    """
    # Try to load the summary config from the current directory or parent directory
    for config_path in [
        Path.cwd() / "summary_prompts_config.json",
        Path.cwd().parent / "summary_prompts_config.json"
    ]:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If there's an error, continue to the next potential location
                continue
    
    # If no config is found, return an empty dict
    return {}

def sanitize_json_response(response: str) -> str:
    """
    Clean up the LLM response to ensure it's valid JSON.
    Handles markdown fences and attempts to fix common control characters within strings.
    """
    logger.debug(f"Sanitizing JSON input (first 100 chars): {repr(response[:100])}")
    
    # Remove markdown fences first
    text = re.sub(r'^```json\n?', '', response.strip())
    text = re.sub(r'\n?```$', '', text.strip())
    text = text.strip()

    # Find the first { and last }
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1:
        logger.warning(f"No JSON object structure found in response: {text[:100]}...")
        raise ValueError(f"Response does not contain a JSON object: {text[:100]}") 

    # Extract the potential JSON block
    json_str = text[start_index : end_index + 1]

    # Attempt to fix common errors: unescaped newlines, tabs, etc. within the string values
    # Note: This is still heuristic and might fail on complex nested strings or edge cases.
    try:
        # Replace literal newlines, tabs, carriage returns NOT preceded by a backslash
        # Use negative lookbehind assertion (?<!\) to avoid double-escaping
        # Important: Process backslashes FIRST to avoid breaking other escapes
        fixed_json_str = json_str.replace('\\', '\\\\') # Escape existing backslashes
        fixed_json_str = fixed_json_str.replace('\"', '\\"') # Escape existing escaped quotes
        
        # Now replace literal control chars with their escaped versions
        fixed_json_str = fixed_json_str.replace('\n', '\\n')
        fixed_json_str = fixed_json_str.replace('\r', '\\r')
        fixed_json_str = fixed_json_str.replace('\t', '\\t')
        
        # Attempt to parse the fixed string
        json.loads(fixed_json_str)
        logger.debug(f"JSON parsed successfully after basic sanitization.")
        logger.debug(f"Sanitized JSON output (first 100 chars): {repr(fixed_json_str[:100])}")
        return fixed_json_str
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed even after basic sanitization: {e}")
        logger.debug(f"Problematic JSON string after basic sanitization (first 200 chars): {repr(fixed_json_str[:200])}")
        # Raise the error if basic fixing doesn't work
        raise ValueError(f"Failed to parse sanitized JSON. Error: {e}. String: {json_str[:200]}...")
    except Exception as e_other:
        logger.error(f"Unexpected error during sanitization: {e_other}")
        raise # Re-raise unexpected errors

# Category tool configuration
CATEGORY_TOOL_CONFIG = {
    "model": "claude-3-haiku-20240307",
    "temperature": 0,
    "max_tokens": 1000,
    "prompt_template": """Analyze the provided category summary for {category_id} and answer the query.

{summary}

Question: {query}

Think through this step by step:
1. Review the available information for {category_id}
2. Identify relevant details for the query
3. Determine if you can provide a confident answer
4. Format your response carefully

Your response MUST be a valid JSON object with these fields:
- thought: Your reasoning process
- answer: Your detailed answer or null if insufficient information
- document_ids: Array of relevant document IDs or empty array

Format your response EXACTLY like this, with commas between fields:
{
  "thought": "...",
  "answer": "...",
  "document_ids": []
}"""
}
