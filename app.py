from fastapi import FastAPI
from pydantic import BaseModel
import os
import socket
from textblob import TextBlob

# Optional: Gemini (Google Generative AI) - used only if key & internet are available
try:
    import google.generativeai as genai
except Exception:
    genai = None

app = FastAPI(title="Python Grammar Assistant (TextBlob offline + Gemini online)")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
use_gemini = False
model = None


# -------------------- INTERNET CHECK -------------------- #
def is_internet_available(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


# -------------------- GEMINI CONFIG -------------------- #
def configure_gemini():
    """Connect Gemini model if API key + internet exist."""
    global use_gemini, model
    if genai is None:
        use_gemini = False
        return
    if not GEMINI_API_KEY or not is_internet_available():
        use_gemini = False
        return
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        use_gemini = True
        print("✅ Gemini connected (online mode).")
    except Exception as e:
        print("⚠ Gemini setup failed:", e)
        use_gemini = False


# Try to set up Gemini at startup
configure_gemini()


# -------------------- DATA MODEL -------------------- #
class TextInput(BaseModel):
    text: str


# -------------------- ROUTES -------------------- #
@app.get("/")
def root():
    mode = "Online (Gemini)" if use_gemini else "Offline (TextBlob)"
    return {"message": f"Grammar Assistant running in {mode} mode 🚀"}


@app.post("/check")
def check_grammar(data: TextInput):
    text = data.text.strip()
    global use_gemini

    # Recheck internet / switch modes dynamically
    if is_internet_available() and not use_gemini:
        configure_gemini()
    elif not is_internet_available() and use_gemini:
        use_gemini = False

    # -------------------- ONLINE (GEMINI) -------------------- #
    if use_gemini:
        try:
            prompt = (
                f'Correct the following text and explain briefly. '
                f'Respond in JSON with keys: corrected_text, explanation.\\nText: "{text}"'
            )
            response = model.generate_content(prompt)
            import json
            parsed = json.loads(response.text)
            return {
                "suggestion": parsed.get("corrected_text", text),
                "explanation": parsed.get("explanation", "No explanation."),
            }
        except Exception as e:
            print("⚠ Gemini error, switching to offline mode:", e)
            use_gemini = False

    # -------------------- OFFLINE (TEXTBLOB) -------------------- #
    try:
        blob = TextBlob(text)
        corrected = str(blob.correct())
        explanation = (
            "Corrected using TextBlob (offline). "
            "TextBlob performs spelling correction and simple grammar improvements."
        )
    except Exception as e:
        corrected = text
        explanation = f"Offline correction failed: {e}"

    return {"suggestion": corrected, "explanation": explanation}


# -------------------- RUN SERVER -------------------- #
def run_server(host="127.0.0.1", port=5000):
    import uvicorn
    uvicorn.run("backend.app:app", host=host, port=port, reload=False)
