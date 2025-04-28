import os
import anthropic

# Use the provided API key
api_key = "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"
client = anthropic.Anthropic(api_key=api_key)

try:
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print(response)
    print("Success!")
except Exception as e:
    print(f"Error: {e}") 
import anthropic

# Use the provided API key
api_key = "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"
client = anthropic.Anthropic(api_key=api_key)

try:
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print(response)
    print("Success!")
except Exception as e:
    print(f"Error: {e}") 
 
 