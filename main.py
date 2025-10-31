from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.post("/check")
def check_grammar(input_text: TextInput):
    original = input_text.text
    suggestion = original.replace(" .", ".")
    if suggestion == original:
        explanation = "No major issues found."
    else:
        explanation = "Removed unnecessary space before period."
    return {
        "original": original,
        "suggestion": suggestion,
        "explanation": explanation
    }
