import json
import argparse
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RESULTS_FILE = BASE_DIR / "data" / "dieciseisavos" / "data.json"
DEFAULT_PREDICTIONS_FILE = BASE_DIR / "data" / "dieciseisavos" / "predicciones_dieciseisavos.json"
DEFAULT_OUTPUT_JSON = BASE_DIR / "data" / "dieciseisavos" / "leaderboard_dieciseisavos.json"


DECISION_ALIASES = {
    "90": "90",
    "90_min": "90",
    "90 minutos": "90",
    "90min": "90",
    "normal": "90",
    "prorroga": "extra_time",
    "prórroga": "extra_time",
    "extra_time": "extra_time",
    "extra time": "extra_time",
    "penaltis": "penalties",
    "penalties": "penalties",
    "penalty": "penalties",
}


def strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(ch) != "Mn"
    )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = strip_accents(str(value)).lower().strip()
    text = text.replace(".", "").replace("-", " ")
    return " ".join(text.split())


def normalize_decision(value: Any) -> str:
    key = normalize_text(value)
    return DECISION_ALIASES.get(key, key)


def match_key(home_team: str, away_team: str) -> Tuple[str, str]:
    return normalize_text(home_team), normalize_text(away_team)


def get_winner(match: Dict[str, Any]) -> Optional[str]:
    for key in (
        "winner",
        "qualified_team",
        "classified_team",
        "winner_team",
        "team_winner",
        "penalty_winner",
        "penalties_winner",
        "extra_time_winner",
        "qualified",
        "classified",
    ):
        if match.get(key):
            return match[key]

    home_goals = match.get("home_goals")
    away_goals = match.get("away_goals")

    if home_goals is None or away_goals is None:
        return None

    home_goals = int(home_goals)
    away_goals = int(away_goals)

    if home_goals > away_goals:
        return match["home_team"]

    if away_goals > home_goals:
        return match["away_team"]

    # Si hay empate en 90 minutos, necesitamos saber quién se clasificó.
    # Si no está indicado en data.json, no se puede calcular bien el ganador.
    return None


def score_total_goals(predicted: Any, actual: Any) -> int:
    if predicted is None or actual is None:
        return 0

    diff = abs(int(predicted) - int(actual))

    if diff == 0:
        return 3
    if diff == 1:
        return 2
    if diff == 2:
        return 1
    return 0


def score_spain_first_goal(predicted: Any, actual: Any) -> int:
    if predicted is None or actual is None:
        return 0

    diff = abs(int(predicted) - int(actual))

    if diff == 0:
        return 5
    if diff == 1:
        return 3
    return 0


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_results_index(results: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index = {}

    for match in results.get("matches", []):
        index[match_key(match["home_team"], match["away_team"])] = match

    return index


def calculate_points(results: Dict[str, Any], predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
    results_index = build_results_index(results)
    actual_spain = results.get("spain", {})
    leaderboard = []

    for participant in predictions.get("participants", []):
        name = (
            participant.get("mote")
            or participant.get("participant")
            or participant.get("name")
            or "Sin nombre"
        )

        total_points = 0
        match_points = 0
        match_details = []

        for pred_match in participant.get("matches", []):
            key = match_key(pred_match["home_team"], pred_match["away_team"])
            real_match = results_index.get(key)

            match_name = f"{pred_match['home_team']} - {pred_match['away_team']}"

            if not real_match:
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Partido no encontrado en data.json"
                })
                continue

            if real_match.get("home_goals") is None or real_match.get("away_goals") is None:
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Partido pendiente en data.json"
                })
                continue

            actual_winner = get_winner(real_match)
            actual_total_goals = int(real_match["home_goals"]) + int(real_match["away_goals"])
            actual_decision = normalize_decision(real_match.get("decided_in"))

            points_winner = 0
            if actual_winner and normalize_text(pred_match.get("predicted_winner")) == normalize_text(actual_winner):
                points_winner = 6

            points_goals = score_total_goals(
                pred_match.get("predicted_total_goals_90"),
                actual_total_goals
            )

            points_decision = 0
            if normalize_decision(pred_match.get("predicted_decided_in")) == actual_decision:
                points_decision = 1

            points = points_winner + points_goals + points_decision

            match_points += points
            total_points += points

            match_details.append({
                "match": match_name,
                "points": points,
                "winner_points": points_winner,
                "goals_points": points_goals,
                "decision_points": points_decision,
                "prediction": {
                    "winner": pred_match.get("predicted_winner"),
                    "total_goals_90": pred_match.get("predicted_total_goals_90"),
                    "decided_in": pred_match.get("predicted_decided_in"),
                },
                "real": {
                    "winner": actual_winner,
                    "home_goals": real_match.get("home_goals"),
                    "away_goals": real_match.get("away_goals"),
                    "total_goals_90": actual_total_goals,
                    "decided_in": actual_decision,
                }
            })

        participant_spain = participant.get("spain", {})

        first_goal_points = score_spain_first_goal(
            participant_spain.get("first_spain_goal"),
            actual_spain.get("first_spain_goal")
        )

        first_sub_points = 0
        if actual_spain.get("first_spain_sub") is not None:
            if normalize_text(participant_spain.get("first_spain_sub")) == normalize_text(actual_spain.get("first_spain_sub")):
                first_sub_points = 3

        mvp_points = 0
        if actual_spain.get("spain_mvp") is not None:
            if normalize_text(participant_spain.get("spain_mvp")) == normalize_text(actual_spain.get("spain_mvp")):
                mvp_points = 2

        spain_points = first_goal_points + first_sub_points + mvp_points
        total_points += spain_points

        leaderboard.append({
            "participant": name,
            "total_points": total_points,
            "match_points": match_points,
            "spain_points": spain_points,
            "spain_detail": {
                "first_spain_goal_points": first_goal_points,
                "first_spain_sub_points": first_sub_points,
                "spain_mvp_points": mvp_points,
                "prediction": {
                    "first_spain_goal": participant_spain.get("first_spain_goal"),
                    "first_spain_sub": participant_spain.get("first_spain_sub"),
                    "spain_mvp": participant_spain.get("spain_mvp"),
                },
                "real": {
                    "first_spain_goal": actual_spain.get("first_spain_goal"),
                    "first_spain_sub": actual_spain.get("first_spain_sub"),
                    "spain_mvp": actual_spain.get("spain_mvp"),
                }
            },
            "match_detail": match_details,
        })

    leaderboard.sort(key=lambda row: row["total_points"], reverse=True)

    for position, row in enumerate(leaderboard, start=1):
        row["position"] = position

    return leaderboard


def save_json(data: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calcula puntos de la porra de dieciseisavos.")

    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_FILE),
        help="Fichero con resultados reales."
    )
    parser.add_argument(
        "--predictions",
        default=str(DEFAULT_PREDICTIONS_FILE),
        help="Fichero con predicciones."
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Salida JSON."
    )

    args = parser.parse_args()

    results_path = Path(args.results)
    predictions_path = Path(args.predictions)
    output_json_path = Path(args.output_json)

    results = load_json(results_path)
    predictions = load_json(predictions_path)

    leaderboard = calculate_points(results, predictions)
    save_json(leaderboard, output_json_path)

    print("\nCLASIFICACIÓN DIECISEISAVOS")
    print("=" * 40)

    for row in leaderboard:
        print(
            f"{row['position']:>2}. {row['participant']} - "
            f"{row['total_points']} pts "
            f"({row['match_points']} partidos + {row['spain_points']} España)"
        )

    print(f"\nJSON generado: {output_json_path.resolve()}")


if __name__ == "__main__":
    main()