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