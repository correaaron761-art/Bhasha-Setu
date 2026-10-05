# Bhasha Setu local speech backend

Pipeline:

Microphone → SraVaani ASR → existing Bhasha Setu translation → Qwen3-TTS

SraVaani is used for local speech recognition. Qwen3-TTS is used for local speech synthesis where its language support matches the requested output. The backend does **not** pretend Qwen TTS supports Santhali; add a Santhali TTS model later for native Santhali audio.

## Windows setup

Use Python 3.12 for the speech environment rather than the Python 3.14 environment currently used by the project.

```powershell
py -3.12 -m venv speech_venv
.\speech_venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-speech.txt
```

Put the SraVaani `.nemo` checkpoint at:

```text
backend\models\SraVaani-nemo-checkpoint.nemo
```

or change `SRAVAANI_CHECKPOINT` in `.env`.

Start:

```powershell
uvicorn main:app --reload --port 8001
```

Test:

```text
http://127.0.0.1:8001/docs
```

The first model request downloads/loads model weights and can take a while.
