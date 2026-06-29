import json
import unicodedata
from datetime import datetime
from pathlib import Path


PREDICTIONS_FILE = Path("data") / "predictions.json"
STANDINGS_FILE = Path("data") / "standings.json"
SPAIN_ANSWERS_FILE = Path("data") / "spain_answers.json"
OUTPUT_FILE = Path("data") / "results.json"

GROUPS = list("ABCDEFGHIJKL")


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value


def normalize_player_name(value):
    """
    Convierte:
    'Ferran Torres (FC Barcelona)' -> 'ferran torres'
    """
    if value is None:
        return ""

    value = str(value).strip()

    if "(" in value:
        value = value.split("(")[0].strip()

    return normalize_text(value)


def score_group(predicted_group, real_group):
    points = 0

    detail = {
        "classified_teams_points": 0,
        "classified_bonus_points": 0,
        "exact_order_points": 0,
        "third_place_points": 0,
        "fourth_place_points": 0,
        "total": 0,
        "real_order": [],
        "predicted_order": [],
    }

    real_order = [team["team"] for team in real_group]
    predicted_order = [item["team"] for item in predicted_group]

    detail["real_order"] = real_order
    detail["predicted_order"] = predicted_order

    real_top_2 = set(real_order[:2])
    predicted_top_2 = set(predicted_order[:2])

    matched_classified = real_top_2.intersection(predicted_top_2)

    classified_points = len(matched_classified) * 2
    points += classified_points
    detail["classified_teams_points"] = classified_points

    if predicted_top_2 == real_top_2:
        points += 1
        detail["classified_bonus_points"] = 1

        if predicted_order[:2] == real_order[:2]:
            points += 3
            detail["exact_order_points"] = 3

    if len(predicted_order) >= 3 and predicted_order[2] == real_order[2]:
        points += 1
        detail["third_place_points"] = 1

    if len(predicted_order) >= 4 and predicted_order[3] == real_order[3]:
        points += 1
        detail["fourth_place_points"] = 1

    detail["total"] = min(points, 10)
    return detail


def get_exact_or_nearest_points(participants, question_key, real_value):
    scores = {}
    distances = {}

    for participant in participants:
        name = participant["name"]
        predicted_value = participant.get("spain_questions", {}).get(question_key)

        try:
            predicted_value = int(predicted_value)
            real_value_int = int(real_value)
        except (TypeError, ValueError):
            scores[name] = 0
            continue

        if predicted_value == real_value_int:
            scores[name] = 10
        else:
            scores[name] = 0
            distances[name] = abs(predicted_value - real_value_int)

    if any(score == 10 for score in scores.values()):
        return scores

    if not distances:
        return scores

    min_distance = min(distances.values())

    for name, distance in distances.items():
        if distance == min_distance:
            scores[name] = 5

    return scores


def calculate_spain_question_scores(participants, spain_answers):
    spain = spain_answers["spain"]

    real_top_scorers = {
        normalize_player_name(player)
        for player in spain.get("top_scorers", [])
    }

    real_top_assistants = {
        normalize_player_name(player)
        for player in spain.get("top_assistants", [])
    }

    goals_for_scores = get_exact_or_nearest_points(
        participants,
        "goals_for",
        spain.get("goals_for"),
    )

    goals_against_scores = get_exact_or_nearest_points(
        participants,
        "goals_against",
        spain.get("goals_against"),
    )

    result = {}

    for participant in participants:
        name = participant["name"]
        questions = participant.get("spain_questions", {})

        predicted_scorer = normalize_player_name(questions.get("top_scorer"))
        predicted_assistant = normalize_player_name(questions.get("top_assistant"))

        top_scorer_points = 5 if predicted_scorer in real_top_scorers else 0
        top_assistant_points = 5 if predicted_assistant in real_top_assistants else 0

        result[name] = {
            "top_scorer": {
                "prediction": questions.get("top_scorer"),
                "real": spain.get("top_scorers", []),
                "points": top_scorer_points,
            },
            "top_assistant": {
                "prediction": questions.get("top_assistant"),
                "real": spain.get("top_assistants", []),
                "points": top_assistant_points,
            },
            "goals_for": {
                "prediction": questions.get("goals_for"),
                "real": spain.get("goals_for"),
                "points": goals_for_scores.get(name, 0),
            },
            "goals_against": {
                "prediction": questions.get("goals_against"),
                "real": spain.get("goals_against"),
                "points": goals_against_scores.get(name, 0),
            },
        }

        result[name]["total"] = (
            result[name]["top_scorer"]["points"]
            + result[name]["top_assistant"]["points"]
            + result[name]["goals_for"]["points"]
            + result[name]["goals_against"]["points"]
        )

    return result


def calculate_results():
    predictions = read_json(PREDICTIONS_FILE)
    standings = read_json(STANDINGS_FILE)
    spain_answers = read_json(SPAIN_ANSWERS_FILE)

    participants = predictions["participants"]
    real_groups = standings["groups"]

    spain_scores = calculate_spain_question_scores(participants, spain_answers)

    participant_results = []

    for participant in participants:
        name = participant["name"]

        group_details = {}
        group_total = 0

        for group_name in GROUPS:
            predicted_group = participant["groups"][group_name]
            real_group = real_groups[group_name]

            detail = score_group(predicted_group, real_group)
            group_details[group_name] = detail
            group_total += detail["total"]

        spain_total = spain_scores[name]["total"]
        total = group_total + spain_total

        participant_results.append({
            "name": name,
            "total_points": total,
            "group_points": group_total,
            "spain_points": spain_total,
            "groups": group_details,
            "spain_questions": spain_scores[name],
        })

    participant_results.sort(
        key=lambda item: (
            item["total_points"],
            item["group_points"],
            item["spain_points"],
        ),
        reverse=True,
    )

    for index, participant in enumerate(participant_results, start=1):
        participant["rank"] = index

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {
            "predictions": str(PREDICTIONS_FILE),
            "standings": str(STANDINGS_FILE),
            "spain_answers": str(SPAIN_ANSWERS_FILE),
        },
        "scoring_rules": {
            "group": {
                "classified_team_each": 2,
                "both_classified_bonus": 1,
                "exact_order": 3,
                "third_place": 1,
                "fourth_place": 1,
                "max_per_group": 10,
            },
            "spain_questions": {
                "top_scorer": 5,
                "top_assistant": 5,
                "goals_for_exact": 10,
                "goals_for_nearest": 5,
                "goals_against_exact": 10,
                "goals_against_nearest": 5,
            },
        },
        "ranking": participant_results,
    }


def main():
    results = calculate_results()
    write_json(OUTPUT_FILE, results)

    print(f"Fichero generado: {OUTPUT_FILE}")
    print("\nClasificación general:")

    for participant in results["ranking"]:
        print(
            f'{participant["rank"]}. {participant["name"]} - '
            f'{participant["total_points"]} pts '
            f'({participant["group_points"]} grupos + '
            f'{participant["spain_points"]} España)'
        )


if __name__ == "__main__":
    main()