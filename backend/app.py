from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import google.generativeai as genai
import os

# =========================
# LOAD ENV
# =========================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# =========================
# FASTAPI APP
# =========================

app = FastAPI()

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# GEMINI SETUP
# =========================

model = None

try:

    if GEMINI_API_KEY:

        genai.configure(
            api_key=GEMINI_API_KEY
        )

        model = genai.GenerativeModel(
            "gemini-1.5-flash"
        )

        print("Gemini initialized successfully")

    else:

        print("WARNING: GEMINI_API_KEY missing")

except Exception as e:

    print("Gemini initialization failed:", str(e))

# =========================
# REQUEST MODEL
# =========================

class MessageHistory(BaseModel):
    sender: str
    text: str


class ChatRequest(BaseModel):
    text: str
    history: list[MessageHistory] = []

# =========================
# HOME ROUTE
# =========================

@app.get("/")
async def home():

    return {
        "message": "Backend Running Successfully"
    }

# =========================
# MOCK RESPONSE
# =========================

def mock_reply(user_text):

    text = user_text.lower()

    if "iphone" in text:
        return "The iPhone 15 is available for ₹74,999."

    if "samsung" in text:
        return "Samsung Galaxy S24 costs ₹71,999."

    if "refund" in text:
        return "We provide 7-day refund support."

    if "delivery" in text:
        return "Delivery takes 3-7 business days."

    return "Hello! How can I help you today?"

# =========================
# CHAT ROUTE
# =========================

@app.post("/chat")
async def chat(data: ChatRequest):

    try:

        user_text = data.text.strip()

        if not user_text:

            return {
                "response": "Please enter a message."
            }

        # =========================
        # FALLBACK IF MODEL FAILED
        # =========================

        if model is None:

            return {
                "response": mock_reply(user_text)
            }

        # =========================
        # FORMAT HISTORY
        # =========================

        history_text = ""

        for msg in data.history[-10:]:

            sender = (
                "Customer"
                if msg.sender == "user"
                else "Support Agent"
            )

            history_text += (
                f"{sender}: {msg.text}\n"
            )

        # =========================
        # PROMPT
        # =========================

        prompt = f"""
You are an AI customer support assistant.

Conversation:
{history_text}

Customer:
{user_text}

Support Agent:
"""

        # =========================
        # GEMINI RESPONSE
        # =========================

        response = model.generate_content(
            prompt
        )

        ai_reply = response.text

        return {
            "response": ai_reply
        }

    except Exception as e:

        print("CHAT ERROR:", str(e))

        return {
            "response": mock_reply(data.text)
        }