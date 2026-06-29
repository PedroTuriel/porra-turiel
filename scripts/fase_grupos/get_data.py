import json
import time
from datetime import datetime
from pathlib import Path

import requests


BASE_URL = "https://worldcup26.ir"

DATA_DIR = Path("data")
TEAMS_FILE = DATA_DIR / "teams.json"
OUTPUT_FILE = DATA_DIR / "standings.json"


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


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Ejecuta primero: python generate_teams_json.py"
        )

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_team_map(teams_data: dict) -> dict:
    teams = teams_data.get("teams", [])

    return {
        str(team["id"]): {
            "id": str(team["id"]),
            "name": team.get("name_en"),
            "fifa_code": team.get("fifa_code"),
            "group": team.get("groups"),
            "flag": team.get("flag"),
        }
        for team in teams
    }


def build_standings(groups_data: dict, team_map: dict) -> dict:
    result = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": {
            "groups": f"{BASE_URL}/get/groups",
            "teams": str(TEAMS_FILE),
        },
        "groups": {},
    }

    for group in groups_data.get("groups", []):
        group_name = group.get("name")
        rows = []

        for team_stats in group.get("teams", []):
            team_id = str(team_stats.get("team_id"))
            team_info = team_map.get(team_id, {})

            rows.append({
                "team_id": team_id,
                "team": team_info.get("name", f"Unknown {team_id}"),
                "fifa_code": team_info.get("fifa_code"),
                "flag": team_info.get("flag"),
                "played": to_int(team_stats.get("mp")),
                "wins": to_int(team_stats.get("w")),
                "draws": to_int(team_stats.get("d")),
                "losses": to_int(team_stats.get("l")),
                "points": to_int(team_stats.get("pts")),
                "goals_for": to_int(team_stats.get("gf")),
                "goals_against": to_int(team_stats.get("ga")),
                "goal_difference": to_int(team_stats.get("gd")),
            })

        rows.sort(
            key=lambda x: (
                x["points"],
                x["goal_difference"],
                x["goals_for"],
            ),
            reverse=True,
        )

        for index, row in enumerate(rows, start=1):
            row["position"] = index

        result["groups"][group_name] = rows

    return result


def save_json(data: dict):
    DATA_DIR.mkdir(exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(f"Fichero generado: {OUTPUT_FILE}")


def main():
    print("Leyendo equipos estáticos...")
    teams_data = read_json(TEAMS_FILE)

    print("Recuperando grupos...")
    groups_data = get_json("/get/groups")

    team_map = build_team_map(teams_data)
    standings = build_standings(groups_data, team_map)

    save_json(standings)

    print("Clasificación actual:")
    for group_name, teams in standings["groups"].items():
        print(f"\nGrupo {group_name}")
        for team in teams:
            print(
                f'{team["position"]}. {team["team"]} - '
                f'{team["points"]} pts, '
                f'DG {team["goal_difference"]}, '
                f'GF {team["goals_for"]}, '
                f'GC {team["goals_against"]}'
            )


if __name__ == "__main__":
    main()