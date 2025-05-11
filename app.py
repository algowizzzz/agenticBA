#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from basic_agent import BasicAgent
from langchain.schema import SystemMessage, HumanMessage
import logging
import os
import re

# Import OpenAI specific modules
from langchain_openai import ChatOpenAI
import anthropic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize our agent (only done once when server starts)
try:
    agent = BasicAgent()
    logger.info("BasicAgent initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize BasicAgent: {e}")
    agent = None

# Dictionary to store plans by session ID
active_plans = {}

# Initialize OpenAI backup LLM
openai_api_key = os.environ.get("OPENAI_API_KEY", "")
try:
    backup_llm = ChatOpenAI(model_name="gpt-4o", temperature=0, api_key=openai_api_key)
    logger.info("OpenAI GPT-4o backup LLM initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI backup LLM: {e}")
    backup_llm = None

def get_working_llm():
    """Returns a working LLM - either the primary one from the agent or the backup OpenAI one"""
    # Try the agent's primary LLM first
    if agent and agent.llm:
        try:
            # Simple test to see if the LLM is working
            test_messages = [SystemMessage(content="You are a helpful assistant."), 
                           HumanMessage(content="Say 'working' if you can see this.")]
            response = agent.llm.invoke(test_messages)
            if response and 'working' in response.content.lower():
                logger.info("Primary LLM (Claude) is working.")
                return agent.llm
        except Exception as e:
            logger.warning(f"Primary LLM test failed: {e}")
    
    # Fall back to OpenAI if available
    if backup_llm:
        try:
            # Simple test to see if the backup LLM is working
            test_messages = [SystemMessage(content="You are a helpful assistant."), 
                           HumanMessage(content="Say 'working' if you can see this.")]
            response = backup_llm.invoke(test_messages)
            if response and 'working' in response.content.lower():
                logger.info("Backup LLM (OpenAI) is working.")
                return backup_llm
        except Exception as e:
            logger.warning(f"Backup LLM test failed: {e}")
    
    logger.error("No working LLM found.")
    return None

def provide_fallback_response(query, execution_results=None):
    """Provides a generic helpful response when APIs are unavailable"""
    topic_patterns = {
        "stock price": "To find historical stock prices, you can check financial websites like Yahoo Finance or Google Finance. For real-time data, you might need a market data subscription.",
        "earnings": "Earnings information can be found in a company's quarterly reports, which are typically published on their investor relations website. Financial data providers like Bloomberg, FactSet, or S&P Capital IQ also aggregate this data.",
        "financials": "Company financial information is available through their SEC filings (10-K, 10-Q reports) on the SEC EDGAR database, or through financial data providers.",
        "revenue": "Revenue figures are typically reported in a company's income statement, which can be found in their quarterly and annual reports.",
        "growth": "Growth metrics like year-over-year revenue growth or earnings growth are calculated from financial statements. Many financial websites also provide these calculations.",
        "news": "For the latest financial news, consider checking Bloomberg, CNBC, Financial Times, Wall Street Journal, or industry-specific publications.",
        "trends": "Industry trends can be identified through market research reports, news analyses, and company earnings calls where management often discusses market conditions.",
        "microsoft": "Microsoft financial information is available through their investor relations website: https://www.microsoft.com/en-us/investor/",
        "apple": "Apple financial information is available through their investor relations website: https://investor.apple.com/",
        "nvidia": "NVIDIA financial information is available through their investor relations website: https://investor.nvidia.com/",
        "amazon": "Amazon financial information is available through their investor relations website: https://ir.aboutamazon.com/",
        "google": "Alphabet (Google) financial information is available through their investor relations website: https://abc.xyz/investor/",
        "ai": "AI industry information can be found through research firms like Gartner, IDC, or through company-specific announcements and earnings calls.",
        "cloud": "Cloud computing market data is available through research firms like Gartner, IDC, and Forrester, as well as company-specific disclosures in earnings reports."
    }
    
    # Base response acknowledging the API issue and explicitly stating we're using general knowledge
    base_response = "NOTICE: I could not retrieve specific data from the databases for your query. The following response is based on general knowledge rather than actual database lookups.\n\nI apologize, but I'm currently experiencing connection issues with my data sources. However, I can still provide some general guidance."
    
    # Detect which topics might be present in the query
    relevant_topics = []
    query_lower = query.lower()
    for pattern, info in topic_patterns.items():
        if pattern.lower() in query_lower:
            relevant_topics.append(info)
    
    # If no specific topics were matched, provide a general response
    if not relevant_topics:
        relevant_topics.append("For financial and business data, good sources include company investor relations websites, SEC EDGAR database, financial news publications, and data providers like Bloomberg or S&P Capital IQ.")
    
    # Combine the base response with helpful information about detected topics
    full_response = f"{base_response}\n\n"
    
    if len(relevant_topics) > 1:
        full_response += "Based on your query, here are some helpful resources:\n\n"
        for i, topic in enumerate(relevant_topics, 1):
            full_response += f"{i}. {topic}\n"
    else:
        full_response += f"{relevant_topics[0]}"
    
    return full_response

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/test')
def test():
    """Serve the test HTML page"""
    return send_from_directory('.', 'test.html')

@app.route('/api/generate-plan', methods=['POST'])
def generate_plan():
    """Generate a plan for a given query"""
    if agent is None:
        return jsonify({
            "error": "Agent not initialized. Check server logs for details.",
            "message": "Sorry, the system is currently unavailable. Please try again later."
        }), 500

    try:
        # Get query from request
        data = request.json
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' in request",
                "message": "Sorry, I couldn't understand your request. Please try again."
            }), 400

        query = data['query']
        logger.info(f"Received query for plan generation: {query}")
        
        # Get a working LLM
        working_llm = get_working_llm()
        if not working_llm:
            # Generate a helpful fallback response when no LLM is available
            fallback_response = provide_fallback_response(query)
            return jsonify({
                "error": "No working LLM available.",
                "message": fallback_response
            }), 200  # Return 200 with helpful content, not 500
        
        # Try to generate a plan
        try:
            # Generate plan using BasicAgent's internal methods
            modified_query = agent._guardrail_check(query, override_llm=working_llm).get('query', query)
            plan = agent._generate_plan(modified_query, override_llm=working_llm)
        except anthropic.BadRequestError as e:
            # Check if it's a credit/billing issue with Anthropic
            if "credit balance is too low" in str(e) or "billing" in str(e).lower():
                logger.warning("Anthropic API credit issue detected. Using backup plan generation.")
                # Simple backup plan - use an LLM directly to generate a basic plan
                system_prompt = """You are an AI assistant tasked with creating a simple research plan.
Format your response as a plan with steps using the following format:

Tool: [Tool Name]
Input: [Input for the tool]

Tool: [Tool Name]
Input: [Input for the tool]

Available tools: EarningsCallSummary, FinancialNewsSearch, FinancialSQL, CCRSQL
Choose tools that would help answer the user's query."""
                
                human_prompt = f"Create a simple research plan to answer this question: {query}"
                
                try:
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=human_prompt)
                    ]
                    response = working_llm.invoke(messages)
                    plan = response.content.strip()
                except Exception as inner_e:
                    logger.error(f"Backup plan generation failed: {inner_e}")
                    # Generate a helpful fallback response
                    fallback_response = provide_fallback_response(query)
                    return jsonify({
                        "error": "API connection issues.",
                        "message": fallback_response
                    }), 200  # Return 200 with helpful content
            else:
                # Some other API error
                logger.error(f"API error during plan generation: {e}")
                fallback_response = provide_fallback_response(query)
                return jsonify({
                    "error": str(e),
                    "message": fallback_response
                }), 200
        
        # Generate a session ID
        session_id = os.urandom(8).hex()
        
        # Store the plan and query for later execution
        active_plans[session_id] = {
            'query': modified_query if 'modified_query' in locals() else query,
            'plan': plan
        }
        
        # Extract the steps from the plan for better UI display
        steps = []
        lines = plan.strip().split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith("Tool:"):
                tool = lines[i].replace("Tool:", "").strip()
                i += 1
                if i < len(lines) and lines[i].startswith("Input:"):
                    input_text = lines[i].replace("Input:", "").strip()
                    steps.append({"tool": tool, "input": input_text})
                i += 1
            else:
                i += 1
        
        return jsonify({
            "session_id": session_id,
            "plan": plan,
            "steps": steps,
            "message": "Please confirm if you want to proceed with this plan."
        })

    except Exception as e:
        logger.error(f"Error generating plan: {e}", exc_info=True)
        # Provide a helpful fallback response
        fallback_response = provide_fallback_response(query if 'query' in locals() else "your question")
        return jsonify({
            "error": str(e),
            "message": fallback_response
        }), 200

@app.route('/api/execute-plan', methods=['POST'])
def execute_plan():
    """Execute a previously generated plan"""
    if agent is None:
        return jsonify({
            "error": "Agent not initialized. Check server logs for details.",
            "message": "Sorry, the system is currently unavailable. Please try again later."
        }), 500

    try:
        # Get session ID from request
        data = request.json
        if not data or 'session_id' not in data:
            return jsonify({
                "error": "Missing 'session_id' in request",
                "message": "Sorry, I couldn't find the plan to execute. Please try again."
            }), 400

        session_id = data['session_id']
        logger.info(f"Executing plan for session: {session_id}")
        
        # Retrieve stored plan and query
        if session_id not in active_plans:
            return jsonify({
                "error": "Invalid or expired session ID",
                "message": "Sorry, I couldn't find the plan to execute. It might have expired. Please try again."
            }), 400
            
        plan_data = active_plans[session_id]
        query = plan_data['query']
        plan = plan_data['plan']
        
        # Get a working LLM for possible use in synthesis
        working_llm = get_working_llm()
        if not working_llm:
            # Generate a helpful fallback response when no LLM is available
            fallback_response = provide_fallback_response(query)
            
            # Clean up - remove the plan from storage
            del active_plans[session_id]
            
            return jsonify({
                "response": fallback_response,
                "thinking_steps": ["Detected API connection issues and provided general guidance."]
            }), 200
        
        # Execute the plan
        try:
            execution_results = agent._execute_plan(plan)
        except Exception as exec_e:
            logger.error(f"Plan execution error: {exec_e}")
            if "credit balance is too low" in str(exec_e) or "billing" in str(exec_e).lower() or "authentication_error" in str(exec_e).lower() or "overloaded_error" in str(exec_e).lower():
                # API credit/auth/overloaded issue, provide fallback
                fallback_response = provide_fallback_response(query)
                
                # Clean up - remove the plan from storage
                del active_plans[session_id]
                
                return jsonify({
                    "response": fallback_response,
                    "thinking_steps": ["Detected API connection issues during execution and provided general guidance."]
                }), 200
            else:
                # Re-raise for general error handling
                raise exec_e
        
        # Extract thinking steps from execution results
        thinking_steps = []
        for key, result in execution_results.items():
            if isinstance(result, str) and "Thought:" in result:
                # Extract all thoughts from the result
                thoughts = re.findall(r'Thought:(.*?)(?=Action:|Final Answer:|$)', result, re.DOTALL)
                for thought in thoughts:
                    thinking_steps.append(thought.strip())
        
        # Summarize thinking steps if there are more than 3
        thinking_summary = ""
        if thinking_steps:
            if len(thinking_steps) > 3:
                thinking_summary = "# My Reasoning Process\n\n"
                thinking_summary += "Here's a summary of my thought process while addressing your question:\n\n"
                for i, step in enumerate(thinking_steps[:3], 1):
                    thinking_summary += f"{i}. {step}\n\n"
                thinking_summary += f"...and {len(thinking_steps) - 3} more steps.\n\n"
            else:
                thinking_summary = "# My Reasoning Process\n\n"
                thinking_summary += "Here's my thought process while addressing your question:\n\n"
                for i, step in enumerate(thinking_steps, 1):
                    thinking_summary += f"{i}. {step}\n\n"
        
        # Custom synthesis that focuses on being helpful with whatever information is available
        try:
            # First try using the agent's built-in synthesizer
            response = agent._synthesize_answer(query, execution_results, override_llm=working_llm)
            
            # Check if the response is essentially saying "I don't have enough information"
            unhelpful_patterns = [
                "I cannot provide", 
                "I don't have enough information",
                "I apologize, but I cannot",
                "does not contain",
                "The available context is limited",
                "cannot offer a reliable",
                "would be necessary to consult more recent sources"
            ]
            
            is_unhelpful = any(pattern in response for pattern in unhelpful_patterns)
            
            if is_unhelpful:
                # Create a more helpful response using whatever information we have
                logger.info("Detected unhelpful response, generating more helpful alternative...")
                
                # Extract any useful information from execution results
                useful_info = []
                for key, result in execution_results.items():
                    if result and isinstance(result, str) and len(result) > 50:
                        useful_info.append(result)
                
                if useful_info:
                    # Use a more direct prompt to generate a helpful response
                    system_prompt = """You are a helpful AI assistant providing business analysis. 
Your task is to synthesize the information provided to answer the user's question.
Important guidelines:
1. Focus on what you CAN say based on the available information, not what you don't know
2. Be honest but prioritize providing value to the user
3. If information is limited or somewhat outdated, still provide the best insights possible
4. Use phrases like "Based on the available information..." rather than apologizing
5. Be concise and direct
6. Don't focus on the limitations of the data unless absolutely necessary
7. Format your response in a clear, structured way using markdown:
   - Use # for main headings
   - Use ## for subheadings
   - Use bullet points (- or *) for lists
   - Use numbered lists (1., 2., etc.) for sequential information
   - Use **bold** for emphasis on key points
   - Separate paragraphs with blank lines"""
                    
                    human_prompt = f"""Question: {query}

Available information:
{' '.join(useful_info)}

Please provide the most helpful answer possible based on this information, even if it's limited or not completely up-to-date."""
                    
                    # Use the working LLM
                    try:
                        messages_obj = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=human_prompt)
                        ]
                        llm_response = working_llm.invoke(messages_obj)
                        response = llm_response.content.strip()
                        logger.info("Generated more helpful response successfully")
                    except Exception as e:
                        logger.error(f"Error generating helpful response: {e}", exc_info=True)
                        # Fall back to original response if error occurs
                
        except Exception as e:
            logger.error(f"Error in custom synthesis: {e}", exc_info=True)
            # Check if it's an API credit/authentication/overloaded issue
            if "credit balance is too low" in str(e) or "billing" in str(e).lower() or "authentication_error" in str(e).lower() or "overloaded_error" in str(e).lower():
                # Generate a helpful fallback response based on query content
                response = provide_fallback_response(query, execution_results)
            else:
                # Try direct synthesis with working LLM as fallback
                try:
                    system_prompt = """You are a helpful AI assistant providing business analysis. 
Synthesize the available information to provide the best answer to the user's question.
Be honest but focus on what you CAN provide based on the limited information available."""
                    
                    human_prompt = f"""Question: {query}

Available information from tools:
{execution_results}

Please provide a helpful answer based on this information."""
                    
                    messages_obj = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=human_prompt)
                    ]
                    llm_response = working_llm.invoke(messages_obj)
                    response = llm_response.content.strip()
                except Exception as fallback_e:
                    logger.error(f"Fallback synthesis also failed: {fallback_e}", exc_info=True)
                    # Final fallback to static response
                    response = provide_fallback_response(query, execution_results)
        
        # Append thinking summary to response if available
        if thinking_summary:
            response = response + "\n\n" + thinking_summary
        
        # Clean up - remove the plan from storage
        del active_plans[session_id]
        
        return jsonify({
            "response": response,
            "thinking_steps": thinking_steps
        })

    except Exception as e:
        logger.error(f"Error executing plan: {e}", exc_info=True)
        query = active_plans.get(session_id, {}).get('query', 'your question') if 'session_id' in locals() and session_id in active_plans else 'your question'
        
        # Clean up if possible
        if 'session_id' in locals() and session_id in active_plans:
            del active_plans[session_id]
        
        # Check if it's a service overload error
        if "overloaded_error" in str(e):
            fallback_response = f"I apologize, but the AI service is currently experiencing high demand and is temporarily overloaded. Here's some general guidance for your query about {query}:\n\n" + provide_fallback_response(query)
        else:
            # Provide a helpful fallback response
            fallback_response = provide_fallback_response(query)
            
        return jsonify({
            "error": str(e),
            "response": fallback_response,
            "thinking_steps": ["Encountered an error and provided general guidance."]
        }), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    """Original chat endpoint (for backward compatibility)"""
    if agent is None:
        return jsonify({
            "error": "Agent not initialized. Check server logs for details.",
            "response": "Sorry, the system is currently unavailable. Please try again later."
        }), 500

    try:
        # Get query from request
        data = request.json
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing 'query' in request",
                "response": "Sorry, I couldn't understand your request. Please try again."
            }), 400

        query = data['query']
        logger.info(f"Received query: {query}")

        # Get a working LLM
        working_llm = get_working_llm()
        if not working_llm:
            return jsonify({
                "error": "No working LLM available.",
                "response": "Sorry, I'm having trouble connecting to my language models. Please try again later."
            }), 500

        try:
            # Process query with agent
            response = agent.run(query, override_llm=working_llm)
        except Exception as agent_e:
            logger.error(f"Agent run failed: {agent_e}", exc_info=True)
            # Fall back to direct LLM response
            system_prompt = """You are a helpful business analysis assistant. 
            Provide a concise and helpful response to the user's query. 
            If you don't know the specific answer, provide general information that might be helpful."""
            
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=query)
                ]
                llm_response = working_llm.invoke(messages)
                response = llm_response.content.strip()
            except Exception as llm_e:
                logger.error(f"Fallback LLM call also failed: {llm_e}", exc_info=True)
                response = "I apologize, but I'm experiencing technical difficulties and cannot properly process your request right now. Please try again later."
        
        return jsonify({
            "response": response
        })

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "response": "Sorry, I encountered an error while processing your request. Please try again."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    debug = os.environ.get('FLASK_ENV') == 'development'
    logger.info(f"Starting server on port {port}, debug mode: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug) 