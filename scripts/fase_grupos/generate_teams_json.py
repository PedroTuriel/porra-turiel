import json
import time
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://worldcup26.ir"
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "teams.json"


def get_json(endpoint: str) -> dict:
    url = f"{BASE_URL}{endpoint}"

    headers = {
        "User-Agent": "Mozilla/5.0 PorraTurielBot/1.0",
        "Accept": "application/json",
    }

    last_error = None

    for attempt in range(1, 6):
        try:
            print(f"Intento {attempt}/5: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:
            last_error = error
            print(f"Error en intento {attempt}/5: {error}")
            time.sleep(3)

    raise RuntimeError(
        f"No se pudo recuperar {url} después de 5 intentos"
    ) from last_error


def save_json(data: dict):
    OUTPUT_DIR.mkdir(exist_ok=True)

    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": f"{BASE_URL}/get/teams",
        "teams": data.get("teams", []),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"Fichero generado: {OUTPUT_FILE}")
    print(f"Equipos guardados: {len(output['teams'])}")


def main():
    print("Generando fichero estático de equipos...")
    teams_data = get_json("/get/teams")
    save_json(teams_data)


if __name__ == "__main__":
    main()