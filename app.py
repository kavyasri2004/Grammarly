from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
import re
import google.generativeai as genai
import asyncio

# --- Load environment variables from .env (local) ---
load_dotenv()

# --- FastAPI app ---
app = FastAPI()

# --- Gemini setup ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    raise RuntimeError(" Missing GEMINI_API_KEY — please set it in .env or environment variables")

genai.configure(api_key=GEMINI_KEY)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
model = genai.GenerativeModel(MODEL_NAME)

# --- Request/Response Models ---
class CheckRequest(BaseModel):
    text: str
    language: str = "auto"

class CheckResponse(BaseModel):
    original: str
    suggestion: str
    explanation: str

# --- API endpoint ---
@app.post("/check", response_model=CheckResponse)
async def check(req: CheckRequest):
    prompt = f"""
You are a professional English grammar assistant. Follow these strict rules exactly:
1) Fix grammar, spelling, punctuation, and sentence structure so the output is one natural, fluent sentence.
2) Ensure tense and verb agreement are consistent across clauses.
3) Preserve the original meaning; do NOT invent new facts.
4) Output only valid JSON and nothing else, in this exact shape:
{{"corrected": "<corrected sentence>"}}

Text: {req.text}
"""
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=30
        )

        raw = getattr(response, "text", None)
        if not raw and response.candidates:
            raw = response.candidates[0].content.parts[0].text

    except asyncio.TimeoutError:
        return CheckResponse(
            original=req.text,
            suggestion=req.text,
            explanation=" Gemini request timed out, returned original text."
        )
    except Exception as e:
        return CheckResponse(
            original=req.text,
            suggestion=req.text,
            explanation=f"⚠ Gemini error: {e}, returned original text."
        )

    if not raw:
        return CheckResponse(
            original=req.text,
            suggestion=req.text,
            explanation=" No response from Gemini, returned original text."
        )

    raw = raw.strip()

    # --- Extract JSON safely ---
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    corrected = ""

    if match:
        json_str = match.group(0)
        try:
            data = json.loads(json_str)
            corrected = data.get("corrected", "").strip()
        except Exception:
            corrected = raw.strip()
    else:
        corrected = raw.strip()

    # --- Fallback if empty ---
    if not corrected:
        corrected = req.text.strip()

    return CheckResponse(
        original=req.text,
        suggestion=corrected,
        explanation=" Grammar corrected"
    )
