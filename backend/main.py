from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import fitz  # PyMuPDF
import torch
from transformers import pipeline
import os

app = FastAPI(title="AI PDF Summarizer")

# Serve your new frontend
# Make sure this path points to your new frontend folder
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Load offline model at startup
OFFLINE_MODEL_NAME = "facebook/bart-large-cnn"
device = 0 if torch.cuda.is_available() else -1
offline_summarizer = pipeline("summarization", model=OFFLINE_MODEL_NAME, device=device)


def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Extract text from uploaded PDF file.
    """
    text = ""
    try:
        with fitz.open(stream=file.file.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid PDF file")
    return text


def summarize_text(text: str, mode: str, length: str) -> str:
    """
    Summarize text using either offline or online model.
    """
    # Define length parameters
    if length == "short":
        max_len, min_len = 80, 20
    elif length == "medium":
        max_len, min_len = 150, 50
    else:  # long
        max_len, min_len = 300, 100

    if mode == "offline":
        return offline_summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']

    elif mode == "online":
        # Load online model lazily
        online_summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=device)
        return online_summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']

    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Choose 'online' or 'offline'.")


@app.post("/api/summarize/{mode}")
async def summarize(mode: str, file: UploadFile, length: str = Form("medium")):
    """
    API endpoint to summarize PDF.
    mode: 'online' or 'offline'
    length: 'short', 'medium', or 'long'
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    text = extract_text_from_pdf(file)

    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF contains no text.")

    summary = summarize_text(text, mode, length)
    return JSONResponse({"summary": summary})


# Optional root endpoint redirecting to frontend
@app.get("/")
async def root():
    return JSONResponse({"message": "Visit /frontend/index.html for the UI"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True)
