import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RESULTS_FILE = BASE_DIR / "data" / "octavos" / "data.json"
DEFAULT_PREDICTIONS_FILE = BASE_DIR / "data" / "octavos" / "predicciones_octavos.json"
DEFAULT_OUTPUT_JSON = BASE_DIR / "data" / "octavos" / "leaderboard_octavos.json"


HALF_TIME_ALIASES = {
    "1": "home",
    "home": "home",
    "local": "home",
    "gana local": "home",
    "gana el equipo local": "home",
    "gana equipo local": "home",
    "gana home": "home",
    "gana brasil": "home",
    "gana mexico": "home",
    "gana méxico": "home",
    "gana portugal": "home",
    "gana estados unidos": "home",
    "gana argentina": "home",
    "gana suiza": "home",
    "x": "draw",
    "empate": "draw",
    "draw": "draw",
    "2": "away",
    "away": "away",
    "visitante": "away",
    "gana visitante": "away",
    "gana el equipo visitante": "away",
    "gana equipo visitante": "away",
    "gana noruega": "away",
    "gana inglaterra": "away",
    "gana espana": "away",
    "gana españa": "away",
    "gana belgica": "away",
    "gana bélgica": "away",
    "gana egipto": "away",
    "gana colombia": "away",
}

YES_ALIASES = {"si", "sí", "yes", "true", "1", "y", "s"}
NO_ALIASES = {"no", "false", "0", "n"}


# ---------- Normalización ----------

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


def normalize_team(value: Any) -> str:
    text = normalize_text(value)
    aliases = {
        "eeuu": "estados unidos",
        "ee uu": "estados unidos",
        "usa": "estados unidos",
        "united states": "estados unidos",
        "us": "estados unidos",
        "england": "inglaterra",
        "mexico": "mexico",
        "espana": "espana",
        "belgium": "belgica",
        "switzerland": "suiza",
    }
    return aliases.get(text, text)


def normalize_half_time(value: Any, home_team: Optional[str] = None, away_team: Optional[str] = None) -> str:
    key = normalize_text(value)
    if key in HALF_TIME_ALIASES:
        return HALF_TIME_ALIASES[key]

    if home_team and key == normalize_text(f"gana {home_team}"):
        return "home"
    if away_team and key == normalize_text(f"gana {away_team}"):
        return "away"

    return key


def normalize_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    key = normalize_text(value)
    if key in YES_ALIASES:
        return True
    if key in NO_ALIASES:
        return False
    return None


def match_key(home_team: str, away_team: str) -> Tuple[str, str]:
    return normalize_team(home_team), normalize_team(away_team)


# ---------- Carga y preparación ----------

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_results_index(results: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index = {}
    for match in results.get("matches", []):
        index[match_key(match["home_team"], match["away_team"])] = match
    return index


def get_qualified_team(match: Dict[str, Any]) -> Optional[str]:
    for key in ("qualified_team", "winner", "classified_team", "winner_team"):
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

    # En eliminatorias, si hay empate, debe rellenarse qualified_team.
    return None


def get_actual_half_time(match: Dict[str, Any]) -> Optional[str]:
    if match.get("half_time_result") is not None:
        return normalize_half_time(match.get("half_time_result"), match.get("home_team"), match.get("away_team"))

    ht_home = match.get("half_time_home_goals")
    ht_away = match.get("half_time_away_goals")
    if ht_home is None or ht_away is None:
        return None

    ht_home = int(ht_home)
    ht_away = int(ht_away)
    if ht_home > ht_away:
        return "home"
    if ht_away > ht_home:
        return "away"
    return "draw"


def get_actual_penalty(match: Dict[str, Any]) -> Optional[bool]:
    for key in ("penalty_awarded", "penalty", "had_penalty", "penalty_in_match"):
        if key in match:
            return normalize_bool(match.get(key))
    return None


# ---------- Puntuaciones ----------

def score_diff_3_points(predicted: Any, actual: Any) -> int:
    """Exacto 3, diferencia 1 => 2, diferencia 2 => 1, resto 0."""
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


def find_possession_bonus_participants(
    predictions: Dict[str, Any],
    actual_possession: Optional[Any],
    include_ties: bool = True,
) -> set:
    """Devuelve participantes que reciben 3 puntos por estar entre los más cercanos sin acertar exacto.

    include_ties=True: si hay empate en la distancia del segundo puesto, todos los empatados reciben 3.
    include_ties=False: solo los dos primeros participantes en orden de aparición reciben 3.
    """
    if actual_possession is None:
        return set()

    actual = float(actual_possession)
    distances = []

    for participant in predictions.get("participants", []):
        name = participant.get("mote") or participant.get("participant") or participant.get("name") or "Sin nombre"
        pred = participant.get("spain", {}).get("spain_possession")
        if pred is None:
            continue

        pred_value = float(pred)
        if pred_value == actual:
            continue

        distances.append((abs(pred_value - actual), name))

    if not distances:
        return set()

    distances.sort(key=lambda row: row[0])

    if not include_ties:
        return {name for _, name in distances[:2]}

    # Tomamos el umbral de distancia de la segunda posición, incluyendo empates.
    cutoff_index = min(1, len(distances) - 1)
    cutoff_distance = distances[cutoff_index][0]
    return {name for diff, name in distances if diff <= cutoff_distance}


# ---------- Cálculo principal ----------

def calculate_points(results: Dict[str, Any], predictions: Dict[str, Any], include_possession_ties: bool = True) -> List[Dict[str, Any]]:
    results_index = build_results_index(results)
    actual_spain = results.get("spain", {})
    possession_bonus_participants = find_possession_bonus_participants(
        predictions,
        actual_spain.get("spain_possession"),
        include_ties=include_possession_ties,
    )

    leaderboard = []

    for participant in predictions.get("participants", []):
        name = participant.get("mote") or participant.get("participant") or participant.get("name") or "Sin nombre"

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
                    "warning": "Partido no encontrado en data.json",
                })
                continue

            # Si el partido todavía no está rellenado, lo dejamos a 0.
            required_fields = [
                real_match.get("qualified_team") or get_qualified_team(real_match),
                get_actual_half_time(real_match),
                real_match.get("yellow_cards"),
                real_match.get("corners"),
                get_actual_penalty(real_match),
            ]
            if any(value is None for value in required_fields):
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Partido pendiente o con campos incompletos en data.json",
                })
                continue

            actual_qualified = get_qualified_team(real_match)
            actual_half_time = get_actual_half_time(real_match)
            actual_yellows = real_match.get("yellow_cards")
            actual_corners = real_match.get("corners")
            actual_penalty = get_actual_penalty(real_match)

            points_qualified = 0
            if normalize_team(pred_match.get("predicted_qualified_team")) == normalize_team(actual_qualified):
                points_qualified = 5

            points_half_time = 0
            predicted_half_time = normalize_half_time(
                pred_match.get("predicted_half_time_result", pred_match.get("predicted_half_time")),
                pred_match.get("home_team"),
                pred_match.get("away_team"),
            )
            if predicted_half_time == actual_half_time:
                points_half_time = 2

            points_yellows = score_diff_3_points(pred_match.get("predicted_yellow_cards_90"), actual_yellows)
            points_corners = score_diff_3_points(pred_match.get("predicted_corners_90"), actual_corners)

            points_penalty = 0
            if normalize_bool(pred_match.get("predicted_penalty")) == actual_penalty:
                points_penalty = 2

            points = points_qualified + points_half_time + points_yellows + points_corners + points_penalty
            match_points += points
            total_points += points

            match_details.append({
                "match": match_name,
                "points": points,
                "qualified_points": points_qualified,
                "half_time_points": points_half_time,
                "yellow_cards_points": points_yellows,
                "corners_points": points_corners,
                "penalty_points": points_penalty,
                "prediction": {
                    "qualified_team": pred_match.get("predicted_qualified_team"),
                    "half_time_result": pred_match.get("predicted_half_time_result", pred_match.get("predicted_half_time")),
                    "yellow_cards_90": pred_match.get("predicted_yellow_cards_90"),
                    "corners_90": pred_match.get("predicted_corners_90"),
                    "penalty": pred_match.get("predicted_penalty"),
                },
                "real": {
                    "qualified_team": actual_qualified,
                    "half_time_result": actual_half_time,
                    "yellow_cards_90": actual_yellows,
                    "corners_90": actual_corners,
                    "penalty": actual_penalty,
                },
            })

        participant_spain = participant.get("spain", {})

        first_goal_points = score_spain_first_goal(
            participant_spain.get("first_spain_goal"),
            actual_spain.get("first_spain_goal"),
        )

        first_scorer_points = 0
        if actual_spain.get("first_spain_scorer") is not None:
            if normalize_text(participant_spain.get("first_spain_scorer")) == normalize_text(actual_spain.get("first_spain_scorer")):
                first_scorer_points = 5

        possession_points = 0
        possession_pred = participant_spain.get("spain_possession")
        possession_real = actual_spain.get("spain_possession")
        if possession_real is not None and possession_pred is not None:
            if float(possession_pred) == float(possession_real):
                possession_points = 5
            elif name in possession_bonus_participants:
                possession_points = 3

        spain_points = first_goal_points + first_scorer_points + possession_points
        total_points += spain_points

        leaderboard.append({
            "participant": name,
            "total_points": total_points,
            "match_points": match_points,
            "spain_points": spain_points,
            "spain_detail": {
                "first_spain_goal_points": first_goal_points,
                "first_spain_scorer_points": first_scorer_points,
                "spain_possession_points": possession_points,
                "prediction": {
                    "first_spain_goal": participant_spain.get("first_spain_goal"),
                    "first_spain_goal_label": participant_spain.get("first_spain_goal_label"),
                    "first_spain_scorer": participant_spain.get("first_spain_scorer"),
                    "spain_possession": participant_spain.get("spain_possession"),
                },
                "real": {
                    "first_spain_goal": actual_spain.get("first_spain_goal"),
                    "first_spain_scorer": actual_spain.get("first_spain_scorer"),
                    "spain_possession": actual_spain.get("spain_possession"),
                },
            },
            "match_detail": match_details,
        })

    leaderboard.sort(key=lambda row: row["total_points"], reverse=True)

    for position, row in enumerate(leaderboard, start=1):
        row["position"] = position

    return leaderboard


# ---------- CLI ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Calcula puntos de la porra de octavos.")

    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_FILE),
        help="Fichero con resultados reales. Por defecto: data/octavos/data.json",
    )
    parser.add_argument(
        "--predictions",
        default=str(DEFAULT_PREDICTIONS_FILE),
        help="Fichero con predicciones. Por defecto: data/octavos/predicciones_octavos.json",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Salida JSON. Por defecto: data/octavos/leaderboard_octavos.json",
    )
    parser.add_argument(
        "--possession-tie-mode",
        choices=["include_ties", "top_two"],
        default="include_ties",
        help="Cómo resolver empates entre los dos más cercanos en posesión. Por defecto: include_ties.",
    )

    args = parser.parse_args()

    results_path = Path(args.results)
    predictions_path = Path(args.predictions)
    output_json_path = Path(args.output_json)

    results = load_json(results_path)
    predictions = load_json(predictions_path)

    leaderboard = calculate_points(
        results,
        predictions,
        include_possession_ties=args.possession_tie_mode == "include_ties",
    )
    save_json(leaderboard, output_json_path)

    print("\nCLASIFICACIÓN OCTAVOS")
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
