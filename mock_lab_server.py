import json
from datetime import datetime, timezone
from typing import List, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
import uvicorn

# ==========================================
# PAMIĘĆ RAM
# ==========================================
SAMPLES_RAM: List[Any] = []
current_sample_idx: int = 0
frame_counter: int = 0


class WaveShaperRAM:
    start_freq = 191.1
    stop_freq = 196.1
    last_profile = ""

ws_ram = WaveShaperRAM()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wczytanie próbek FROG do RAM przy starcie
    for i in range(1, 6):
        try:
            with open(f"frog_mockup/frog_data_{i}.json", "r", encoding="utf-8") as f:
                SAMPLES_RAM.append(json.load(f))
        except FileNotFoundError:
            pass
    print(f"[LAB MOCK] Załadowano {len(SAMPLES_RAM)} próbek FROGa do pamięci RAM.")
    yield


app = FastAPI(title="Full Optical Lab Mock (FROG + WaveShaper)", lifespan=lifespan)


# --- ENDPOINTY FROG ---
@app.put("/runner/start")
@app.put("/start")
async def frog_start():
    return {"status": "started"}


@app.get("/runner/lastResult/json")
async def get_frog_last_result(subRunnerId: str = Query(...)):
    global current_sample_idx, frame_counter
    if not SAMPLES_RAM:
        return {}

    sample = json.loads(json.dumps(SAMPLES_RAM[current_sample_idx]))
    current_sample_idx = (current_sample_idx + 1) % len(SAMPLES_RAM)
    frame_counter += 1

    if isinstance(sample, list) and len(sample) > 0 and sample[0]:
        acq = sample[0]
        acq["sequenceNum"] = frame_counter
        if "acquisition" in acq:
            acq["acquisition"]["timestamp"] = datetime.now(timezone.utc).isoformat()

    if subRunnerId == "acquisition":
        return sample[0] if isinstance(sample, list) else sample
    return sample[1] if isinstance(sample, list) and len(sample) > 1 else None


# --- ENDPOINTY WAVESHAPER ---
@app.get("/waveshaper/devinfo")
async def ws_devinfo():
    return {"startfreq": ws_ram.start_freq, "stopfreq": ws_ram.stop_freq, "sno": "WS-MOCK"}


@app.post("/waveshaper/loadprofile")
async def ws_loadprofile(request: Request):
    data = await request.json()
    if isinstance(data, str):
        data = json.loads(data)
    ws_ram.last_profile = data.get("wsp", "")
    return {"rc": 0, "msg": "OK", "sno": "WS-MOCK"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)