import json
from pathlib import Path

# -----------------------------
# RUTAS (CLAVE)
# -----------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

RESULTS_FILE = ROOT_DIR / "data" / "final" / "data.json"
PREDICTIONS_FILE = ROOT_DIR / "data" / "final" / "predicciones_final.json"
OUTPUT_FILE = ROOT_DIR / "data" / "final" / "leaderboard_final.json"


# -----------------------------
# HELPERS
# -----------------------------
def outcome(h, a):
    if h > a:
        return "home"
    elif a > h:
        return "away"
    return "draw"


def score_result(ph, pa, ah, aa):
    if ph == ah and pa == aa:
        return 8
    if outcome(ph, pa) == outcome(ah, aa):
        if abs(ph - ah) + abs(pa - aa) == 1:
            return 4
    return 0


def diff_score(pred, real, exact, d1, d2=None):
    diff = abs(pred - real)
    if diff == 0:
        return exact
    if diff == 1:
        return d1
    if d2 is not None and diff == 2:
        return d2
    return 0


# -----------------------------
# MAIN
# -----------------------------
def calculate(results, predictions):

    match = results["match"]
    spain_real = results["spain"]

    ah = match["home_goals_90"]
    aa = match["away_goals_90"]

    leaderboard = []

    for p in predictions["participants"]:

        name = p["mote"]
        pred = p["prediction"]
        sp = p["spain"]

        total = 0
        match_points = 0
        spain_points = 0

        # 1 Campeón
        pts = 10 if pred["champion"] == match["qualified_team"] else 0
        total += pts
        match_points += pts

        # 2 Resultado
        pts = score_result(pred["home_goals_90"], pred["away_goals_90"], ah, aa)
        total += pts
        match_points += pts

        # 3 Decisión
        pts = 5 if pred["decided_in"] == match["decided_in"] else 0
        total += pts
        match_points += pts

        # 4 Descanso
        pts = 4 if pred["half_time_result"] == match["half_time_result"] else 0
        total += pts
        match_points += pts

        # 5 Goles
        pts = diff_score(pred["total_goals"], match["total_goals"], 5, 3, 1)
        total += pts
        match_points += pts

        # 6 Corners
        pts = diff_score(pred["corners"], match["corners"], 4, 2)
        total += pts
        match_points += pts

        # 7 Amarillas
        pts = diff_score(pred["yellow_cards"], match["yellow_cards"], 4, 2)
        total += pts
        match_points += pts

        # 8 Offsides
        pts = diff_score(pred["offsides"], match["offsides"], 3, 1)
        total += pts
        match_points += pts

        # 9 Posesión
        pts = 3 if pred["more_possession"] == match["more_possession"] else 0
        total += pts
        match_points += pts

        # 10 Penalti
        pts = 3 if pred["penalty"] == match["penalty"] else 0
        total += pts
        match_points += pts

        # 11 Roja
        pts = 3 if pred["red_card"] == match["red_card"] else 0
        total += pts
        match_points += pts

        # 12 MVP
        pts = 8 if pred["mvp"] == match["mvp"] else 0
        total += pts
        match_points += pts

        # ----------------
        # ESPAÑA
        # ----------------

        if sp["first_goal_scorer"] == spain_real["first_spain_goal"]:
            spain_points += 6

        if sp["first_assist"] == spain_real["first_assist"]:
            spain_points += 4

        # minuto
        diff = abs(sp["first_goal_minute"] - spain_real["first_goal_minute"])
        if diff == 0:
            spain_points += 6
        elif diff <= 5:
            spain_points += 4
        elif diff <= 10:
            spain_points += 2

        if sp["first_sub_in"] == spain_real["first_sub_in"]:
            spain_points += 4

        if sp["first_sub_out"] == spain_real["first_sub_out"]:
            spain_points += 4

        spain_points += diff_score(sp["spain_goals"], spain_real["spain_goals"], 6, 3)

        total += spain_points

        leaderboard.append({
            "participant": name,
            "total_points": total,
            "match_points": match_points,
            "spain_points": spain_points
        })

    leaderboard.sort(key=lambda x: x["total_points"], reverse=True)

    for i, row in enumerate(leaderboard, 1):
        row["position"] = i

    return leaderboard


# -----------------------------
# EXEC
# -----------------------------
if __name__ == "__main__":

    results = json.load(open(RESULTS_FILE, encoding="utf-8"))
    predictions = json.load(open(PREDICTIONS_FILE, encoding="utf-8"))

    leaderboard = calculate(results, predictions)

    print("\nCLASIFICACION FINAL")
    print("=" * 70)

    for row in leaderboard:
        print(
            f"{row['position']:>2}. {row['participant']} - "
            f"{row['total_points']} pts "
            f"({row['match_points']} partido + {row['spain_points']} España)"
        )

    json.dump(leaderboard, open(OUTPUT_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print(f"\nJSON generado en: {OUTPUT_FILE}")