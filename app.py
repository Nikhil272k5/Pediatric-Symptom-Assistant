from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import run_triage
import uvicorn

app = FastAPI(
    title="Mumzworld Pediatric Symptom Triage",
    description="Bilingual EN/AR pediatric symptom triage API for Mumzworld parents in the MENA region.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    input: str
    locale: str = "auto"  # "en", "ar", "auto" — informational only, pipeline auto-detects


@app.get("/health")
def health():
    return {"status": "ok", "service": "Mumzworld Pediatric Triage"}


@app.post("/triage")
def triage(request: TriageRequest):
    if not request.input or not request.input.strip():
        raise HTTPException(status_code=400, detail="Input cannot be empty.")
    result = run_triage(request.input)
    return result


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
