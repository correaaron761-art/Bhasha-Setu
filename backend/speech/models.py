import io, os, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf

SRA_MODEL = None
QWEN_TTS = None


def load_sravaani():
    global SRA_MODEL
    if SRA_MODEL is not None:
        return SRA_MODEL
    checkpoint = os.getenv("SRAVAANI_CHECKPOINT", "models/SraVaani-1.0.nemo")
    if not Path(checkpoint).exists():
        raise FileNotFoundError(f"SraVaani checkpoint not found: {checkpoint}")
    from nemo.collections.asr.models import EncDecHybridRNNTCTCBPEModel
    SRA_MODEL = EncDecHybridRNNTCTCBPEModel.restore_from(checkpoint, map_location="cuda" if _cuda() else "cpu")
    SRA_MODEL.eval()
    if _cuda():
        SRA_MODEL = SRA_MODEL.cuda()
    return SRA_MODEL


def _cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def transcribe_sravaani(audio_bytes: bytes) -> str:
    model = load_sravaani()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        try:
            result = model.transcribe([path], batch_size=1)
        except TypeError:
            result = model.transcribe([path])
        item = result[0] if isinstance(result, (list, tuple)) else result
        if hasattr(item, "text"):
            return item.text.strip()
        return str(item).strip()
    finally:
        try: os.unlink(path)
        except OSError: pass


def load_qwen_tts():
    global QWEN_TTS
    if QWEN_TTS is not None:
        return QWEN_TTS
    import torch
    from qwen_tts import Qwen3TTSModel
    model_id = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
    if torch.cuda.is_available():
        QWEN_TTS = Qwen3TTSModel.from_pretrained(model_id, device_map="cuda:0", dtype=torch.bfloat16)
    else:
        QWEN_TTS = Qwen3TTSModel.from_pretrained(model_id, device_map="cpu", dtype=torch.float32)
    return QWEN_TTS


def synthesize_qwen(text: str, language: str = "Hindi", speaker: str = "Vivian") -> tuple[bytes, int]:
    model = load_qwen_tts()
    supported = set(model.get_supported_languages()) if hasattr(model, "get_supported_languages") else set()
    if supported and language not in supported:
        raise ValueError(f"Qwen TTS does not support {language}. Supported: {sorted(supported)}")
    speakers = set(model.get_supported_speakers()) if hasattr(model, "get_supported_speakers") else set()
    if speakers and speaker not in speakers:
        speaker = next(iter(speakers))
    wavs, sr = model.generate_custom_voice(text=text, language=language, speaker=speaker)
    wav = np.asarray(wavs[0])
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue(), sr
