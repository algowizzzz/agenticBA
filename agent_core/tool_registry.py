#!/usr/bin/env python3
"""
Tool registry for RiskGPT agent system.
"""

import os
import sys
import json
import logging
import importlib
from typing import Dict, List, Any, Callable, Optional, Tuple

logger = logging.getLogger("riskgpt.tools")

class ToolRegistry:
    """Registry for agent tools with dynamic loading capabilities."""
    
    def __init__(self, tools_dir: str = "tools", load_profiles: bool = True):
        """
        Initialize the tool registry.
        
        Args:
            tools_dir: Directory containing tool modules
            load_profiles: Whether to load tool profiles from tool_profiles.json
        """
        self.tools_dir = tools_dir
        self.tools_map: Dict[str, Callable] = {}
        self.profiles: Dict[str, Dict[str, Any]] = {}
        
        # Set up tools import path
        self._setup_tools_path()
        
        # Load tool profiles if requested
        if load_profiles:
            self._load_tool_profiles()
        
        logger.info(f"Tool registry initialized with directory: {tools_dir}")
    
    def _setup_tools_path(self) -> None:
        """Ensure tools directory is in the Python path."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tools_path = os.path.join(project_root, self.tools_dir)
        
        if os.path.exists(tools_path) and tools_path not in sys.path:
            sys.path.append(tools_path)
            logger.info(f"Added {tools_path} to Python path")
        elif not os.path.exists(tools_path):
            logger.warning(f"Tools directory not found at {tools_path}")
    
    def _load_tool_profiles(self) -> None:
        """Load tool profiles from tool_profiles.json."""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            profile_path = os.path.join(project_root, "tool_profiles.json")
            
            if os.path.exists(profile_path):
                with open(profile_path, 'r') as f:
                    self.profiles = json.load(f)
                logger.info(f"Loaded {len(self.profiles)} tool profiles from {profile_path}")
            else:
                logger.warning(f"Tool profiles file not found at {profile_path}")
        except Exception as e:
            logger.error(f"Error loading tool profiles: {e}")
    
    def register_tool(self, name: str, tool_function: Callable) -> None:
        """
        Register a tool with the registry.
        
        Args:
            name: The tool name
            tool_function: The tool function
        """
        self.tools_map[name] = tool_function
        logger.info(f"Registered tool: {name}")
    
    def register_tool_from_module(self, internal_name: str, module_name: str, function_name: str) -> bool:
        """
        Register a tool by dynamically importing it from a module.
        
        Args:
            internal_name: Internal name for the tool
            module_name: Name of the module containing the tool
            function_name: Name of the function in the module
            
        Returns:
            True if registration succeeded, False otherwise
        """
        try:
            module = importlib.import_module(module_name)
            tool_function = getattr(module, function_name)
            self.register_tool(internal_name, tool_function)
            return True
        except ImportError:
            logger.error(f"Failed to import module: {module_name}")
            return False
        except AttributeError:
            logger.error(f"Function {function_name} not found in module {module_name}")
            return False
        except Exception as e:
            logger.error(f"Error registering tool {internal_name}: {e}")
            return False
    
    def register_default_tools(self) -> None:
        """Register the default set of tools based on tool profiles."""
        if not self.profiles:
            logger.warning("No tool profiles available, skipping default tool registration")
            return
        
        for internal_name, profile in self.profiles.items():
            module_name = profile.get("module_name")
            function_name = profile.get("function_name")
            
            if module_name and function_name:
                success = self.register_tool_from_module(internal_name, f"{self.tools_dir}.{module_name}", function_name)
                if not success:
                    logger.warning(f"Failed to register default tool: {internal_name}")
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Get a tool by name.
        
        Args:
            name: The tool name
            
        Returns:
            The tool function or None if not found
        """
        return self.tools_map.get(name)
    
    def execute_tool(self, name: str, input_text: str, llm_manager = None) -> Any:
        """
        Execute a tool by name with the given input and LLM.
        
        Args:
            name: The tool name
            input_text: The input text for the tool
            llm_manager: Optional LLM manager to pass to tools that need it
            
        Returns:
            The result of the tool execution or an error message
        """
        tool_function = self.get_tool(name)
        
        if not tool_function:
            return f"Error: Tool '{name}' not found"
        
        try:
            # Check if the tool function accepts an llm parameter
            import inspect
            import os
            params = inspect.signature(tool_function).parameters
            
            # Special handling for SQL tools that need db_path
            if name in ["CcrSql", "FinancialSql"]:
                # Determine database paths directly
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                db_paths = {
                    "financial": os.path.join(project_root, "scripts", "data", "financial_data.db"),
                    "ccr": os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
                }
                
                # Get the appropriate db_path
                db_key = "ccr" if name == "CcrSql" else "financial"
                db_path = db_paths[db_key]
                
                if 'llm' in params and llm_manager:
                    # Pass both llm and db_path
                    return tool_function(input_text, llm=llm_manager.llm, db_path=db_path)
                else:
                    # Just pass db_path (unlikely but for completeness)
                    return tool_function(input_text, db_path=db_path)
            elif 'llm' in params and llm_manager:
                # Pass the LLM from the LLM manager if available (for non-SQL tools)
                return tool_function(input_text, llm=llm_manager.llm)
            else:
                # Just call with the input text
                return tool_function(input_text)
                
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error executing tool {name}: {str(e)}"
    
    def get_tool_profile(self, name: str) -> Dict[str, Any]:
        """
        Get a tool profile by name.
        
        Args:
            name: The tool name
            
        Returns:
            The tool profile or empty dict if not found
        """
        return self.profiles.get(name, {})
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """
        Get all registered tools.
        
        Returns:
            Dictionary mapping tool names to functions
        """
        return self.tools_map.copy()
    
    def get_tools_by_category(self, category: str, category_type: str = "functional") -> Dict[str, Dict[str, Any]]:
        """
        Get tools belonging to a specific category.
        
        Args:
            category: The category name
            category_type: The category type ('functional', 'department', etc.)
            
        Returns:
            Dictionary mapping tool names to their profiles
        """
        category_tools = {}
        
        for internal_name, profile in self.profiles.items():
            category_field = f"{category_type}_category"
            
            if category_field in profile and profile[category_field] == category:
                category_tools[internal_name] = profile
        
        return category_tools 