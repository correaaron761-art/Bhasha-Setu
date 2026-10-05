import io, os, re
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from speech.models import transcribe_sravaani, synthesize_qwen

BASE = Path(__file__).resolve().parent
OLM={"a":"ᱟ","e":"ᱮ","i":"ᱤ","o":"ᱚ","u":"ᱩ","O":"ᱳ","b":"ᱵ","c":"ᱪ","d":"ᱰ","D":"ᱫ","g":"ᱜ","h":"ᱦ","H":"ᱷ","j":"ᱡ","k":"ᱠ","K":"ᱠ","l":"ᱞ","m":"ᱢ","n":"ᱱ","N":"ᱸ","p":"ᱯ","q":"ᱧ","r":"ᱨ","R":"ᱲ","z":"ᱲ","s":"ᱥ","t":"ᱴ","T":"ᱛ","w":"ᱣ","v":"ᱶ","x":"ᱽ","y":"ᱭ","Y":"ᱭ"}

def to_olchiki(s: str) -> str:
    s = re.sub(r"([aeiouO])\.", lambda m: m.group(1) + chr(0x1C79), str(s))
    s = s.replace("aa", "a")
    return "".join(OLM.get(c,c) for c in s)

DB_PATH = BASE / "bhasa_setu.sqlite3"

def get_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def lookup_exact(text, source, target):
    source = "sat" if source == "san" else source
    target = "sat" if target == "san" else target
    with get_db() as conn:
        row = conn.execute(
            "SELECT target_text FROM entries WHERE source_language=? AND target_language=? AND lower(trim(source_text))=lower(trim(?)) ORDER BY length(target_text) DESC LIMIT 1",
            (source, target, text)
        ).fetchone()
    return row["target_text"] if row else None

def dictionary_rows(source, target):
    source = "sat" if source == "san" else source
    target = "sat" if target == "san" else target
    with get_db() as conn:
        return conn.execute(
            "SELECT source_text,target_text FROM entries WHERE source_language=? AND target_language=? ORDER BY length(source_text) DESC",
            (source, target)
        ).fetchall()

def dict_translate(text, source, target):
    if source == target:
        return text
    source = "sat" if source == "san" else source
    target = "sat" if target == "san" else target
    exact = lookup_exact(text, source, target)
    if exact is not None:
        result = exact
    else:
        result = text
        for row in dictionary_rows(source, target):
            src = row["source_text"].strip()
            dst = row["target_text"].strip().rstrip("?")
            if not src:
                continue
            if source == "sat":
                pattern = re.compile(r"(?<!\w)" + re.escape(src) + r"(?!\w)")
            else:
                pattern = re.compile(re.escape(src), re.IGNORECASE)
            result = pattern.sub(dst, result)
    if target == "sat":
        result = to_olchiki(result)
    return result


app = FastAPI(title="Bhasha Setu Speech + Translation API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class TTSRequest(BaseModel):
    text: str
    language: str = "Hindi"
    speaker: str = "Vivian"

@app.get("/")
def root():
    return {"app":"Bhasha Setu", "status":"ok", "speech":"SraVaani + Qwen3-TTS"}

@app.get("/speech/health")
def health():
    return {"status":"ok","sravaani":"local","qwen_tts":"local","translation":"Bhasha Setu offline dictionary"}

@app.post("/translate")
def translate(text: str = Form(...), source_language: str = Form("hi"), target_language: str = Form("san")):
    return {"text": dict_translate(text, source_language, target_language), "source_language": source_language, "target_language": target_language, "method":"offline_dictionary"}

@app.post("/speech/transcribe")
async def transcribe(file: UploadFile = File(...), source_language: str = Form("hi")):
    audio = await file.read()
    if not audio: raise HTTPException(400,"Empty audio file")
    try:
        text = transcribe_sravaani(audio)
        return {"text":text,"source_language":source_language,"model":"SraVaani-1.0"}
    except Exception as e:
        raise HTTPException(500,f"SraVaani transcription failed: {e}")

@app.post("/speech/voice-translate")
async def voice_translate(file: UploadFile = File(...), source_language: str = Form("hi"), target_language: str = Form("san")):
    audio=await file.read()
    if not audio: raise HTTPException(400,"Empty audio file")
    try: source_text=transcribe_sravaani(audio)
    except Exception as e: raise HTTPException(500,f"SraVaani transcription failed: {e}")
    translated=dict_translate(source_text,source_language,target_language)
    return {"source_text":source_text,"translated_text":translated,"source_language":source_language,"target_language":target_language,"asr_model":"SraVaani-1.0","translation_model":"Bhasha Setu offline dictionary"}

@app.post("/speech/synthesize")
async def synthesize(req:TTSRequest):
    try:
        audio,sr=synthesize_qwen(req.text,req.language,req.speaker)
        return StreamingResponse(io.BytesIO(audio),media_type="audio/wav",headers={"X-Sample-Rate":str(sr),"X-Model":"Qwen3-TTS"})
    except Exception as e:
        raise HTTPException(500,f"Qwen TTS failed: {e}")
