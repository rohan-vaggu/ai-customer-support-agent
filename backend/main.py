from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv
import os
from knowledge_base import STORE_INFO, DEFAULT_SUPPORT_MESSAGE

# Load environment variables
load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check API key
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Load Gemini model
MODEL_NAME = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
model = genai.GenerativeModel(MODEL_NAME)

# Create FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model with conversation history
class MessageHistory(BaseModel):
    sender: str
    text: str

class Message(BaseModel):
    text: str
    history: list[MessageHistory] = []  # Conversation history (optional)

# Home route
@app.get("/")
async def home():
    return {
        "message": "Backend running successfully"
    }

# Chat route
@app.post("/chat")
async def chat(message: Message):

    try:
        user_text = message.text
        conversation_history = message.history or []

        # Limit to last 10 messages for richer context window
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history

        # Format conversation history
        history_context = ""
        if recent_history:
            history_context = "Previous conversation:\n"
            for msg in recent_history:
                sender = "Customer" if msg.sender == "user" else "Support Agent"
                history_context += f"{sender}: {msg.text}\n"
            history_context += "\n"

        prompt = f"""You are a professional AI customer support assistant for NovaCart, an e-commerce platform.

CONVERSATION CONTEXT (Use this to understand what the customer is referring to):
{history_context if history_context else '(No previous conversation)'}

KNOWLEDGE BASE:
{STORE_INFO}

INSTRUCTIONS FOR RESPONDING:
1. Use conversation context to understand customer intent
   - If customer mentions a product earlier, follow-up questions refer to that product
   - Example: If "iPhone 15" was discussed, "any discount?" means discount on iPhone 15
2. Answer questions based on knowledge base and conversation history combined
3. Be concise, professional, and helpful (2-3 sentences max)
4. For related questions (discounts, colors, warranty, etc.), answer based on the product context
5. If truly unable to help (unrelated topic), use fallback message: "{DEFAULT_SUPPORT_MESSAGE}"
6. Always maintain accuracy when quoting prices or policies
7. Never make up information not in the knowledge base

Current customer message:
Customer: {user_text}

Support Agent Response:"""

        # Generate AI response
        response = model.generate_content(prompt)

        # Debug logging
        print(f"DEBUG - Response object: {response}")
        print(f"DEBUG - Response candidates: {response.candidates if hasattr(response, 'candidates') else 'N/A'}")
        
        # Extract text safely - check multiple sources
        ai_reply = None
        
        # Try response.text first
        if hasattr(response, 'text') and response.text:
            ai_reply = response.text
        # If empty, check candidates
        elif hasattr(response, 'candidates') and response.candidates:
            try:
                first_candidate = response.candidates[0]
                if hasattr(first_candidate, 'content') and first_candidate.content.parts:
                    ai_reply = first_candidate.content.parts[0].text
            except (IndexError, AttributeError):
                pass
        
        # If still no response, check for safety ratings
        if not ai_reply:
            print("WARNING: No valid response text found")
            if hasattr(response, 'prompt_feedback'):
                print(f"DEBUG - Prompt feedback: {response.prompt_feedback}")
            if hasattr(response, 'candidates') and response.candidates:
                print(f"DEBUG - Finish reason: {response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'N/A'}")
            ai_reply = "I apologize, but I encountered a technical issue. Please try again or contact support at +91-9876543210."
        
        print(f"DEBUG - Final reply: {ai_reply[:100]}...")
        
        return {
            "response": ai_reply
        }

    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        import traceback
        print("TRACEBACK:", traceback.format_exc())
        return {
            "response": DEFAULT_SUPPORT_MESSAGE
        }