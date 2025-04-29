import logging
from typing import Dict, Any, List, Optional

from langchain.chains import LLMChain
from langchain.agents import Tool

from stages.greeting import greet_user
from stages.guardrails import run_guardrails_check
from stages.planning import generate_plan
from stages.execution import run_execution
from stages.reasoning import run_reasoning
from stages.final_output import generate_final_answer
# Import other stage functions as they are built

logger = logging.getLogger(__name__)

MAX_REPLAN_ATTEMPTS = 2

def confirm_plan(planning_chain: LLMChain, 
                 confirmation_chain: LLMChain,
                 tools: List[Tool], 
                 original_query: str, 
                 plan_text: str) -> Optional[str]:
    """
    Presents the plan, uses an LLM to classify user's natural language response,
    and handles confirmation, cancellation, or re-planning.
    """
    current_query = original_query
    attempts = 0

    while attempts <= MAX_REPLAN_ATTEMPTS:
        print("\nProposed Plan:")
        print(plan_text)

        # Handle errors from plan generation first
        if plan_text.startswith("ERROR:") or "cannot be answered" in plan_text.lower():
            print("\nThis query might not be answerable or an error occurred during planning.")
            # Ask for rephrase/cancel (simpler interaction here)
            confirm = input("Would you like to rephrase or cancel? (rephrase/cancel): ").strip().lower()
            if confirm == "cancel":
                logger.warning("User cancelled due to planning failure.")
                return None
            else:
                current_query = input("Please provide your rephrased query: ").strip()
                if not current_query:
                    logger.warning("User provided empty rephrased query, cancelling.")
                    return None
                attempts = 0 # Reset attempts for new query
                # Regenerate plan using the planning stage function
                from stages.planning import generate_plan # Local import okay here
                plan_text = generate_plan(planning_chain, tools, current_query)
                continue # Go back to presenting the new plan

        # Get user confirmation/feedback in natural language
        user_response = input("\nDoes this plan look correct, or do you have any modifications? ").strip()
        if not user_response:
            print("No response received. Please provide input.")
            continue

        # Classify the user's response
        try:
            classification_result = confirmation_chain.run(user_response=user_response)
            classification = classification_result.strip().upper()
            logger.info(f"User plan response: '{user_response}'. Classification: {classification}")
        except Exception as e:
            logger.error(f"Error classifying user confirmation: {e}", exc_info=True)
            print("Sorry, I had trouble understanding your response. Please try again (e.g., 'yes', 'no', 'cancel', 'modify: [your feedback]').")
            continue

        # Act based on classification
        if classification == "APPROVE":
            logger.info("Plan approved by user.")
            return plan_text
        elif classification == "REJECT":
            logger.info("Plan rejected or cancelled by user.")
            print("Okay, cancelling plan execution.")
            return None
        elif classification == "MODIFY":
            attempts += 1
            if attempts > MAX_REPLAN_ATTEMPTS:
                print(f"Maximum re-planning attempts ({MAX_REPLAN_ATTEMPTS}) reached. Cancelling.")
                logger.warning("Maximum re-planning attempts reached.")
                return None

            # Use the full user response as feedback for re-planning
            user_feedback = user_response 
            current_query = f"{original_query}\nUser feedback on previous plan: {user_feedback}"
            logger.info(f"Re-planning attempt {attempts} with feedback: {user_feedback[:50]}...")
            
            from stages.planning import generate_plan # Local import okay here
            plan_text = generate_plan(planning_chain, tools, current_query)
            # Loop will continue and present the new plan
        else: # Unclear classification
            logger.warning(f"Could not confidently classify user response: '{user_response}' -> {classification}")
            print("Sorry, I didn't quite understand that. Please try phrasing your response clearly (e.g., 'Yes, proceed', 'No, cancel', or explain the changes you want).")
            # Let user try again without counting as re-plan attempt

    # If loop exits due to attempts
    logger.warning("Maximum re-planning attempts reached during confirmation.")
    return None

def run_agent_loop(components: Dict[str, Any]):
    """
    Runs the main interactive loop for the agent.

    Args:
        components (Dict[str, Any]): A dictionary containing initialized agent components
                                      (tools, chains, etc.).
    """
    greet_user()

    tools = components["tools"]
    guardrails_chain = components["guardrails_chain"]
    planning_chain = components["planning_chain"]
    confirmation_chain = components["confirmation_chain"]
    execution_agent = components["execution_component"]
    reasoning_chain = components["reasoning_chain"]
    final_output_chain = components["final_output_chain"]

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                logger.info("User requested exit.")
                break

            logger.info(f"Received query: {user_input}")

            # --- Stage 1: Guardrails ---
            allowed, reason = run_guardrails_check(guardrails_chain, user_input)
            if not allowed:
                print(f"Request blocked: {reason}")
                continue

            logger.info("Guardrails passed.")

            # --- Stage 2: Planning ---
            plan_text = generate_plan(planning_chain, tools, user_input)

            # --- Stage 3: Plan Confirmation ---
            confirmed_plan = confirm_plan(
                planning_chain,
                confirmation_chain,
                tools,
                user_input,
                plan_text
            )

            if not confirmed_plan:
                print("Restarting query process. Please enter a new query or type exit.")
                continue # User cancelled or failed to confirm

            logger.info("Plan confirmed.")
            # --- Stage 4: Execution ---
            logger.info("Executing plan...")
            print("\n--- Executing Plan --- (Agent logs below if verbose=True) ---")
            execution_results = run_execution(execution_agent, confirmed_plan, user_input)

            # Handle potential errors from execution
            if 'error' in execution_results:
                logger.error(f"Execution failed: {execution_results['error']}")
                print(f"\nError during execution: {execution_results['error']}")
                print("Please try rephrasing your query or contact support.")
                continue # Go to next query iteration

            logger.info("Execution finished successfully.")
            # Display intermediate steps if needed for debugging (optional)
            # logger.debug(f"Intermediate steps: {execution_results.get('intermediate_steps')}")

            # --- Stage 5: Reasoning ---
            logger.info("Reasoning about results...")
            print("\n--- Reasoning --- (Processing execution results) ---")
            # Call the run_reasoning function
            reasoning_output = run_reasoning(reasoning_chain, user_input, execution_results)

            # Handle potential errors from reasoning
            if reasoning_output.startswith("ERROR:"):
                logger.error(f"Reasoning failed: {reasoning_output}")
                print(f"\nError during reasoning: {reasoning_output}")
                print("Could not synthesize results. Please try again or contact support.")
                continue # Go to next query iteration

            logger.info("Reasoning finished successfully.")
            # Display reasoning output for debugging (optional)
            # logger.debug(f"Reasoning output:\n{reasoning_output}")

            # --- Stage 6: Final Output ---
            logger.info("Generating final answer...")
            print("\n--- Final Answer --- ")
            # Call the generate_final_answer function
            final_answer = generate_final_answer(final_output_chain, user_input, reasoning_output)

            # Print the final answer to the user
            print(final_answer)
            logger.info("Final answer provided.")

        except Exception as e:
            logger.error(f"An error occurred during the agent loop: {e}", exc_info=True)
            print("\nAn unexpected error occurred. Please try again or type 'exit'.")
            # Decide whether to break or continue on error
            # continue
