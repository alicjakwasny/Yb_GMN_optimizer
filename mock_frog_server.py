import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
import uvicorn

# ==========================================
# WARSTWA PAMIĘCI RAM
# ==========================================
SAMPLES_RAM: List[Any] = []
current_sample_idx: int = 0
frame_counter: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Nowoczesny zarządca cyklu życia aplikacji (zastępuje wycofane @app.on_event).
    Wczytuje pliki JSON do pamięci RAM przy starcie serwera.
    """
    global SAMPLES_RAM
    for i in range(1, 6):
        filename = f"frog_data_{i}.json"
        try:
            with open("frog_mockup/"+filename, "r", encoding="utf-8") as f:
                SAMPLES_RAM.append(json.load(f))
            print(f"[RAM Storage] Pomyślnie załadowano: {filename}")
        except FileNotFoundError:
            print(f"[Ostrzeżenie] Nie znaleziono pliku: {filename}")

    if not SAMPLES_RAM:
        print("[BŁĄD CRITICAL] Brak plików danych! Upewnij się, że pliki frog_data_X.json są w katalogu roboczym.")

    yield  # Miejsce, w którym aplikacja FastAPI działa i obsługuje zapytania

    # Kod po 'yield' wykonuje się przy wyłączaniu serwera (opcjonalny cleanup)
    SAMPLES_RAM.clear()
    print("[RAM Storage] Wyczyszczono pamięć RAM.")


# Inicjalizacja aplikacji z nowym zarządcą lifespan
app = FastAPI(title="FROG Hardware Mock Server", lifespan=lifespan)


def generate_mock_frame() -> Any:
    """Tworzy dynamiczną ramkę danych z pamięci RAM z aktualnymi znacznikami czasu."""
    global current_sample_idx, frame_counter
    if not SAMPLES_RAM:
        return {}

    # Pobranie próbki w pętli (Round-Robin)
    raw_sample = SAMPLES_RAM[current_sample_idx]
    current_sample_idx = (current_sample_idx + 1) % len(SAMPLES_RAM)
    frame_counter += 1

    # Szybka kopia struktury
    sample_copy = json.loads(json.dumps(raw_sample))
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    # Aktualizacja ramek akwizycji (struktura główna)
    if isinstance(sample_copy, list) and len(sample_copy) > 0 and sample_copy[0]:
        acq_data = sample_copy[0]
        acq_data["num"] = frame_counter
        acq_data["sequenceNum"] = frame_counter

        if "acquisition" in acq_data:
            acq_data["acquisition"]["timestamp"] = now_iso

        if "history" in acq_data and isinstance(acq_data["history"], list):
            for h_item in acq_data["history"]:
                h_item["timestamp"] = now_iso

    return sample_copy


# ==========================================
# ENDPOINTY API (Zgodne z femtoeasy.py)
# ==========================================

@app.put("/runner/start")
async def start_runner():
    return {"status": "started"}


@app.put("/start")
async def start_sub_runner(subRunnerId: str = Query(...)):
    return {"status": "started", "subRunnerId": subRunnerId}


@app.put("/stop")
async def stop_sub_runner(subRunnerId: str = Query(...)):
    return {"status": "stopped", "subRunnerId": subRunnerId}


@app.get("/runner/lastResult/json")
async def get_last_result(subRunnerId: str = Query(...)):
    sample = generate_mock_frame()

    # Obsługa struktury tablicowej [acquisition, retrieve]
    if isinstance(sample, list):
        if subRunnerId == "acquisition":
            return sample[0] if len(sample) > 0 else {}
        elif subRunnerId == "retrieve":
            return sample[1] if len(sample) > 1 else None

    return sample


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)