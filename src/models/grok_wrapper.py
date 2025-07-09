# src/models/grok_wrapper.py
import os
from src.utils.caching import get_groq_client

# Initialize the client once using the cached function
client = get_groq_client()

def call_grok_api(prompt):
    """
    Call Grok LLM via the official Python client and return generated text.
    """
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "You are an assistant helping to generate exams."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        # Log the error or handle it as needed
        print(f"An error occurred with the Groq API call: {e}")
        # Reraise the exception or return a user-friendly error message
        raise Exception(f"Grok API error: {e}")