import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key or api_key == "your_gemini_key_here":
    print("Error: Valid GOOGLE_API_KEY not found in .env file.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

headers = {
    "Content-Type": "application/json"
}

data = {
    "contents": [{
        "parts":[{
            "text": "Write a short 1-sentence tagline for a tool called ResumeForge."
        }]
    }]
}

print("Testing Gemini API...")
try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    print("\nSUCCESS! API Key is working! Here is the response:")
    print("-" * 50)
    print(result["candidates"][0]["content"]["parts"][0]["text"].strip())
    print("-" * 50)
except requests.exceptions.HTTPError as e:
    print(f"\nAPI Error: {e}")
    print(f"Response details: {response.text}")
except Exception as e:
    print(f"\nError: {e}")
