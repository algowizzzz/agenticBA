import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv() # Re-enable .env loading

api_key = os.getenv("ANTHROPIC_API_KEY") # Re-enable os.getenv

# api_key = "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"
# print("Using hardcoded API key for this test.") # Remove hardcoding

if not api_key:
    print("ERROR: ANTHROPIC_API_KEY not found in environment variables.")
else:
    print(f"Found API key starting with: {api_key[:15]}...") # Print first 15 chars for confirmation
    try:
        llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0, anthropic_api_key=api_key)
        print("ChatAnthropic client initialized successfully.")
        
        messages = [HumanMessage(content="Hello, this is a test.")]
        print("Attempting to invoke LLM...")
        response = llm.invoke(messages)
        
        print("LLM invoked successfully!")
        print(f"Response: {response.content}")
        
    except Exception as e:
        print(f"ERROR during Anthropic API call: {e}")
        print("Details:")
        import traceback
        traceback.print_exc() 