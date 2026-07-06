import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "docs"
OUTPUT_FILE = PUBLIC_DIR / "index.html"

# Fase de grupos, congelada / estatica
GROUP_STAGE_DIR = DATA_DIR / "fase_grupos"
GROUP_STAGE_RESULTS_FILE = GROUP_STAGE_DIR / "results.json"
GROUP_STAGE_STANDINGS_FILE = GROUP_STAGE_DIR / "standings.json"

# Dieciseisavos, congelado / estatico
R32_DIR = DATA_DIR / "dieciseisavos"
R32_LEADERBOARD_FILE = R32_DIR / "leaderboard_dieciseisavos.json"
R32_RESULTS_FILE = R32_DIR / "data.json"

# Octavos, dinamico
R16_DIR = DATA_DIR / "octavos"
R16_LEADERBOARD_FILE = R16_DIR / "leaderboard_octavos.json"
R16_RESULTS_FILE = R16_DIR / "data.json"


TEAM_ES = {
    "Mexico": "México",
    "South Africa": "Sudáfrica",
    "South Korea": "República de Corea",
    "Czech Republic": "Chequia",
    "Canada": "Canadá",
    "Bosnia and Herzegovina": "Bosnia Herzegovina",
    "Qatar": "Catar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Scotland": "Escocia",
    "United States": "Estados Unidos",
    "Paraguay": "Paraguay",
    "Australia": "Australia",
    "Turkey": "Turquía",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Ivory Coast": "Costa de Marfil",
    "Ecuador": "Ecuador",
    "Netherlands": "Países Bajos",
    "Japan": "Japón",
    "Sweden": "Suecia",
    "Tunisia": "Túnez",
    "Belgium": "Bélgica",
    "Egypt": "Egipto",
    "Iran": "Irán",
    "New Zealand": "Nueva Zelanda",
    "Spain": "España",
    "Cape Verde": "Cabo Verde",
    "Saudi Arabia": "Arabia Saudí",
    "Uruguay": "Uruguay",
    "France": "Francia",
    "Senegal": "Senegal",
    "Iraq": "Irak",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Algeria": "Argelia",
    "Austria": "Austria",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "Democratic Republic of the Congo": "R.D. del Congo",
    "Uzbekistan": "Uzbekistán",
    "Colombia": "Colombia",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Ghana": "Ghana",
    "Panama": "Panamá",
}

DECISION_ES = {
    None: "Pendiente",
    "90": "90 minutos",
    "extra_time": "Prórroga",
    "penalties": "Penaltis",
    "prorroga": "Prórroga",
    "prórroga": "Prórroga",
    "penaltis": "Penaltis",
}

SPAIN_GOAL_WINDOWS = {
    None: "Pendiente",
    0: "No marcará",
    1: "Entre el minuto 0 y la primera pausa de hidratación",
    2: "Entre la primera pausa de hidratación y el descanso",
    3: "Entre el descanso y la segunda pausa de hidratación",
    4: "Entre la segunda pausa de hidratación y el final de los 90 minutos",
    5: "En la prórroga",
    6: "En los penaltis",
    "0": "No marcará",
    "1": "Entre el minuto 0 y la primera pausa de hidratación",
    "2": "Entre la primera pausa de hidratación y el descanso",
    "3": "Entre el descanso y la segunda pausa de hidratación",
    "4": "Entre la segunda pausa de hidratación y el final de los 90 minutos",
    "5": "En la prórroga",
    "6": "En los penaltis",
}


HALF_TIME_ES = {
    None: "Pendiente",
    "home": "Gana el equipo local",
    "draw": "Empate",
    "away": "Gana el equipo visitante",
    "1": "Gana el equipo local",
    "x": "Empate",
    "2": "Gana el equipo visitante",
}

PENALTY_ES = {
    None: "Pendiente",
    True: "Sí",
    False: "No",
    "true": "Sí",
    "false": "No",
    "si": "Sí",
    "sí": "Sí",
    "no": "No",
}


def half_time_label(value: Any) -> str:
    if value is None:
        return "Pendiente"
    return HALF_TIME_ES.get(value, HALF_TIME_ES.get(str(value).lower(), str(value)))


def penalty_label(value: Any) -> str:
    if value is None:
        return "Pendiente"
    if isinstance(value, bool):
        return PENALTY_ES[value]
    return PENALTY_ES.get(str(value).lower(), str(value))


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        print(f"Aviso: no existe {path}. Se usará valor vacío.")
        return default
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def team_es(team: Any) -> str:
    if team is None:
        return "-"
    return TEAM_ES.get(str(team), str(team))


def enrich_group_stage_leaderboard(results: Dict[str, Any]) -> Dict[str, Any]:
    """Mantiene la fase de grupos estatica, pero añade nombres en español para pintarla mejor."""
    ranking = results.get("ranking", [])
    for participant in ranking:
        participant["display_name"] = participant.get("name") or participant.get("participant")
        for group in participant.get("groups", {}).values():
            group["real_order_es"] = [team_es(t) for t in group.get("real_order", [])]
            group["predicted_order_es"] = [team_es(t) for t in group.get("predicted_order", [])]
    return results


def enrich_standings(standings: Dict[str, Any]) -> Dict[str, Any]:
    for teams in standings.get("groups", {}).values():
        for team in teams:
            team["team_es"] = team_es(team.get("team"))
    return standings


def enrich_r32_leaderboard(leaderboard: List[Dict[str, Any]], r32_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    for idx, row in enumerate(leaderboard, start=1):
        row.setdefault("position", idx)
        row["display_name"] = row.get("participant") or row.get("name") or "Sin nombre"

        for detail in row.get("match_detail", []):
            detail["decision_label"] = DECISION_ES.get(detail.get("real", {}).get("decided_in"), detail.get("real", {}).get("decided_in", "Pendiente"))
            prediction = detail.get("prediction", {})
            real = detail.get("real", {})
            prediction["winner_es"] = team_es(prediction.get("winner"))
            real["winner_es"] = team_es(real.get("winner"))
            prediction["decided_in_es"] = DECISION_ES.get(prediction.get("decided_in"), prediction.get("decided_in", "-"))
            real["decided_in_es"] = DECISION_ES.get(real.get("decided_in"), real.get("decided_in", "-"))

        spain_detail = row.get("spain_detail", {})
        prediction = spain_detail.get("prediction", {})
        real = spain_detail.get("real", {})
        prediction["first_spain_goal_label"] = SPAIN_GOAL_WINDOWS.get(prediction.get("first_spain_goal"), prediction.get("first_spain_goal", "-"))
        real["first_spain_goal_label"] = SPAIN_GOAL_WINDOWS.get(real.get("first_spain_goal"), real.get("first_spain_goal", "-"))
    return leaderboard


def enrich_r16_leaderboard(leaderboard: List[Dict[str, Any]], r16_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    for idx, row in enumerate(leaderboard, start=1):
        row.setdefault("position", idx)
        row["display_name"] = row.get("participant") or row.get("name") or "Sin nombre"

        for detail in row.get("match_detail", []):
            prediction = detail.get("prediction", {})
            real = detail.get("real", {})

            prediction["qualified_team_es"] = team_es(prediction.get("qualified_team"))
            real["qualified_team_es"] = team_es(real.get("qualified_team"))

            prediction["half_time_result_es"] = half_time_label(prediction.get("half_time_result"))
            real["half_time_result_es"] = half_time_label(real.get("half_time_result"))

            prediction["penalty_es"] = penalty_label(prediction.get("penalty"))
            real["penalty_es"] = penalty_label(real.get("penalty"))

        spain_detail = row.get("spain_detail", {})
        prediction = spain_detail.get("prediction", {})
        real = spain_detail.get("real", {})
        prediction["first_spain_goal_label"] = SPAIN_GOAL_WINDOWS.get(prediction.get("first_spain_goal"), prediction.get("first_spain_goal", "-"))
        real["first_spain_goal_label"] = SPAIN_GOAL_WINDOWS.get(real.get("first_spain_goal"), real.get("first_spain_goal", "-"))
    return leaderboard


def build_app_data() -> Dict[str, Any]:
    group_results = read_json(GROUP_STAGE_RESULTS_FILE, {"ranking": []})
    group_standings = read_json(GROUP_STAGE_STANDINGS_FILE, {"groups": {}})

    r32_leaderboard = read_json(R32_LEADERBOARD_FILE, [])
    r32_results = read_json(R32_RESULTS_FILE, {"round": "R32", "spain": {}, "matches": []})

    r16_leaderboard = read_json(R16_LEADERBOARD_FILE, [])
    r16_results = read_json(R16_RESULTS_FILE, {"round": "R16", "spain": {}, "matches": []})

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    return {
        "group_stage": {
            "results": enrich_group_stage_leaderboard(group_results),
            "standings": enrich_standings(group_standings),
        },
        "r32": {
            "leaderboard": enrich_r32_leaderboard(r32_leaderboard, r32_results),
            "results": {
              **r32_results,
              "generated_at": generated_at,
            },
        },
        "r16": {
            "leaderboard": enrich_r16_leaderboard(r16_leaderboard, r16_results),
            "results": {
              **r16_results,
              "generated_at": generated_at,
            },
        },
    }


def generate_html(app_data: Dict[str, Any]) -> str:
    app_json = safe_json(app_data)
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>La Porra Turiel 2026</title>

  <style>
    :root {{
      --bg: #061014;
      --bg2: #0b1d24;
      --card: rgba(10, 25, 31, 0.92);
      --card2: rgba(17, 39, 49, 0.92);
      --gold: #f5b942;
      --gold2: #ffd978;
      --green: #32d17d;
      --red: #ff6b6b;
      --muted: #9fb3bd;
      --text: #f7f0df;
      --border: rgba(245, 185, 66, 0.35);
      --shadow: rgba(0, 0, 0, 0.35);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top, rgba(245, 185, 66, 0.16), transparent 35%),
        linear-gradient(180deg, #061014 0%, #0b1d24 45%, #05090c 100%);
      color: var(--text);
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
      background-size: 36px 36px;
      opacity: 0.35;
    }}

    .container {{
      width: min(1180px, calc(100% - 28px));
      margin: 0 auto;
      position: relative;
      z-index: 1;
    }}

    .hero {{
      min-height: 58vh;
      display: flex;
      align-items: center;
      padding: 48px 0 28px;
      text-align: center;
    }}

    .hero-card {{
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 42px 24px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)),
        radial-gradient(circle at center, rgba(245, 185, 66, 0.16), transparent 45%),
        var(--card);
      box-shadow: 0 22px 80px var(--shadow);
      overflow: hidden;
      position: relative;
    }}

    .hero-card::before {{
      content: "🏆";
      position: absolute;
      font-size: 220px;
      opacity: 0.055;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -45%);
    }}

    .eyebrow {{
      color: var(--gold2);
      letter-spacing: 0.22em;
      text-transform: uppercase;
      font-weight: 800;
      font-size: 0.82rem;
      margin-bottom: 16px;
    }}

    h1 {{
      font-size: clamp(3rem, 10vw, 7.5rem);
      line-height: 0.92;
      margin: 0;
      text-transform: uppercase;
      letter-spacing: -0.06em;
      text-shadow: 0 8px 22px rgba(0,0,0,0.65);
    }}

    .subtitle {{
      margin-top: 18px;
      color: var(--gold);
      font-size: clamp(1rem, 3vw, 1.45rem);
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .hero-stats {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin: 32px auto 0;
      max-width: 860px;
    }}

    .stat {{
      background: rgba(0,0,0,0.24);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 18px;
      padding: 16px;
    }}

    .stat strong {{
      display: block;
      font-size: 1.8rem;
      color: var(--gold2);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .stat span {{ color: var(--muted); font-size: 0.9rem; }}

    .tabs-bar {{
      position: sticky;
      top: 0;
      z-index: 5;
      backdrop-filter: blur(12px);
      background: rgba(5, 12, 16, 0.88);
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}

    .tabs-inner {{ display: flex; gap: 10px; overflow-x: auto; padding: 10px 0; }}

    .tab-button, .nav-link {{
      color: var(--text);
      text-decoration: none;
      white-space: nowrap;
      padding: 10px 14px;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 999px;
      background: rgba(255,255,255,0.04);
      font-weight: 800;
      font-size: 0.9rem;
      cursor: pointer;
    }}

    .tab-button.active {{
      background: rgba(245,185,66,0.18);
      color: var(--gold2);
      border-color: var(--border);
    }}

    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}

    section {{ padding: 34px 0; }}

    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 18px;
    }}

    h2 {{
      font-size: clamp(1.7rem, 4vw, 2.6rem);
      margin: 0;
      color: var(--gold2);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    h3 {{ margin-top: 0; }}

    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 13px;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--gold2);
      background: rgba(245,185,66,0.08);
      font-size: 0.88rem;
      font-weight: 800;
    }}

    .breakdown {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    .breakdown span {{
      background: rgba(255,255,255,0.06);
      color: var(--muted);
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 800;
    }}

    .table-wrap {{
      overflow-x: auto;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: var(--card);
    }}

    table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
    th, td {{ padding: 13px 14px; border-bottom: 1px solid rgba(255,255,255,0.07); text-align: left; }}
    th {{ color: var(--gold2); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; background: rgba(245,185,66,0.07); }}
    tr:hover td {{ background: rgba(255,255,255,0.035); }}

    .eliminated-row td {{
      background: rgba(255, 107, 107, 0.22);
      border-bottom-color: rgba(255, 107, 107, 0.35);
    }}

    .eliminated-row:hover td {{
      background: rgba(255, 107, 107, 0.30);
    }}

    .selector-box {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }}
    select {{
      width: min(100%, 420px);
      padding: 13px 16px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #091920;
      color: var(--text);
      font-weight: 800;
      font-size: 1rem;
    }}

    .detail-layout {{ display: grid; grid-template-columns: 340px 1fr; gap: 18px; align-items: start; }}
    .profile-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px;
      position: sticky;
      top: 74px;
    }}
    .profile-card h3 {{ margin: 0 0 10px; font-size: 1.7rem; }}
    .big-score {{ font-size: 3.2rem; line-height: 1; color: var(--gold2); font-weight: 950; margin: 18px 0; }}

    .cards-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .card {{ background: var(--card2); border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 14px; }}
    .card header {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }}
    .card h4 {{ margin: 0; color: var(--gold2); font-size: 1.05rem; }}
    .badge {{ padding: 6px 10px; border-radius: 999px; background: rgba(50,209,125,0.12); color: var(--green); border: 1px solid rgba(50,209,125,0.25); font-weight: 900; font-size: 0.82rem; }}
    .badge.pending {{ color: var(--muted); background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.10); }}

    .comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem; }}
    .comparison strong {{ display: block; color: var(--muted); margin-bottom: 6px; font-size: 0.78rem; text-transform: uppercase; }}
    .mini-line {{ color: var(--muted); margin: 5px 0; }}
    .mini-line b {{ color: var(--text); }}

    ol {{ margin: 0; padding-left: 22px; }}
    li {{ margin: 4px 0; }}

    .standings-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .standings-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 15px; }}
    .standings-card h3 {{ margin: 0 0 10px; color: var(--gold2); text-transform: uppercase; }}
    .team-row {{ display: grid; grid-template-columns: 28px 1fr auto; gap: 8px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.06); align-items: center; }}
    .team-row:last-child {{ border-bottom: none; }}
    .team-points {{ color: var(--gold2); font-weight: 900; }}

    .rules {{ background: var(--card); border: 1px solid var(--border); border-radius: 24px; padding: 20px; }}
    details {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 14px 16px; margin: 12px 0; }}
    summary {{ cursor: pointer; color: var(--gold2); font-weight: 900; }}

    footer {{ text-align: center; color: var(--muted); padding: 42px 0; }}

    @media (max-width: 900px) {{
      .hero {{ min-height: auto; padding-top: 34px; }}
      .hero-stats, .standings-grid, .cards-grid, .detail-layout {{ grid-template-columns: 1fr; }}
      .profile-card {{ position: static; }}
      .section-title {{ align-items: flex-start; flex-direction: column; }}
      table {{ min-width: 620px; }}
    }}
  </style>
</head>

<body>
  <script>
    const APP_DATA = {app_json};
  </script>

  <header class="hero">
    <div class="container">
      <div class="hero-card">
        <div class="eyebrow">Mundial 2026</div>
        <h1>La Porra<br>Turiel 2026</h1>
        <div class="subtitle">Octavos de final</div>
        <div class="hero-stats">
          <div class="stat"><strong id="statParticipants">0</strong><span>Participantes</span></div>
          <div class="stat"><strong id="statLeader">-</strong><span>Líder octavos</span></div>
          <div class="stat"><strong id="statUpdated">-</strong><span>Última actualización</span></div>
        </div>
      </div>
    </div>
  </header>

  <div class="tabs-bar">
    <div class="container tabs-inner">
      <button class="tab-button active" data-tab="r16Tab">Octavos</button>
      <button class="tab-button" data-tab="r32Tab">Dieciseisavos</button>
      <button class="tab-button" data-tab="groupsTab">Fase de grupos</button>
    </div>
  </div>

  <main>
    <div id="r16Tab" class="tab-panel active">
      <section id="r16Clasificacion">
        <div class="container">
          <div class="section-title">
            <h2>Clasificación octavos</h2>
            <span class="pill">Actualización dinámica</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Posición</th><th>Participante</th><th>Total</th><th>Partidos</th><th>España</th></tr>
              </thead>
              <tbody id="r16RankingTable"></tbody>
            </table>
          </div>
        </div>
      </section>

      <section id="r16Detalle">
        <div class="container">
          <div class="section-title">
            <h2>Detalle por participante</h2>
            <span class="pill">Predicción vs realidad</span>
          </div>
          <div class="selector-box"><select id="r16ParticipantSelect"></select></div>
          <div class="detail-layout">
            <aside class="profile-card" id="r16ParticipantSummary"></aside>
            <div id="r16ParticipantMatches" class="cards-grid"></div>
          </div>
        </div>
      </section>
    </div>

    <div id="r32Tab" class="tab-panel">
      <section id="r32Clasificacion">
        <div class="container">
          <div class="section-title">
            <h2>Clasificación dieciseisavos</h2>
            <span class="pill">Actualización dinámica diaria</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Posición</th><th>Participante</th><th>Total</th><th>Partidos</th><th>España</th></tr>
              </thead>
              <tbody id="r32RankingTable"></tbody>
            </table>
          </div>
        </div>
      </section>

      <section id="r32Detalle">
        <div class="container">
          <div class="section-title">
            <h2>Detalle por participante</h2>
            <span class="pill">Predicción vs realidad</span>
          </div>
          <div class="selector-box"><select id="r32ParticipantSelect"></select></div>
          <div class="detail-layout">
            <aside class="profile-card" id="r32ParticipantSummary"></aside>
            <div id="r32ParticipantMatches" class="cards-grid"></div>
          </div>
        </div>
      </section>
    </div>

    <div id="groupsTab" class="tab-panel">
      <section id="groupClasificacion">
        <div class="container">
          <div class="section-title">
            <h2>Clasificación fase de grupos</h2>
            <span class="pill">Resultado final congelado</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Posición</th><th>Participante</th><th>Total</th><th>Grupos</th><th>España</th></tr>
              </thead>
              <tbody id="groupRankingTable"></tbody>
            </table>
          </div>
        </div>
      </section>

      <section id="groupDetalle">
        <div class="container">
          <div class="section-title">
            <h2>Detalle fase de grupos</h2>
            <span class="pill">Predicción vs resultado real</span>
          </div>
          <div class="selector-box"><select id="groupParticipantSelect"></select></div>
          <div class="detail-layout">
            <aside class="profile-card" id="groupParticipantSummary"></aside>
            <div id="groupParticipantGroups" class="cards-grid"></div>
          </div>
        </div>
      </section>

      <section id="groupStandings">
        <div class="container">
          <div class="section-title">
            <h2>Resultado real de cada grupo</h2>
            <span class="pill">Tabla final</span>
          </div>
          <div id="standingsGrid" class="standings-grid"></div>
        </div>
      </section>
    </div>

    <section id="reglas">
      <div class="container">
        <div class="section-title"><h2>Reglas de puntuación</h2></div>
        <div class="rules">
          <details open>
            <summary>Octavos: máximo 15 puntos por partido</summary>
            <ul>
              <li>Acertar la selección que se clasifica: <strong>5 puntos</strong></li>
              <li>Acertar cómo acaba la primera parte: <strong>2 puntos</strong></li>
              <li>Tarjetas amarillas en 90 minutos: exacto <strong>3</strong>, diferencia de 1 <strong>2</strong>, diferencia de 2 <strong>1</strong></li>
              <li>Córners en 90 minutos: exacto <strong>3</strong>, diferencia de 1 <strong>2</strong>, diferencia de 2 <strong>1</strong></li>
              <li>Acertar si habrá penalti durante el partido: <strong>2 puntos</strong></li>
            </ul>
          </details>
          <details>
            <summary>Preguntas de España en octavos</summary>
            <ul>
              <li>Primer gol de España: franja exacta <strong>5 puntos</strong>, franja anterior/posterior <strong>3 puntos</strong></li>
              <li>Primer goleador de España: <strong>5 puntos</strong></li>
              <li>Posesión de España: exacta <strong>5 puntos</strong>; los dos más cercanos sin acierto exacto <strong>3 puntos</strong></li>
            </ul>
          </details>
          <details>
            <summary>Dieciseisavos: máximo 10 puntos por partido</summary>
            <ul>
              <li>Acertar el equipo que se clasifica: <strong>6 puntos</strong></li>
              <li>Goles totales en 90 minutos: exacto <strong>3</strong>, a 1 gol <strong>2</strong>, a 2 goles <strong>1</strong></li>
              <li>Acertar cuándo se decide: <strong>1 punto</strong> — 90 minutos, prórroga o penaltis</li>
            </ul>
          </details>
          <details>
            <summary>Preguntas de España en dieciseisavos</summary>
            <ul>
              <li>Primer gol de España: franja exacta <strong>5 puntos</strong>, franja anterior/posterior <strong>3 puntos</strong></li>
              <li>Primer sustituido de España: <strong>3 puntos</strong></li>
              <li>MVP del partido: <strong>2 puntos</strong></li>
            </ul>
          </details>
          <details>
            <summary>Fase de grupos</summary>
            <ul>
              <li>Cada grupo tenía una puntuación máxima de <strong>10 puntos</strong>.</li>
              <li>La pestaña de fase de grupos queda congelada para consulta.</li>
            </ul>
          </details>
        </div>
      </div>
    </section>
  </main>

  <footer>Un mundial. Una porra. Una leyenda.</footer>

  <script>
    const medal = (rank) => {{ if (rank === 1) return "🥇"; if (rank === 2) return "🥈"; if (rank === 3) return "🥉"; return rank; }};
    const escapeHtml = (value) => {{
      if (value === null || value === undefined) return "";
      return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    }};
    const pts = (value) => `${{value || 0}} pts`;

    function setupTabs() {{
      document.querySelectorAll(".tab-button").forEach((button) => {{
        button.addEventListener("click", () => {{
          document.querySelectorAll(".tab-button").forEach((b) => b.classList.remove("active"));
          document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
          button.classList.add("active");
          document.getElementById(button.dataset.tab).classList.add("active");
          window.scrollTo({{ top: document.querySelector(".tabs-bar").offsetTop, behavior: "smooth" }});
        }});
      }});
    }}

    function initHero() {{
      const ranking = APP_DATA.r16.leaderboard || [];
      document.getElementById("statParticipants").textContent = ranking.length;
      document.getElementById("statLeader").textContent = ranking[0]?.display_name || "-";
      document.getElementById("statUpdated").textContent = APP_DATA.r16.generated_at || APP_DATA.r16.results?.generated_at || APP_DATA.r32.results?.generated_at || APP_DATA.group_stage.results?.generated_at || "-";
    }}

    function renderR16Ranking() {{
      const tbody = document.getElementById("r16RankingTable");
      const ranking = APP_DATA.r16.leaderboard || [];
      const eliminatedStartIndex = Math.max(ranking.length - 8, 0);

      tbody.innerHTML = ranking.map((p, index) => {{
        const isEliminated = index >= eliminatedStartIndex;
        return `
          <tr class="${{isEliminated ? "eliminated-row" : ""}}">
            <td><strong>${{medal(p.position || index + 1)}}</strong></td>
            <td><strong>${{escapeHtml(p.display_name)}}</strong></td>
            <td><strong>${{pts(p.total_points)}}</strong></td>
            <td>${{pts(p.match_points)}}</td>
            <td>${{pts(p.spain_points)}}</td>
          </tr>
        `;
      }}).join("");
    }}

    function renderR16Selector() {{
      const select = document.getElementById("r16ParticipantSelect");
      const ranking = APP_DATA.r16.leaderboard || [];
      select.innerHTML = ranking.map((p, index) => `<option value="${{index}}">${{p.position || index + 1}}. ${{escapeHtml(p.display_name)}} - ${{pts(p.total_points)}}</option>`).join("");
      select.addEventListener("change", () => renderR16Detail(Number(select.value)));
      if (ranking.length) renderR16Detail(0);
    }}

    function renderR16Detail(index) {{
      const participant = (APP_DATA.r16.leaderboard || [])[index];
      if (!participant) return;
      const summary = document.getElementById("r16ParticipantSummary");
      const matches = document.getElementById("r16ParticipantMatches");
      const spain = participant.spain_detail || {{}};
      const spainPred = spain.prediction || {{}};
      const spainReal = spain.real || {{}};

      summary.innerHTML = `
        <h3>${{escapeHtml(participant.display_name)}}</h3>
        <div class="pill">Puesto ${{participant.position}}</div>
        <div class="big-score">${{participant.total_points}} pts</div>
        <div class="breakdown"><span>Partidos: ${{participant.match_points}}</span><span>España: ${{participant.spain_points}}</span></div>
        <hr style="border-color: rgba(255,255,255,.08); margin: 18px 0;" />
        <h4 style="color: var(--gold2); margin-bottom: 8px;">España</h4>
        <p class="mini-line"><b>Primer gol:</b> ${{escapeHtml(spainPred.first_spain_goal_label || spainPred.first_spain_goal)}} → real: ${{escapeHtml(spainReal.first_spain_goal_label || spainReal.first_spain_goal)}} <strong>(${{spain.first_spain_goal_points || 0}} pts)</strong></p>
        <p class="mini-line"><b>Primer goleador:</b> ${{escapeHtml(spainPred.first_spain_scorer)}} → real: ${{escapeHtml(spainReal.first_spain_scorer)}} <strong>(${{spain.first_spain_scorer_points || 0}} pts)</strong></p>
        <p class="mini-line"><b>Posesión:</b> ${{escapeHtml(spainPred.spain_possession)}}% → real: ${{escapeHtml(spainReal.spain_possession)}}% <strong>(${{spain.spain_possession_points || 0}} pts)</strong></p>
      `;

      matches.innerHTML = (participant.match_detail || []).map((m) => {{
        const pred = m.prediction || {{}};
        const real = m.real || {{}};
        const pending = !!m.warning;
        return `
          <article class="card">
            <header><h4>${{escapeHtml(m.match)}}</h4><span class="badge ${{pending ? "pending" : ""}}">${{m.points || 0}} pts</span></header>
            ${{pending ? `<p class="mini-line">${{escapeHtml(m.warning)}}</p>` : ""}}
            <div class="comparison">
              <div>
                <strong>Predicción</strong>
                <p class="mini-line">Clasificado: <b>${{escapeHtml(pred.qualified_team_es || pred.qualified_team)}}</b></p>
                <p class="mini-line">Descanso: <b>${{escapeHtml(pred.half_time_result_es || pred.half_time_result)}}</b></p>
                <p class="mini-line">Amarillas: <b>${{escapeHtml(pred.yellow_cards_90)}}</b></p>
                <p class="mini-line">Córners: <b>${{escapeHtml(pred.corners_90)}}</b></p>
                <p class="mini-line">Penalti: <b>${{escapeHtml(pred.penalty_es || pred.penalty)}}</b></p>
              </div>
              <div>
                <strong>Real</strong>
                <p class="mini-line">Clasificado: <b>${{escapeHtml(real.qualified_team_es || real.qualified_team || "Pendiente")}}</b></p>
                <p class="mini-line">Descanso: <b>${{escapeHtml(real.half_time_result_es || real.half_time_result || "Pendiente")}}</b></p>
                <p class="mini-line">Amarillas: <b>${{escapeHtml(real.yellow_cards_90 ?? "Pendiente")}}</b></p>
                <p class="mini-line">Córners: <b>${{escapeHtml(real.corners_90 ?? "Pendiente")}}</b></p>
                <p class="mini-line">Penalti: <b>${{escapeHtml(real.penalty_es || real.penalty || "Pendiente")}}</b></p>
              </div>
            </div>
            <div class="breakdown"><span>Clasificado: ${{m.qualified_points || 0}}</span><span>Descanso: ${{m.half_time_points || 0}}</span><span>Amarillas: ${{m.yellow_cards_points || 0}}</span><span>Córners: ${{m.corners_points || 0}}</span><span>Penalti: ${{m.penalty_points || 0}}</span></div>
          </article>
        `;
      }}).join("");
    }}

    function renderR32Ranking() {{
      const tbody = document.getElementById("r32RankingTable");
      const ranking = APP_DATA.r32.leaderboard || [];
      const eliminatedStartIndex = ranking.length + 1;

      tbody.innerHTML = ranking.map((p, index) => {{
        const isEliminated = index >= eliminatedStartIndex;
        return `
          <tr class="${{isEliminated ? "eliminated-row" : ""}}">
            <td><strong>${{medal(p.position || index + 1)}}</strong></td>
            <td><strong>${{escapeHtml(p.display_name)}}</strong></td>
            <td><strong>${{pts(p.total_points)}}</strong></td>
            <td>${{pts(p.match_points)}}</td>
            <td>${{pts(p.spain_points)}}</td>
          </tr>
        `;
      }}).join("");
    }}

    function renderR32Selector() {{
      const select = document.getElementById("r32ParticipantSelect");
      const ranking = APP_DATA.r32.leaderboard || [];
      select.innerHTML = ranking.map((p, index) => `<option value="${{index}}">${{p.position || index + 1}}. ${{escapeHtml(p.display_name)}} - ${{pts(p.total_points)}}</option>`).join("");
      select.addEventListener("change", () => renderR32Detail(Number(select.value)));
      if (ranking.length) renderR32Detail(0);
    }}

    function renderR32Detail(index) {{
      const participant = (APP_DATA.r32.leaderboard || [])[index];
      if (!participant) return;
      const summary = document.getElementById("r32ParticipantSummary");
      const matches = document.getElementById("r32ParticipantMatches");
      const spain = participant.spain_detail || {{}};
      const spainPred = spain.prediction || {{}};
      const spainReal = spain.real || {{}};

      summary.innerHTML = `
        <h3>${{escapeHtml(participant.display_name)}}</h3>
        <div class="pill">Puesto ${{participant.position}}</div>
        <div class="big-score">${{participant.total_points}} pts</div>
        <div class="breakdown"><span>Partidos: ${{participant.match_points}}</span><span>España: ${{participant.spain_points}}</span></div>
        <hr style="border-color: rgba(255,255,255,.08); margin: 18px 0;" />
        <h4 style="color: var(--gold2); margin-bottom: 8px;">España</h4>
        <p class="mini-line"><b>Primer gol:</b> ${{escapeHtml(spainPred.first_spain_goal_label || spainPred.first_spain_goal)}} → real: ${{escapeHtml(spainReal.first_spain_goal_label || spainReal.first_spain_goal)}} <strong>(${{spain.first_spain_goal_points || 0}} pts)</strong></p>
        <p class="mini-line"><b>Primer sustituido:</b> ${{escapeHtml(spainPred.first_spain_sub)}} → real: ${{escapeHtml(spainReal.first_spain_sub)}} <strong>(${{spain.first_spain_sub_points || 0}} pts)</strong></p>
        <p class="mini-line"><b>MVP:</b> ${{escapeHtml(spainPred.spain_mvp)}} → real: ${{escapeHtml(spainReal.spain_mvp)}} <strong>(${{spain.spain_mvp_points || 0}} pts)</strong></p>
      `;

      matches.innerHTML = (participant.match_detail || []).map((m) => {{
        const pred = m.prediction || {{}};
        const real = m.real || {{}};
        const pending = !!m.warning;
        return `
          <article class="card">
            <header><h4>${{escapeHtml(m.match)}}</h4><span class="badge ${{pending ? "pending" : ""}}">${{m.points || 0}} pts</span></header>
            ${{pending ? `<p class="mini-line">${{escapeHtml(m.warning)}}</p>` : ""}}
            <div class="comparison">
              <div>
                <strong>Predicción</strong>
                <p class="mini-line">Ganador: <b>${{escapeHtml(pred.winner_es || pred.winner)}}</b></p>
                <p class="mini-line">Goles 90': <b>${{escapeHtml(pred.total_goals_90)}}</b></p>
                <p class="mini-line">Decisión: <b>${{escapeHtml(pred.decided_in_es || pred.decided_in)}}</b></p>
              </div>
              <div>
                <strong>Real</strong>
                <p class="mini-line">Ganador: <b>${{escapeHtml(real.winner_es || real.winner || "Pendiente")}}</b></p>
                <p class="mini-line">Goles 90': <b>${{escapeHtml(real.total_goals_90 ?? "Pendiente")}}</b></p>
                <p class="mini-line">Decisión: <b>${{escapeHtml(real.decided_in_es || "Pendiente")}}</b></p>
              </div>
            </div>
            <div class="breakdown"><span>Clasificado: ${{m.winner_points || 0}}</span><span>Goles: ${{m.goals_points || 0}}</span><span>Decisión: ${{m.decision_points || 0}}</span></div>
          </article>
        `;
      }}).join("");
    }}

    function renderGroupRanking() {{
      const tbody = document.getElementById("groupRankingTable");
      const ranking = APP_DATA.group_stage.results?.ranking || [];
      tbody.innerHTML = ranking.map((p) => `
        <tr>
          <td><strong>${{medal(p.rank)}}</strong></td>
          <td><strong>${{escapeHtml(p.display_name || p.name)}}</strong></td>
          <td><strong>${{pts(p.total_points)}}</strong></td>
          <td>${{pts(p.group_points)}}</td>
          <td>${{pts(p.spain_points)}}</td>
        </tr>
      `).join("");
    }}

    function renderGroupSelector() {{
      const select = document.getElementById("groupParticipantSelect");
      const ranking = APP_DATA.group_stage.results?.ranking || [];
      select.innerHTML = ranking.map((p, index) => `<option value="${{index}}">${{p.rank}}. ${{escapeHtml(p.display_name || p.name)}} - ${{pts(p.total_points)}}</option>`).join("");
      select.addEventListener("change", () => renderGroupDetail(Number(select.value)));
      if (ranking.length) renderGroupDetail(0);
    }}

    function renderGroupDetail(index) {{
      const participant = (APP_DATA.group_stage.results?.ranking || [])[index];
      if (!participant) return;
      const summary = document.getElementById("groupParticipantSummary");
      const groups = document.getElementById("groupParticipantGroups");
      const spain = participant.spain_questions || {{}};

      summary.innerHTML = `
        <h3>${{escapeHtml(participant.display_name || participant.name)}}</h3>
        <div class="pill">Puesto ${{participant.rank}}</div>
        <div class="big-score">${{participant.total_points}} pts</div>
        <div class="breakdown"><span>Grupos: ${{participant.group_points}}</span><span>España: ${{participant.spain_points}}</span></div>
        <hr style="border-color: rgba(255,255,255,.08); margin: 18px 0;" />
        <h4 style="color: var(--gold2); margin-bottom: 8px;">España fase de grupos</h4>
        <p class="mini-line">Goleador: ${{escapeHtml(spain.top_scorer?.prediction)}} <strong>(${{spain.top_scorer?.points || 0}} pts)</strong></p>
        <p class="mini-line">Asistente: ${{escapeHtml(spain.top_assistant?.prediction)}} <strong>(${{spain.top_assistant?.points || 0}} pts)</strong></p>
        <p class="mini-line">Goles a favor: ${{escapeHtml(spain.goals_for?.prediction)}} <strong>(${{spain.goals_for?.points || 0}} pts)</strong></p>
        <p class="mini-line">Goles en contra: ${{escapeHtml(spain.goals_against?.prediction)}} <strong>(${{spain.goals_against?.points || 0}} pts)</strong></p>
      `;

      groups.innerHTML = Object.entries(participant.groups || {{}}).map(([groupName, group]) => `
        <article class="card">
          <header><h4>Grupo ${{groupName}}</h4><span class="badge">${{group.total}} pts</span></header>
          <div class="comparison">
            <div><strong>Predicción</strong><ol>${{(group.predicted_order_es || group.predicted_order || []).map((team) => `<li>${{escapeHtml(team)}}</li>`).join("")}}</ol></div>
            <div><strong>Real</strong><ol>${{(group.real_order_es || group.real_order || []).map((team) => `<li>${{escapeHtml(team)}}</li>`).join("")}}</ol></div>
          </div>
          <div class="breakdown"><span>Clasificados: ${{group.classified_teams_points}}</span><span>Bonus: ${{group.classified_bonus_points || 0}}</span><span>Orden: ${{group.exact_order_points}}</span><span>3º: ${{group.third_place_points}}</span><span>4º: ${{group.fourth_place_points}}</span></div>
        </article>
      `).join("");
    }}

    function renderStandings() {{
      const container = document.getElementById("standingsGrid");
      const groups = APP_DATA.group_stage.standings?.groups || {{}};
      container.innerHTML = Object.entries(groups).map(([groupName, teams]) => `
        <article class="standings-card">
          <h3>Grupo ${{groupName}}</h3>
          ${{teams.map((team) => `
            <div class="team-row"><strong>${{team.position}}</strong><span>${{escapeHtml(team.team_es || team.team)}}</span><span class="team-points">${{team.points}} pts</span></div>
          `).join("")}}
        </article>
      `).join("");
    }}

    setupTabs();
    initHero();
    renderR16Ranking();
    renderR16Selector();
    renderR32Ranking();
    renderR32Selector();
    renderGroupRanking();
    renderGroupSelector();
    renderStandings();
  </script>
</body>
</html>'''


def main() -> None:
    app_data = build_app_data()
    html = generate_html(app_data)
    write_file(OUTPUT_FILE, html)
    print(f"HTML generado correctamente: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
