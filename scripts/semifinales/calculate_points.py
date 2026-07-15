import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

DEFAULT_RESULTS_FILE = ROOT_DIR / "data" / "semifinales" / "data.json"
DEFAULT_PREDICTIONS_FILE = (
    ROOT_DIR / "data" / "semifinales" / "predicciones_semifinales.json"
)
DEFAULT_OUTPUT_JSON = (
    ROOT_DIR / "data" / "semifinales" / "leaderboard_semifinales.json"
)


# -----------------------------------------------------------------------------
# Normalizacion
# -----------------------------------------------------------------------------

def strip_accents(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(char) != "Mn"
    )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = strip_accents(str(value)).lower().strip()
    text = text.replace(".", "").replace("-", " ").replace("_", " ")
    return " ".join(text.split())


def normalize_team(value: Any) -> str:
    key = normalize_text(value)
    aliases = {
        "france": "francia",
        "spain": "espana",
        "england": "inglaterra",
        "argentina": "argentina",
    }
    return aliases.get(key, key)


def normalize_decided_in(value: Any) -> str:
    key = normalize_text(value)
    aliases = {
        "90": "90",
        "90 minutos": "90",
        "90 mins": "90",
        "tiempo reglamentario": "90",
        "regular time": "90",
        "prorroga": "extra_time",
        "extra time": "extra_time",
        "120": "extra_time",
        "120 minutos": "extra_time",
        "penaltis": "penalties",
        "penalti": "penalties",
        "penalties": "penalties",
        "penalty shootout": "penalties",
        "tanda de penaltis": "penalties",
    }
    return aliases.get(key, key)


def normalize_outcome(
    value: Any,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
) -> str:
    """Devuelve home, draw o away."""
    key = normalize_text(value)

    if key in {
        "home", "local", "equipo local", "gana local",
        "gana el equipo local", "victoria local",
    }:
        return "home"
    if key in {
        "away", "visitante", "equipo visitante", "gana visitante",
        "gana el equipo visitante", "victoria visitante",
    }:
        return "away"
    if key in {
        "draw", "empate", "empatados", "empataran", "50 50",
        "50% 50%", "igual",
    }:
        return "draw"

    if home_team and normalize_team(value) == normalize_team(home_team):
        return "home"
    if away_team and normalize_team(value) == normalize_team(away_team):
        return "away"

    return key


def normalize_possession(
    value: Any,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
) -> str:
    return normalize_outcome(value, home_team, away_team)


def normalize_no_goal(value: Any) -> bool:
    key = normalize_text(value)
    return key in {
        "espana no marcara",
        "espana no marca",
        "no marcara",
        "no marca",
        "sin gol",
        "no goal",
        "none",
    }


def parse_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)

    text = normalize_text(value)
    if text.isdigit():
        return int(text)
    return None


def match_key(home_team: str, away_team: str) -> Tuple[str, str]:
    return normalize_team(home_team), normalize_team(away_team)


# -----------------------------------------------------------------------------
# Entrada y salida
# -----------------------------------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_results_index(
    results: Dict[str, Any],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for match in results.get("matches", []):
        index[match_key(match["home_team"], match["away_team"])] = match
    return index


# -----------------------------------------------------------------------------
# Lectura flexible de campos
# -----------------------------------------------------------------------------

def first_present(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def actual_qualified_team(match: Dict[str, Any]) -> Optional[str]:
    value = first_present(
        match, "qualified_team", "classified_team", "winner", "winner_team"
    )
    return str(value) if value not in (None, "") else None


def actual_total_goals(match: Dict[str, Any]) -> Optional[int]:
    explicit = parse_int(match.get("total_goals"))
    if explicit is not None:
        return explicit

    home = parse_int(match.get("home_goals"))
    away = parse_int(match.get("away_goals"))
    if home is None or away is None:
        return None
    return home + away


def actual_half_time_result(match: Dict[str, Any]) -> Optional[str]:
    value = first_present(
        match,
        "half_time_result",
        "halftime_result",
        "half_time",
        "result_at_half_time",
    )
    if value is not None:
        normalized = normalize_outcome(
            value, match.get("home_team"), match.get("away_team")
        )
        return normalized or None

    home = parse_int(first_present(match, "half_time_home_goals", "ht_home_goals"))
    away = parse_int(first_present(match, "half_time_away_goals", "ht_away_goals"))
    if home is None or away is None:
        return None
    return scoreline_outcome(home, away)


def actual_possession(match: Dict[str, Any]) -> Optional[str]:
    value = first_present(
        match,
        "more_possession",
        "most_possession",
        "possession_winner",
        "team_more_possession",
    )
    if value is not None:
        return normalize_possession(
            value, match.get("home_team"), match.get("away_team")
        )

    home = first_present(match, "home_possession", "possession_home")
    away = first_present(match, "away_possession", "possession_away")
    if home is None or away is None:
        return None

    home_value = float(home)
    away_value = float(away)
    if home_value > away_value:
        return "home"
    if away_value > home_value:
        return "away"
    return "draw"


# -----------------------------------------------------------------------------
# Reglas de puntuacion
# -----------------------------------------------------------------------------

def scoreline_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if away_goals > home_goals:
        return "away"
    return "draw"


def score_exact_result(
    predicted_home: Any,
    predicted_away: Any,
    actual_home: Any,
    actual_away: Any,
) -> int:
    """
    Marcador exacto: 5 puntos.
    Mismo ganador/empate y distancia total de un gol: 2 puntos.

    Ejemplo con 2-1 real: 2-0, 3-1 y 1-1 suman 2 puntos.
    """
    ph = parse_int(predicted_home)
    pa = parse_int(predicted_away)
    ah = parse_int(actual_home)
    aa = parse_int(actual_away)

    if None in {ph, pa, ah, aa}:
        return 0
    if ph == ah and pa == aa:
        return 5

    same_outcome = scoreline_outcome(ph, pa) == scoreline_outcome(ah, aa)
    total_distance = abs(ph - ah) + abs(pa - aa)
    if same_outcome and total_distance == 1:
        return 2
    return 0


def score_total_goals(predicted: Any, actual: Any) -> int:
    predicted_value = parse_int(predicted)
    actual_value = parse_int(actual)
    if predicted_value is None or actual_value is None:
        return 0

    difference = abs(predicted_value - actual_value)
    if difference == 0:
        return 3
    if difference == 1:
        return 2
    if difference == 2:
        return 1
    return 0


def score_corners(predicted: Any, actual: Any) -> int:
    predicted_value = parse_int(predicted)
    actual_value = parse_int(actual)
    if predicted_value is None or actual_value is None:
        return 0

    difference = abs(predicted_value - actual_value)
    if difference == 0:
        return 2
    if difference in {1, 2}:
        return 1
    return 0


def score_yellow_cards(predicted: Any, actual: Any) -> int:
    predicted_value = parse_int(predicted)
    actual_value = parse_int(actual)
    if predicted_value is None or actual_value is None:
        return 0

    difference = abs(predicted_value - actual_value)
    if difference == 0:
        return 2
    if difference == 1:
        return 1
    return 0


def score_offsides(predicted: Any, actual: Any) -> int:
    predicted_value = parse_int(predicted)
    actual_value = parse_int(actual)
    if predicted_value is None or actual_value is None:
        return 0

    difference = abs(predicted_value - actual_value)
    if difference == 0:
        return 2
    if difference in {1, 2}:
        return 1
    return 0


def score_first_goal_minute(predicted: Any, actual: Any) -> int:
    """
    Exacto: 3; diferencia 1-5: 2; diferencia 6-10: 1; resto: 0.
    "España no marcara" solo acierta contra la misma respuesta real.
    """
    predicted_no_goal = normalize_no_goal(predicted)
    actual_no_goal = normalize_no_goal(actual)

    if predicted_no_goal or actual_no_goal:
        return 3 if predicted_no_goal and actual_no_goal else 0

    predicted_minute = parse_int(predicted)
    actual_minute = parse_int(actual)
    if predicted_minute is None or actual_minute is None:
        return 0

    difference = abs(predicted_minute - actual_minute)
    if difference == 0:
        return 3
    if difference <= 5:
        return 2
    if difference <= 10:
        return 1
    return 0


# -----------------------------------------------------------------------------
# Calculo principal
# -----------------------------------------------------------------------------

def calculate_points(
    results: Dict[str, Any],
    predictions: Dict[str, Any],
) -> List[Dict[str, Any]]:
    results_index = build_results_index(results)
    actual_spain = results.get("spain", {})
    leaderboard: List[Dict[str, Any]] = []

    for participant in predictions.get("participants", []):
        name = (
            participant.get("mote")
            or participant.get("participant")
            or participant.get("name")
            or "Sin nombre"
        )

        total_points = 0
        match_points = 0
        match_details: List[Dict[str, Any]] = []

        # Contadores de desempate. Se aplican en el orden definido abajo.
        exact_results = 0
        qualified_correct = 0
        exact_total_goals = 0
        exact_corners = 0
        exact_yellow_cards = 0
        exact_offsides = 0

        for predicted_match in participant.get("matches", []):
            key = match_key(
                predicted_match["home_team"], predicted_match["away_team"]
            )
            real_match = results_index.get(key)
            match_name = (
                f"{predicted_match['home_team']} - "
                f"{predicted_match['away_team']}"
            )

            if not real_match:
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Partido no encontrado en data.json",
                })
                continue

            actual_home = parse_int(real_match.get("home_goals"))
            actual_away = parse_int(real_match.get("away_goals"))
            actual_qualified = actual_qualified_team(real_match)
            actual_decided = normalize_decided_in(real_match.get("decided_in"))
            actual_half_time = actual_half_time_result(real_match)
            actual_goals = actual_total_goals(real_match)
            actual_corners = parse_int(real_match.get("corners"))
            actual_yellows = parse_int(
                first_present(real_match, "yellow_cards", "yellowcards")
            )
            actual_offside_count = parse_int(real_match.get("offsides"))
            actual_more_possession = actual_possession(real_match)

            required = {
                "home_goals": actual_home,
                "away_goals": actual_away,
                "qualified_team": actual_qualified,
                "decided_in": actual_decided or None,
                "half_time_result": actual_half_time,
                "total_goals": actual_goals,
                "corners": actual_corners,
                "yellow_cards": actual_yellows,
                "offsides": actual_offside_count,
                "more_possession": actual_more_possession,
            }
            missing = [key_name for key_name, value in required.items() if value is None]
            if missing:
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Campos incompletos en data.json: " + ", ".join(missing),
                })
                continue

            # 1. Seleccion clasificada: 5 puntos
            predicted_qualified = predicted_match.get("predicted_qualified_team")
            qualified_points = 0
            if normalize_team(predicted_qualified) == normalize_team(actual_qualified):
                qualified_points = 5
                qualified_correct += 1

            # 2. Resultado exacto a los 90 minutos: 5 / 2 / 0
            predicted_home = first_present(
                predicted_match,
                "predicted_home_goals_90",
                "predicted_home_goals",
                "home_goals",
            )
            predicted_away = first_present(
                predicted_match,
                "predicted_away_goals_90",
                "predicted_away_goals",
                "away_goals",
            )
            result_points = score_exact_result(
                predicted_home, predicted_away, actual_home, actual_away
            )
            if (
                parse_int(predicted_home) == actual_home
                and parse_int(predicted_away) == actual_away
            ):
                exact_results += 1

            # 3. Momento de decision: 3 puntos
            predicted_decided = normalize_decided_in(
                predicted_match.get("predicted_decided_in")
            )
            decided_points = 3 if predicted_decided == actual_decided else 0

            # 4. Resultado al descanso: 2 puntos
            predicted_half_time = normalize_outcome(
                predicted_match.get("predicted_half_time_result"),
                predicted_match.get("home_team"),
                predicted_match.get("away_team"),
            )
            half_time_points = 2 if predicted_half_time == actual_half_time else 0

            # 5. Goles totales incluyendo prorroga: 3 / 2 / 1 / 0
            predicted_goals = predicted_match.get("predicted_total_goals")
            total_goals_points = score_total_goals(predicted_goals, actual_goals)
            if parse_int(predicted_goals) == actual_goals:
                exact_total_goals += 1

            # 6. Corners: 2 / 1 / 0
            predicted_corners = predicted_match.get("predicted_corners")
            corners_points = score_corners(predicted_corners, actual_corners)
            if parse_int(predicted_corners) == actual_corners:
                exact_corners += 1

            # 7. Tarjetas amarillas: 2 / 1 / 0
            predicted_yellows = predicted_match.get("predicted_yellow_cards")
            yellow_cards_points = score_yellow_cards(
                predicted_yellows, actual_yellows
            )
            if parse_int(predicted_yellows) == actual_yellows:
                exact_yellow_cards += 1

            # 8. Fueras de juego: 2 / 1 / 0
            predicted_offsides = predicted_match.get("predicted_offsides")
            offsides_points = score_offsides(
                predicted_offsides, actual_offside_count
            )
            if parse_int(predicted_offsides) == actual_offside_count:
                exact_offsides += 1

            # 9. Posesion: 1 punto
            predicted_possession = normalize_possession(
                predicted_match.get("predicted_more_possession"),
                predicted_match.get("home_team"),
                predicted_match.get("away_team"),
            )
            possession_points = (
                1 if predicted_possession == actual_more_possession else 0
            )

            points = (
                qualified_points
                + result_points
                + decided_points
                + half_time_points
                + total_goals_points
                + corners_points
                + yellow_cards_points
                + offsides_points
                + possession_points
            )
            match_points += points
            total_points += points

            match_details.append({
                "match": match_name,
                "points": points,
                "qualified_points": qualified_points,
                "exact_result_points": result_points,
                "decided_in_points": decided_points,
                "half_time_points": half_time_points,
                "total_goals_points": total_goals_points,
                "corners_points": corners_points,
                "yellow_cards_points": yellow_cards_points,
                "offsides_points": offsides_points,
                "possession_points": possession_points,
                "prediction": {
                    "qualified_team": predicted_qualified,
                    "home_goals_90": predicted_home,
                    "away_goals_90": predicted_away,
                    "decided_in": predicted_match.get("predicted_decided_in"),
                    "half_time_result": predicted_match.get(
                        "predicted_half_time_result"
                    ),
                    "total_goals": predicted_goals,
                    "corners": predicted_corners,
                    "yellow_cards": predicted_yellows,
                    "offsides": predicted_offsides,
                    "more_possession": predicted_match.get(
                        "predicted_more_possession"
                    ),
                },
                "real": {
                    "qualified_team": actual_qualified,
                    "home_goals_90": actual_home,
                    "away_goals_90": actual_away,
                    "decided_in": actual_decided,
                    "half_time_result": actual_half_time,
                    "total_goals": actual_goals,
                    "corners": actual_corners,
                    "yellow_cards": actual_yellows,
                    "offsides": actual_offside_count,
                    "more_possession": actual_more_possession,
                },
            })

        # Bonus de Espana: maximo 10 puntos
        participant_spain = participant.get("spain", {})

        predicted_first_scorer = first_present(
            participant_spain,
            "first_spain_goal",
            "first_goal_scorer",
            "first_scorer",
        )
        actual_first_scorer = first_present(
            actual_spain,
            "first_spain_goal",
            "first_goal_scorer",
            "first_scorer",
        )
        first_scorer_points = 0
        if actual_first_scorer is not None and normalize_text(
            predicted_first_scorer
        ) == normalize_text(actual_first_scorer):
            first_scorer_points = 3

        predicted_first_assist = participant_spain.get("first_assist")
        actual_first_assist = actual_spain.get("first_assist")
        first_assist_points = 0
        if actual_first_assist is not None and normalize_text(
            predicted_first_assist
        ) == normalize_text(actual_first_assist):
            first_assist_points = 2

        predicted_first_goal_minute = first_present(
            participant_spain,
            "first_goal_minute",
            "first_spain_goal_minute",
            "first_goal_interval",  # compatibilidad con el JSON generado previamente
        )
        actual_first_goal_minute = first_present(
            actual_spain,
            "first_goal_minute",
            "first_spain_goal_minute",
            "first_goal_interval",
        )
        first_goal_minute_points = score_first_goal_minute(
            predicted_first_goal_minute, actual_first_goal_minute
        )

        predicted_mvp = first_present(participant_spain, "spain_mvp", "mvp")
        actual_mvp = first_present(actual_spain, "spain_mvp", "mvp")
        mvp_points = 0
        if actual_mvp is not None and normalize_text(predicted_mvp) == normalize_text(
            actual_mvp
        ):
            mvp_points = 2

        spain_points = (
            first_scorer_points
            + first_assist_points
            + first_goal_minute_points
            + mvp_points
        )
        total_points += spain_points

        leaderboard.append({
            "participant": name,
            "total_points": total_points,
            "match_points": match_points,
            "spain_points": spain_points,
            "tiebreakers": {
                "exact_results": exact_results,
                "qualified_correct": qualified_correct,
                "exact_total_goals": exact_total_goals,
                "exact_corners": exact_corners,
                "exact_yellow_cards": exact_yellow_cards,
                "exact_offsides": exact_offsides,
                "spain_points": spain_points,
            },
            "spain_detail": {
                "first_scorer_points": first_scorer_points,
                "first_assist_points": first_assist_points,
                "first_goal_minute_points": first_goal_minute_points,
                "mvp_points": mvp_points,
                "prediction": {
                    "first_spain_goal": predicted_first_scorer,
                    "first_assist": predicted_first_assist,
                    "first_goal_minute": predicted_first_goal_minute,
                    "mvp": predicted_mvp,
                },
                "real": {
                    "first_spain_goal": actual_first_scorer,
                    "first_assist": actual_first_assist,
                    "first_goal_minute": actual_first_goal_minute,
                    "mvp": actual_mvp,
                },
            },
            "match_detail": match_details,
        })

    # Desempates: puntos, marcadores exactos, clasificados, goles exactos,
    # corners exactos, amarillas exactas, fueras de juego exactos y Espana.
    def sort_key(row: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int, int]:
        tie = row["tiebreakers"]
        return (
            row["total_points"],
            tie["exact_results"],
            tie["qualified_correct"],
            tie["exact_total_goals"],
            tie["exact_corners"],
            tie["exact_yellow_cards"],
            tie["exact_offsides"],
            tie["spain_points"],
        )

    leaderboard.sort(key=sort_key, reverse=True)

    previous_key = None
    previous_position = 0
    for index, row in enumerate(leaderboard, start=1):
        current_key = sort_key(row)
        if current_key == previous_key:
            row["position"] = previous_position
        else:
            row["position"] = index
            previous_position = index
            previous_key = current_key

    return leaderboard


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula los puntos de la Porra Turiel - Semifinales."
    )
    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_FILE),
        help="Resultados reales. Por defecto: data.json junto al script.",
    )
    parser.add_argument(
        "--predictions",
        default=str(DEFAULT_PREDICTIONS_FILE),
        help=(
            "Predicciones. Por defecto: predicciones_semifinales.json "
            "junto al script."
        ),
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help=(
            "JSON de salida. Por defecto: leaderboard_semifinales.json "
            "junto al script."
        ),
    )
    args = parser.parse_args()

    results_path = Path(args.results)
    predictions_path = Path(args.predictions)
    output_path = Path(args.output_json)

    results = load_json(results_path)
    predictions = load_json(predictions_path)
    leaderboard = calculate_points(results, predictions)
    save_json(leaderboard, output_path)

    print("\nCLASIFICACION SEMIFINALES")
    print("=" * 72)
    for row in leaderboard:
        tie = row["tiebreakers"]
        print(
            f"{row['position']:>2}. {row['participant']} - "
            f"{row['total_points']} pts "
            f"({row['match_points']} partidos + {row['spain_points']} Espana) "
            f"| desempate: marcadores exactos {tie['exact_results']}, "
            f"clasificados {tie['qualified_correct']}, "
            f"goles exactos {tie['exact_total_goals']}, "
            f"corners exactos {tie['exact_corners']}, "
            f"amarillas exactas {tie['exact_yellow_cards']}, "
            f"fueras de juego exactos {tie['exact_offsides']}"
        )

    print(f"\nJSON generado: {output_path.resolve()}")


if __name__ == "__main__":
    main()
