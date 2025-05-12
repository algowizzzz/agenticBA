#!/usr/bin/env python3
"""
Enhanced thinking steps tracker for RiskGPT agent system.
Provides categorized tracking and more detailed narrative output.
"""

import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("riskgpt")

class EnhancedThinkingStepTracker:
    """Enhanced version of ThinkingStepTracker with categorization and detailed insights."""
    
    def __init__(self):
        """Initialize thinking step categories and storage."""
        # Store steps as (category, step_text) tuples for chronological tracking
        self.steps: List[Tuple[str, str]] = []
        
        # Categorized steps for sectional reporting
        self.categories: Dict[str, List[str]] = {
            "objective": [],  # Understanding user's core objective
            "planning": [],   # Planning and tool selection decisions
            "tools": [],      # Tool execution details
            "data": [],       # Data findings and insights
            "synthesis": [],  # Analysis and combining results
            "error": []       # Error handling
        }
    
    def add_step(self, step: str, category: str = "general") -> None:
        """
        Add a thinking step with category.
        
        Args:
            step: The thinking step text
            category: Category of the step (objective, planning, tools, data, synthesis, error)
        """
        logger.info(f"[Thinking:{category.capitalize()}] {step}")
        self.steps.append((category, step))
        
        # Store in the appropriate category
        if category in self.categories:
            self.categories[category].append(step)
        else:
            # Default to general category if not recognized
            if "general" not in self.categories:
                self.categories["general"] = []
            self.categories["general"].append(step)
    
    def add_objective_understanding(self, insight: str) -> None:
        """
        Add insight about user's core objective.
        
        Args:
            insight: Understanding about the user's core objective
        """
        self.add_step(f"Core objective: {insight}", "objective")
    
    def add_tool_selection(self, tool: str, reason: str) -> None:
        """
        Add reasoning about tool selection.
        
        Args:
            tool: Name of the selected tool
            reason: Reason for selecting this tool
        """
        self.add_step(f"Selected {tool} because {reason}", "planning")
    
    def add_data_insight(self, tool: str, found: bool, data_type: str, details: str = "") -> None:
        """
        Add insight about data findings.
        
        Args:
            tool: Tool that produced the data
            found: Whether data was found
            data_type: Type of data that was sought
            details: Additional details about the data
        """
        status = "✓ Found" if found else "✗ Could not find"
        message = f"{status} {data_type} using {tool}"
        if details:
            message += f": {details}"
        self.add_step(message, "data")
    
    def get_formatted_steps(self) -> str:
        """
        Generate formatted narrative of the agent's thinking process.
        
        Returns:
            Formatted string with sections for different aspects of thinking
        """
        sections = ["# Agent Thinking Process\n"]
        
        # Add main chronological narrative
        sections.append("## Step-by-Step Reasoning\n")
        for category, step in self.steps:
            # Add an icon/emoji based on the category for visual distinction
            icon = self._get_category_icon(category)
            sections.append(f"- {icon} {step}")
        
        # Add objective understanding if present
        if self.categories["objective"]:
            sections.append("\n## Understanding Your Core Objective\n")
            for step in self.categories["objective"]:
                sections.append(f"- 🎯 {step}")
        
        # Add data findings if present
        if self.categories["data"]:
            sections.append("\n## Data Discoveries\n")
            for step in self.categories["data"]:
                sections.append(f"- 📊 {step}")
        
        # Add tools used if present
        if self.categories["tools"]:
            sections.append("\n## Tools Used\n")
            for step in self.categories["tools"]:
                sections.append(f"- 🔧 {step}")
        
        # Add errors if present
        if self.categories["error"]:
            sections.append("\n## Issues Encountered\n")
            for step in self.categories["error"]:
                sections.append(f"- ⚠️ {step}")
        
        return "\n".join(sections)
    
    def _get_category_icon(self, category: str) -> str:
        """Get an icon for a category."""
        icons = {
            "objective": "🎯",
            "planning": "🧠",
            "tools": "🔧",
            "data": "📊",
            "synthesis": "🧩",
            "error": "⚠️",
            "general": "💭"
        }
        return icons.get(category, "💭")
    
    def clear(self) -> None:
        """Clear all thinking steps."""
        self.steps = []
        for category in self.categories:
            self.categories[category] = []
