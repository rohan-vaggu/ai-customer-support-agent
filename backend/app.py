from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv
import os
from knowledge_base import STORE_INFO, DEFAULT_SUPPORT_MESSAGE
import hashlib
import json
from datetime import datetime

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
model = genai.GenerativeModel(MODEL_NAME)

# Response cache to avoid hitting API limits
response_cache = {}

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-customer-support-agent-psi.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock AI response function - uses knowledge base when API is unavailable
def get_mock_response(user_text: str, conversation_history: list) -> str:
    """
    Generate response using knowledge base without API calls.
    Useful when API quota is exceeded.
    """
    text_lower = user_text.lower()
    
    # Product inquiries
    if any(word in text_lower for word in ["iphone", "samsung", "macbook", "product", "what do you have", "catalog"]):
        return "We have three main products: iPhone 15 (₹74,999 with discount), Samsung Galaxy S24 (₹71,999 with discount), and MacBook Air M3 (₹1,04,999 with discount). All come with instant discounts and 1-year warranty. Which one interests you?"
    
    # Pricing/Discount inquiries
    if any(word in text_lower for word in ["discount", "price", "cost", "offer", "how much"]):
        return "Great! We have instant discounts on all products: Smartphones get ₹3,000-₹5,000 off, and laptops get ₹10,000 off. We also offer 0% EMI on purchases above ₹5,000. Would you like details on a specific product?"
    
    # Shipping inquiries
    if any(word in text_lower for word in ["shipping", "delivery", "how long", "when will", "arrive", "track"]):
        return "Free shipping on orders above ₹999! Standard delivery is 3-7 business days, and we offer same-day delivery in select cities. You can track your order in real-time. Which location are you in?"
    
    # Return/Refund inquiries
    if any(word in text_lower for word in ["return", "refund", "damaged", "warranty", "exchange"]):
        return "No problem! You can return items within 7 days in original condition. Damaged items get full refunds within 5 business days. Return shipping is free for defective items. Would you like to start a return?"
    
    # Payment inquiries
    if any(word in text_lower for word in ["payment", "pay", "card", "upi", "transfer", "method"]):
        return "We accept multiple payment methods: UPI, Debit/Credit Cards, Net Banking, Cash on Delivery (COD), and 0% EMI. Choose whatever is convenient for you!"
    
    # EMI inquiries
    if any(word in text_lower for word in ["emi", "installment", "payment plan"]):
        return "Yes! We offer 0% interest EMI on all purchases above ₹5,000. No hidden charges. Would you like to know the EMI options for a specific product?"
    
    # Greeting/General
    if any(word in text_lower for word in ["hi", "hello", "hey", "good morning", "good evening"]):
        return "Hello! Welcome to NovaCart AI Support. How can I help you today? You can ask about products, prices, shipping, returns, or anything else!"
    
    # Fallback
    return "I'd be happy to help! Could you ask more specifically about products, prices, shipping, returns, or payments? You can also contact our team at +91-9876543210 or support@novacart.com."

def get_cache_key(user_text: str, history: list) -> str:
    """Generate cache key from user text and recent history"""
    history_str = json.dumps([(h.sender, h.text[-50:]) for h in history[-5:]], sort_keys=True)
    combined = f"{user_text}:{history_str}"
    return hashlib.md5(combined.encode()).hexdigest()

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
    return {"message": "Backend Running"}

# Chat route
@app.post("/chat")
async def chat(message: Message):
    try:
        user_text = message.text or ""
        conversation_history = message.history or []

        # Check cache first
        cache_key = get_cache_key(user_text, conversation_history)
        if cache_key in response_cache:
            print(f"DEBUG - Using cached response for: {user_text[:50]}")
            return {"response": response_cache[cache_key]}

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
        
        print(f"DEBUG - Final reply: {ai_reply[:100] if ai_reply else 'None'}...")

        # Cache the response
        response_cache[cache_key] = ai_reply

        return {
            "response": ai_reply
        }
    except ResourceExhausted as e:
        print("QUOTA EXCEEDED:", str(e))
        # Use mock response instead of generic message
        mock_response = get_mock_response(message.text or "", message.history or [])
        response_cache[get_cache_key(message.text or "", message.history or [])] = mock_response
        return {
            "response": mock_response
        }
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
        import traceback
        print("TRACEBACK:", traceback.format_exc())
        # Try mock response as fallback
        mock_response = get_mock_response(message.text or "", message.history or [])
        return {
            "response": mock_response
        }