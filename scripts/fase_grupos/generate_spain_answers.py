import json
from datetime import datetime
from pathlib import Path


STANDINGS_FILE = Path("data") / "standings.json"
OUTPUT_FILE = Path("data") / "spain_answers.json"


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def split_names(value: str) -> list[str]:
    """
    Permite introducir varios jugadores separados por coma.
    Ejemplo:
    Morata, Lamine Yamal
    """
    return [name.strip() for name in value.split(",") if name.strip()]


def find_spain_stats(standings: dict) -> dict:
    groups = standings.get("groups", {})

    for group_name, teams in groups.items():
        for team in teams:
            if team.get("team") == "Spain":
                return {
                    "group": group_name,
                    "team": team.get("team"),
                    "team_id": team.get("team_id"),
                    "played": team.get("played", 0),
                    "points": team.get("points", 0),
                    "goals_for": team.get("goals_for", 0),
                    "goals_against": team.get("goals_against", 0),
                    "goal_difference": team.get("goal_difference", 0),
                    "position": team.get("position"),
                }

    raise ValueError("No se ha encontrado España en standings.json")


def main():
    standings = read_json(STANDINGS_FILE)
    spain_stats = find_spain_stats(standings)

    print("Datos actuales de España recuperados desde standings.json:")
    print(f"Grupo: {spain_stats['group']}")
    print(f"Posición: {spain_stats['position']}")
    print(f"Partidos jugados: {spain_stats['played']}")
    print(f"Goles marcados: {spain_stats['goals_for']}")
    print(f"Goles encajados: {spain_stats['goals_against']}")

    print("\nIntroduce los datos manuales.")
    print("Si hay más de un jugador empatado, sepáralos por coma.")
    print("Ejemplo: Morata, Lamine Yamal\n")

    top_scorers_input = input("Máximo goleador/es de España: ")
    top_assistants_input = input("Máximo asistente/s de España: ")

    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": {
            "goals": "data/standings.json",
            "top_scorers": "manual",
            "top_assistants": "manual",
        },
        "spain": {
            "group": spain_stats["group"],
            "team": "Spain",
            "team_id": spain_stats["team_id"],
            "played": spain_stats["played"],
            "position": spain_stats["position"],
            "points": spain_stats["points"],
            "goals_for": spain_stats["goals_for"],
            "goals_against": spain_stats["goals_against"],
            "goal_difference": spain_stats["goal_difference"],
            "top_scorers": split_names(top_scorers_input),
            "top_assistants": split_names(top_assistants_input),
        },
    }

    write_json(OUTPUT_FILE, data)

    print(f"\nFichero generado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()