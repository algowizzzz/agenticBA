#!/usr/bin/env python3
"""
Sub-agent for Control Description Analysis.
Persona: Operational and non-financial risk experienced consultant, 
         reviewing controls within a tier 3 bank across enterprise risk.
"""
import logging
import os
from typing import Dict, Any, Optional, List

from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Configure logging
logger = logging.getLogger(__name__)
# Ensure a handler is configured for the logger, e.g., by adding a StreamHandler
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Or your desired level

# --- Prompts for Internal LLM Calls ---

FIVE_WS_ANALYSIS_PROMPT = """
As an experienced operational and non-financial risk consultant at a tier 3 bank, your task is to analyze the provided control description.
Thoroughly examine the control description and identify its coverage of the 5Ws:
- Who: Who is responsible for performing the control? (e.g., specific roles, departments)
- What: What specific actions are performed as part of the control? What is the control trying to achieve?
- When: When or how frequently is the control performed? (e.g., daily, monthly, continuously, upon event)
- Where: Where is the control performed or where does it apply? (e.g., specific systems, processes, locations)
- Why: Why is this control in place? What risk(s) is it mitigating?

Provide a clear, structured breakdown detailing the coverage for each 'W'. If a 'W' is not clearly covered, state that.

Control Description:
```
{control_description}
```

Your 5Ws Analysis:
"""

CONTROL_IMPROVEMENT_PROMPT = """
As an experienced operational and non-financial risk consultant at a tier 3 bank, you are given a control description and its 5Ws coverage analysis.
Your task is to:
1. Review the control description and the 5Ws analysis.
2. Identify any gaps, ambiguities, or areas for improvement in the control description based on the 5Ws and general control design best practices.
3. Suggest specific, actionable improvements to enhance the clarity, completeness, and effectiveness of the control.
4. You can either provide a list of suggested changes or, if appropriate, an improved version of the control description.
5. IMPORTANT: Do NOT change the core intent, context, or risk focus of the original control. Your goal is to make it a better-written control.
6. If the control description is already well-written and comprehensive based on the analysis, clearly state that and explain why significant improvements are not necessary.

Control Description:
```
{control_description}
```

5Ws Coverage Analysis:
```
{five_ws_analysis}
```

Your Suggestions for Improvement (or statement of adequacy):
"""

TEST_SCRIPT_GENERATION_PROMPT = """
As an experienced operational and non-financial risk consultant at a tier 3 bank, your task is to create a practical test script for the following control description.
The test script should enable an independent reviewer to assess the effectiveness of the control.

Include the following sections in your test script:
1.  **Control ID:** (Placeholder, e.g., CTRL-001)
2.  **Control Description:** (Quote the provided control description)
3.  **Control Objective:** (Infer from the description, what the control aims to achieve)
4.  **Test Objective:** What this test script aims to verify.
5.  **Test Steps for Design Effectiveness (DE):**
    *   Specific actions to verify the control is designed appropriately to meet its objective.
    *   (e.g., "Review policy document X to confirm procedure Y is documented.")
    *   (e.g., "Interview [Role Z] to confirm understanding of control steps.")
6.  **Test Steps for Operating Effectiveness (OE):**
    *   Specific actions to verify the control is operating as designed over a period.
    *   (e.g., "Select a sample of [N] instances of [event/transaction] between [date] and [date].")
    *   (e.g., "For each sample, obtain evidence of [control action] being performed by [Who].")
    *   (e.g., "Verify evidence aligns with the control description.")
7.  **Expected Outcome/Evidence:** What constitutes a successful test for each step or overall.
8.  **Pass/Fail Criteria:** Clear criteria for determining if the control passes or fails the test.

Control Description:
```
{control_description}
```

Your Generated Test Script:
"""

# --- Tool Implementation Functions ---

def _perform_5ws_analysis(control_description: str, llm: BaseChatModel) -> str:
    logger.info(f"[ControlAnalyzer] Performing 5Ws analysis for: '{control_description[:100]}...'")
    try:
        messages = [
            SystemMessage(content="You are an AI assistant specializing in control description analysis following specific instructions."),
            HumanMessage(content=FIVE_WS_ANALYSIS_PROMPT.format(control_description=control_description))
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Error in _perform_5ws_analysis: {e}", exc_info=True)
        return f"Error performing 5Ws analysis: {e}"

def _suggest_control_improvements(inputs_str: str, llm: BaseChatModel) -> str:
    logger.info(f"[ControlAnalyzer] Suggesting improvements based on: '{inputs_str[:100]}...'")
    # Expected inputs_str format: """Control Description: [text]
    # 5Ws Analysis: [text]"""
    try:
        # Basic parsing of the combined input string
        control_desc_marker = "Control Description:"
        five_ws_analysis_marker = "5Ws Analysis:"
        
        cd_start = inputs_str.find(control_desc_marker)
        analysis_start = inputs_str.find(five_ws_analysis_marker)

        if cd_start == -1 or analysis_start == -1:
            return "Error: Input for suggesting improvements is not correctly formatted. Expected 'Control Description: ...' and '5Ws Analysis: ...'."

        control_description = inputs_str[cd_start + len(control_desc_marker):analysis_start].strip()
        five_ws_analysis = inputs_str[analysis_start + len(five_ws_analysis_marker):].strip()

        if not control_description or not five_ws_analysis:
             return "Error: Missing control description or 5Ws analysis in the input for improvement suggestion."

        messages = [
            SystemMessage(content="You are an AI assistant specializing in control improvement suggestions following specific instructions."),
            HumanMessage(content=CONTROL_IMPROVEMENT_PROMPT.format(control_description=control_description, five_ws_analysis=five_ws_analysis))
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Error in _suggest_control_improvements: {e}", exc_info=True)
        return f"Error suggesting control improvements: {e}"

def _create_control_test_script(control_description: str, llm: BaseChatModel) -> str:
    logger.info(f"[ControlAnalyzer] Creating test script for: '{control_description[:100]}...'")
    try:
        messages = [
            SystemMessage(content="You are an AI assistant specializing in generating control test scripts following specific instructions."),
            HumanMessage(content=TEST_SCRIPT_GENERATION_PROMPT.format(control_description=control_description))
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"Error in _create_control_test_script: {e}", exc_info=True)
        return f"Error creating control test script: {e}"

# --- Main Agent Logic ---

REACT_PROMPT_TEMPLATE_CONTROL_ANALYZER = """
You are an experienced Operational and Non-Financial Risk consultant working within a tier 3 bank.
Your primary role is to analyze control descriptions provided by users. You have a suite of specialized tools to assist you.

TOOLS:
------
You have access to the following tools:
{{tools}}

To use a tool, please use the following format:

```
Thought: Do I need to use a tool? Yes
Action: The action to take. Should be one of [{{tool_names}}]
Action Input: The input to the action
Observation: The result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

```
Thought: Do I need to use a tool? No
Final Answer: [Your comprehensive response here. If performing full analysis, combine results from all tools.]
```

Your Task:
The user will provide a control description and may ask for a specific analysis or a "full analysis".

1.  **Understand the Request**: Determine if the user wants:
    *   A specific analysis (e.g., only "5Ws coverage", only "suggest improvements", only "create test script").
    *   A "full analysis", which means you should perform all three: 5Ws coverage, then suggest improvements, then create a test script.
    *   If the request is ambiguous, assume "full analysis".

2.  **Execute Tools Sequentially (if needed for full analysis or chained tasks)**:
    *   **5Ws Coverage**: If needed, use the "Analyze 5Ws Coverage" tool. Input is the control description.
    *   **Suggest Improvements**: If needed (and typically after 5Ws analysis), use the "Suggest Control Improvements" tool.
        *   **IMPORTANT Action Input Formatting for "Suggest Control Improvements"**: The input MUST be a single string formatted exactly as:
            `Control Description: [The full control description text]\n5Ws Analysis: [The full output from the 'Analyze 5Ws Coverage' tool]`
    *   **Create Test Script**: If needed, use the "Create Control Test Script" tool. Input is the control description.

3.  **Synthesize and Respond**:
    *   If a specific analysis was requested, provide the result from that tool.
    *   If "full analysis" was performed, combine the outputs from all tools into a single, coherent "Final Answer". Clearly label each section (5Ws Analysis, Suggested Improvements, Test Script).

User Query Structure:
The user's query will typically contain the control description. It might look like:
- "Analyze 5Ws coverage for control: [description]"
- "Suggest improvements for control: [description] based on this 5Ws analysis: [5Ws text]" (though you'll usually do 5Ws first yourself)
- "Create test script for control: [description]"
- "Full analysis of control: [description]"
- Or simply "Review this control: [description]" (assume full analysis)

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}
"""

def run_control_analyzer_agent(
    query: str,
    llm: BaseChatModel,
    api_key: Optional[str] = None # Included for consistency, though LLM is passed in
) -> str:
    """
    Runs the specialized control description analysis agent.
    """
    logger.info(f"[ControlAnalyzerAgent] Initializing for query: '{query[:100]}...'")

    # Define tools for the internal agent
    tools = [
        Tool(
            name="Analyze 5Ws Coverage",
            func=lambda cd: _perform_5ws_analysis(cd, llm),
            description="Identifies When, What, Who, Why, Where coverage in a control description. Input: control description."
        ),
        Tool(
            name="Suggest Control Improvements",
            func=lambda inputs_str: _suggest_control_improvements(inputs_str, llm),
            description="Suggests improvements to a control description based on its 5Ws analysis. Input: A single string formatted as 'Control Description: [text]\n5Ws Analysis: [text]'."
        ),
        Tool(
            name="Create Control Test Script",
            func=lambda cd: _create_control_test_script(cd, llm),
            description="Creates a test script for testing a control description, including Design and Operating Effectiveness. Input: control description."
        ),
    ]

    try:
        # Create the ReAct prompt
        prompt = PromptTemplate(
            template=REACT_PROMPT_TEMPLATE_CONTROL_ANALYZER,
            input_variables=["input", "agent_scratchpad", "chat_history"],
            partial_variables={"tools": "", "tool_names": ""} # Will be populated by AgentExecutor
        )

        # Create the ReAct agent
        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

        # Create an AgentExecutor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors="Check your output and make sure it conforms to the thought/action/observation ReAct format.",
            max_iterations=10 # Increased to allow for multi-step "full analysis"
        )

        logger.info("[ControlAnalyzerAgent] Executing internal agent...")
        # The input to the agent_executor should be a dictionary.
        # The 'input' key will be formatted into the prompt template.
        # 'chat_history' can be added if we want to maintain conversation state within the sub-agent.
        response = agent_executor.invoke({"input": query, "chat_history": ""})
        
        final_answer = response.get("output", "No output from agent.")
        logger.info(f"[ControlAnalyzerAgent] Execution finished. Output: '{final_answer[:200]}...'")
        return final_answer

    except Exception as e:
        logger.error(f"[ControlAnalyzerAgent] Error during execution: {e}", exc_info=True)
        return f"Error in Control Description Analyzer: {str(e)}"

if __name__ == '__main__':
    # This is a placeholder for testing the sub-agent directly.
    # In a real scenario, BasicAgent would provide the LLM.
    # For local testing, you'd need to instantiate an LLM, e.g., ChatAnthropic.
    
    print("Control Analysis Sub-Agent - Direct Test (Requires LLM setup)")
    
    # Example LLM setup (replace with your actual LLM initialization if testing)
    # try:
    #     from langchain_anthropic import ChatAnthropic
    #     # Ensure ANTHROPIC_API_KEY is set in your environment
    #     test_llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)
    #     logger.info("Test LLM initialized.")
    # except ImportError:
    #     logger.error("ChatAnthropic not installed. pip install langchain-anthropic")
    #     test_llm = None
    # except Exception as e:
    #     logger.error(f"Could not initialize LLM: {e}")
    #     test_llm = None

    # if test_llm:
    #     test_control_description_1 = "The finance manager reconciles the cash account with bank statements on a monthly basis to ensure all transactions are recorded accurately and discrepancies are investigated."
    #     test_query_1 = f"Full analysis of control: {test_control_description_1}"
        
    #     test_control_description_2 = "Access to the production server is restricted."
    #     test_query_2 = f"Analyze 5Ws coverage for control: {test_control_description_2}"

    #     test_control_description_3 = "User access reviews are performed quarterly by system owners."
    #     test_query_3 = f"Create test script for control: {test_control_description_3}"

    #     print(f"\n--- Running Test Query 1 (Full Analysis) ---")
    #     output1 = run_control_analyzer_agent(query=test_query_1, llm=test_llm)
    #     print("\nControl Analyzer Agent Output (Test 1):")
    #     print(output1)

    #     # print(f"\n--- Running Test Query 2 (5Ws Only) ---")
    #     # output2 = run_control_analyzer_agent(query=test_query_2, llm=test_llm)
    #     # print("\nControl Analyzer Agent Output (Test 2):")
    #     # print(output2)

    #     # print(f"\n--- Running Test Query 3 (Test Script Only) ---")
    #     # output3 = run_control_analyzer_agent(query=test_query_3, llm=test_llm)
    #     # print("\nControl Analyzer Agent Output (Test 3):")
    #     # print(output3)
    # else:
    #     # print("Skipping direct tests as LLM is not available or not set up in this stub.")
    #     pass 