import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn


# ==========================================
# STAN URZĄDZENIA W PAMIĘCI RAM
# ==========================================
class WaveShaperState:
    def __init__(self):
        # Domyślny zakres częstotliwości w THz (ok. 191.1 - 196.1 THz dla C-band / 1530-1570 nm)
        self.start_freq: float = 191.1000
        self.stop_freq: float = 196.1000
        self.serial_number: str = "WS-MOCK-12345"

        # Ostatnio wgrany profil w pamięci RAM
        self.last_wsp_profile: str = ""
        self.parsed_points_count: int = 0


state = WaveShaperState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Zarządzanie cyklem życia serwera mocka."""
    print("[WaveShaper Mock] Uruchomiono symulator WaveShaper w pamięci RAM.")
    yield
    print("[WaveShaper Mock] Wyczyszczono pamięć RAM.")


app = FastAPI(title="Finisar WaveShaper Mock Server", lifespan=lifespan)


# ==========================================
# ENDPOINTY API WAVESHAPERA (odwzorowanie Waveshaper.py)
# ==========================================

@app.get("/waveshaper/devinfo")
async def get_devinfo():
    """Zwraca podstawowe parametry urządzenia potrzebne dla konstruktora klasy WaveShaper."""
    return {
        "startfreq": state.start_freq,
        "stopfreq": state.stop_freq,
        "sno": state.serial_number,
        "devtype": "WaveShaper 4000S Mock"
    }


@app.post("/waveshaper/loadprofile")
async def load_profile(request: Request):
    """
    Odbiera profil tłumienia i fazy.
    Oczekuje formatu JSON: {"type": "wsp", "wsp": "freq\tattn\tphase\tport\n..."}
    """
    try:
        data = await request.json()

        if isinstance(data, str):
            data = json.loads(data)

        wsp_string = data.get("wsp", "")

        # Zapis profilu w pamięci RAM
        state.last_wsp_profile = wsp_string
        lines = [line for line in wsp_string.strip().split("\n") if line]
        state.parsed_points_count = len(lines)

        print(f"[WaveShaper Mock] Załadowano profil. Liczba punktów: {state.parsed_points_count}")

        # Kod odpowiedzi 'rc': 0 oznacza OK, tak jak oczekuje klasa WaveShaper
        return {
            "rc": 0,
            "msg": "OK",
            "sno": state.serial_number
        }

    except Exception as e:
        print(f"[WaveShaper Mock ERROR] Błąd przetwarzania profilu: {e}")
        return {
            "rc": -1,
            "msg": f"error: invalid format ({str(e)})",
            "sno": state.serial_number
        }


@app.get("/waveshaper/debug_ram")
async def debug_ram():
    """Dodatkowy endpoint do podglądu stanu mocka z poziomu przeglądarki/GUI."""
    return {
        "points_count": state.parsed_points_count,
        "sample_lines": state.last_wsp_profile.split("\n")[:5] if state.last_wsp_profile else []
    }


if __name__ == "__main__":
    # Uruchomienie na porcie 8080 (lub 8000), zgodne z adresem IP w Twoim kodzie
    uvicorn.run(app, host="127.0.0.1", port=8000)