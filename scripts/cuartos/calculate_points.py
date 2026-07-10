import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_RESULTS_FILE = BASE_DIR / "data" / "cuartos" / "data.json"
DEFAULT_PREDICTIONS_FILE = BASE_DIR / "data" / "cuartos" / "predicciones_cuartos.json"
DEFAULT_OUTPUT_JSON = BASE_DIR / "data" / "cuartos" / "leaderboard_cuartos.json"


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
        "england": "inglaterra",
        "spain": "espana",
        "belgium": "belgica",
        "switzerland": "suiza",
        "morocco": "marruecos",
        "france": "francia",
        "argentina": "argentina",
        "norway": "noruega",
    }
    return aliases.get(text, text)


def normalize_decided_in(value: Any) -> str:
    """Normaliza el momento en que se decidió el partido."""
    key = normalize_text(value)

    aliases = {
        "90": "90",
        "90 minutos": "90",
        "90 mins": "90",
        "tiempo reglamentario": "90",
        "regular time": "90",

        "prorroga": "extra_time",
        "extra time": "extra_time",
        "extra_time": "extra_time",
        "120": "extra_time",
        "120 minutos": "extra_time",

        "penaltis": "penalties",
        "penalti": "penalties",
        "penalties": "penalties",
        "penalty shootout": "penalties",
        "tanda de penaltis": "penalties",
    }
    return aliases.get(key, key)


def normalize_possession(
    value: Any,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
) -> str:
    """
    Devuelve: home, away o draw.

    Acepta nombres de equipos, local/visitante, home/away y empate.
    """
    key = normalize_text(value)

    if key in {"home", "local", "equipo local", "gana local"}:
        return "home"
    if key in {"away", "visitante", "equipo visitante", "gana visitante"}:
        return "away"
    if key in {
        "draw", "empate", "empatados", "empataran", "empatarán",
        "50 50", "50% 50%", "igual posesion", "igual posesión"
    }:
        return "draw"

    if home_team and normalize_team(value) == normalize_team(home_team):
        return "home"
    if away_team and normalize_team(value) == normalize_team(away_team):
        return "away"

    return key


def normalize_third_substitution(value: Any) -> Optional[int]:
    """
    Convierte la respuesta del tercer cambio en una categoría ordenada:

    1 = Entre el minuto 0 y la primera pausa de hidratación
    2 = Entre la primera pausa de hidratación y el descanso
    3 = Entre el descanso y la segunda pausa de hidratación
    4 = Entre la segunda pausa de hidratación y el final del partido
    5 = Prórroga
    6 = No habrá tercer cambio
    """
    if value is None:
        return None

    if isinstance(value, int):
        return value if 1 <= value <= 6 else None

    key = normalize_text(value)

    direct = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "prorroga": 5,
        "extra time": 5,
        "no habra tercer cambio": 6,
        "no habra un tercer cambio": 6,
        "sin tercer cambio": 6,
    }
    if key in direct:
        return direct[key]

    if "minuto 0" in key and "primera pausa" in key:
        return 1
    if "primera pausa" in key and "descanso" in key:
        return 2
    if "descanso" in key and "segunda pausa" in key:
        return 3
    if "segunda pausa" in key and (
        "final del partido" in key or "90 mins" in key or "90 minutos" in key
    ):
        return 4
    if "prorroga" in key:
        return 5
    if "no habra" in key and "tercer cambio" in key:
        return 6

    return None


def match_key(home_team: str, away_team: str) -> Tuple[str, str]:
    return normalize_team(home_team), normalize_team(away_team)


# ---------- Entrada y salida ----------

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_results_index(
    results: Dict[str, Any],
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index = {}
    for match in results.get("matches", []):
        index[match_key(match["home_team"], match["away_team"])] = match
    return index


# ---------- Valores reales ----------

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

    # Si hay empate, debe indicarse qualified_team.
    return None


def get_total_goals(match: Dict[str, Any]) -> Optional[int]:
    if match.get("total_goals") is not None:
        return int(match["total_goals"])

    home_goals = match.get("home_goals")
    away_goals = match.get("away_goals")

    if home_goals is None or away_goals is None:
        return None

    return int(home_goals) + int(away_goals)


def get_actual_decided_in(match: Dict[str, Any]) -> Optional[str]:
    value = match.get("decided_in")
    if value is None:
        return None
    normalized = normalize_decided_in(value)
    return normalized or None


def get_actual_possession(match: Dict[str, Any]) -> Optional[str]:
    for key in (
        "more_possession",
        "most_possession",
        "possession_winner",
        "team_more_possession",
    ):
        if match.get(key) is not None:
            return normalize_possession(
                match[key],
                match.get("home_team"),
                match.get("away_team"),
            )

    home_possession = match.get("home_possession")
    away_possession = match.get("away_possession")

    if home_possession is None or away_possession is None:
        return None

    home = float(home_possession)
    away = float(away_possession)

    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"


# ---------- Reglas de puntuación ----------

def score_total_goals(predicted: Any, actual: Any) -> int:
    """Exacto 3; diferencia 1 => 2; diferencia 2 => 1; resto 0."""
    if predicted is None or actual is None:
        return 0

    difference = abs(int(predicted) - int(actual))

    if difference == 0:
        return 3
    if difference == 1:
        return 2
    if difference == 2:
        return 1
    return 0


def score_offsides(predicted: Any, actual: Any) -> int:
    """Exacto 2; diferencia 1 o 2 => 1; resto 0."""
    if predicted is None or actual is None:
        return 0

    difference = abs(int(predicted) - int(actual))

    if difference == 0:
        return 2
    if difference in {1, 2}:
        return 1
    return 0


def score_third_substitution(predicted: Any, actual: Any) -> int:
    """
    Exacto 5; franja inmediatamente anterior/posterior 3; resto 0.

    'No habrá tercer cambio' solo puntúa si se acierta exactamente.
    """
    predicted_category = normalize_third_substitution(predicted)
    actual_category = normalize_third_substitution(actual)

    if predicted_category is None or actual_category is None:
        return 0

    if predicted_category == actual_category:
        return 5

    if 6 in {predicted_category, actual_category}:
        return 0

    if abs(predicted_category - actual_category) == 1:
        return 3

    return 0


# ---------- Cálculo principal ----------

def calculate_points(
    results: Dict[str, Any],
    predictions: Dict[str, Any],
) -> List[Dict[str, Any]]:
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

        # Desempates adaptados a las preguntas de cuartos.
        qualified_correct = 0
        exact_total_goals = 0
        decided_in_correct = 0
        exact_offsides = 0
        possession_correct = 0

        for pred_match in participant.get("matches", []):
            key = match_key(
                pred_match["home_team"],
                pred_match["away_team"],
            )
            real_match = results_index.get(key)
            match_name = (
                f"{pred_match['home_team']} - "
                f"{pred_match['away_team']}"
            )

            if not real_match:
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": "Partido no encontrado en data.json",
                })
                continue

            actual_qualified = get_qualified_team(real_match)
            actual_total_goals = get_total_goals(real_match)
            actual_decided_in = get_actual_decided_in(real_match)
            actual_offsides = real_match.get("offsides")
            actual_possession = get_actual_possession(real_match)

            required_fields = [
                actual_qualified,
                actual_total_goals,
                actual_decided_in,
                actual_offsides,
                actual_possession,
            ]

            if any(value is None for value in required_fields):
                match_details.append({
                    "match": match_name,
                    "points": 0,
                    "warning": (
                        "Partido pendiente o con campos incompletos "
                        "en data.json"
                    ),
                })
                continue

            # 1. Clasificado: 5 puntos
            points_qualified = 0
            if normalize_team(
                pred_match.get("predicted_qualified_team")
            ) == normalize_team(actual_qualified):
                points_qualified = 5
                qualified_correct += 1

            # 2. Goles totales: máximo 3 puntos
            predicted_total_goals = pred_match.get(
                "predicted_total_goals"
            )
            points_total_goals = score_total_goals(
                predicted_total_goals,
                actual_total_goals,
            )
            if (
                predicted_total_goals is not None
                and int(predicted_total_goals) == int(actual_total_goals)
            ):
                exact_total_goals += 1

            # 3. Cuándo se decide: 3 puntos
            predicted_decided_in = normalize_decided_in(
                pred_match.get("predicted_decided_in")
            )
            points_decided_in = 0
            if predicted_decided_in == actual_decided_in:
                points_decided_in = 3
                decided_in_correct += 1

            # 4. Fueras de juego: máximo 2 puntos
            predicted_offsides = pred_match.get("predicted_offsides")
            points_offsides = score_offsides(
                predicted_offsides,
                actual_offsides,
            )
            if (
                predicted_offsides is not None
                and int(predicted_offsides) == int(actual_offsides)
            ):
                exact_offsides += 1

            # 5. Más posesión: 2 puntos
            predicted_possession = normalize_possession(
                pred_match.get("predicted_more_possession"),
                pred_match.get("home_team"),
                pred_match.get("away_team"),
            )
            points_possession = 0
            if predicted_possession == actual_possession:
                points_possession = 2
                possession_correct += 1

            points = (
                points_qualified
                + points_total_goals
                + points_decided_in
                + points_offsides
                + points_possession
            )

            match_points += points
            total_points += points

            match_details.append({
                "match": match_name,
                "points": points,
                "qualified_points": points_qualified,
                "total_goals_points": points_total_goals,
                "decided_in_points": points_decided_in,
                "offsides_points": points_offsides,
                "possession_points": points_possession,
                "prediction": {
                    "qualified_team": pred_match.get(
                        "predicted_qualified_team"
                    ),
                    "total_goals": predicted_total_goals,
                    "decided_in": pred_match.get(
                        "predicted_decided_in"
                    ),
                    "offsides": predicted_offsides,
                    "more_possession": pred_match.get(
                        "predicted_more_possession"
                    ),
                },
                "real": {
                    "qualified_team": actual_qualified,
                    "total_goals": actual_total_goals,
                    "decided_in": actual_decided_in,
                    "offsides": actual_offsides,
                    "more_possession": actual_possession,
                },
            })

        # ---------- Bonus España ----------

        participant_spain = participant.get("spain", {})

        third_substitution_points = score_third_substitution(
            participant_spain.get("third_substitution"),
            actual_spain.get("third_substitution"),
        )

        first_assist_points = 0
        if actual_spain.get("first_assist") is not None:
            if normalize_text(
                participant_spain.get("first_assist")
            ) == normalize_text(actual_spain.get("first_assist")):
                first_assist_points = 3

        mvp_points = 0
        if actual_spain.get("mvp") is not None:
            if normalize_text(
                participant_spain.get("mvp")
            ) == normalize_text(actual_spain.get("mvp")):
                mvp_points = 2

        spain_points = (
            third_substitution_points
            + first_assist_points
            + mvp_points
        )
        total_points += spain_points

        leaderboard.append({
            "participant": name,
            "total_points": total_points,
            "match_points": match_points,
            "spain_points": spain_points,
            "tiebreakers": {
                "qualified_correct": qualified_correct,
                "exact_total_goals": exact_total_goals,
                "decided_in_correct": decided_in_correct,
                "exact_offsides": exact_offsides,
                "possession_correct": possession_correct,
                "spain_points": spain_points,
            },
            "spain_detail": {
                "third_substitution_points": third_substitution_points,
                "first_assist_points": first_assist_points,
                "mvp_points": mvp_points,
                "prediction": {
                    "third_substitution": participant_spain.get(
                        "third_substitution"
                    ),
                    "first_assist": participant_spain.get(
                        "first_assist"
                    ),
                    "mvp": participant_spain.get("mvp"),
                },
                "real": {
                    "third_substitution": actual_spain.get(
                        "third_substitution"
                    ),
                    "first_assist": actual_spain.get("first_assist"),
                    "mvp": actual_spain.get("mvp"),
                },
            },
            "match_detail": match_details,
        })

    def sort_key(row: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int]:
        tiebreakers = row.get("tiebreakers", {})
        return (
            row["total_points"],
            tiebreakers.get("qualified_correct", 0),
            tiebreakers.get("exact_total_goals", 0),
            tiebreakers.get("decided_in_correct", 0),
            tiebreakers.get("exact_offsides", 0),
            tiebreakers.get("possession_correct", 0),
            tiebreakers.get("spain_points", 0),
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


# ---------- CLI ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calcula los puntos de la porra de cuartos."
    )

    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_FILE),
        help=(
            "Fichero con resultados reales. "
            "Por defecto: data/cuartos/data.json"
        ),
    )
    parser.add_argument(
        "--predictions",
        default=str(DEFAULT_PREDICTIONS_FILE),
        help=(
            "Fichero con predicciones. "
            "Por defecto: data/cuartos/predicciones_cuartos.json"
        ),
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help=(
            "Salida JSON. "
            "Por defecto: data/cuartos/leaderboard_cuartos.json"
        ),
    )

    args = parser.parse_args()

    results_path = Path(args.results)
    predictions_path = Path(args.predictions)
    output_json_path = Path(args.output_json)

    results = load_json(results_path)
    predictions = load_json(predictions_path)

    leaderboard = calculate_points(results, predictions)
    save_json(leaderboard, output_json_path)

    print("\nCLASIFICACIÓN CUARTOS")
    print("=" * 50)

    for row in leaderboard:
        tiebreakers = row["tiebreakers"]

        print(
            f"{row['position']:>2}. {row['participant']} - "
            f"{row['total_points']} pts "
            f"({row['match_points']} partidos + "
            f"{row['spain_points']} España) "
            f"| desempate: "
            f"clasificados {tiebreakers['qualified_correct']}, "
            f"goles exactos {tiebreakers['exact_total_goals']}, "
            f"momento exacto {tiebreakers['decided_in_correct']}, "
            f"fueras de juego exactos {tiebreakers['exact_offsides']}, "
            f"posesión {tiebreakers['possession_correct']}, "
            f"España {tiebreakers['spain_points']}"
        )

    print(f"\nJSON generado: {output_json_path.resolve()}")


if __name__ == "__main__":
    main()
