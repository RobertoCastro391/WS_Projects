import pandas as pd
from simplegraph import SimpleGraph
from collections import defaultdict
import json
import ast

BASE = "http://example.org/nba/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

def uri(resource_type, identifier):
    return f"{BASE}{resource_type}_{str(identifier).replace(' ', '_')}"

graph = SimpleGraph()

# Load CSV files (Files are relative to the script location)
dfs = {
    "arenas": pd.read_csv("../datasets/arenas.csv"),
    "conferences": pd.read_csv("../datasets/conferences.csv"),
    "divisions": pd.read_csv("../datasets/divisions.csv"),
    "players": pd.read_csv("../datasets/players.csv"),
    "positions": pd.read_csv("../datasets/positions.csv"),
    "seasons": pd.read_csv("../datasets/seasons.csv"),
    "seasonTypes": pd.read_csv("../datasets/seasonTypes.csv"),
    "states": pd.read_csv("../datasets/states.csv"),
    "teams": pd.read_csv("../datasets/teams.csv"),
    "stats": pd.read_csv("../datasets/estatisticas_completas.csv"),
}

# States
for _, row in dfs["states"].iterrows():
    s = uri("state", row["Id"])
    graph.add(s, f"{RDF}type", f"{BASE}State")
    graph.add(s, f"{BASE}name", row["Name"])

    if not pd.isna(row["Flag"]):
        graph.add(s, f"{BASE}Flag", row["Flag"])

# Conferences
for _, row in dfs["conferences"].iterrows():
    c = uri("conference", row["Id"])
    graph.add(c, f"{RDF}type", f"{BASE}Conference")
    graph.add(c, f"{BASE}name", row["Name"])

# Divisions
for _, row in dfs["divisions"].iterrows():
    d = uri("division", row["Id"])
    graph.add(d, f"{RDF}type", f"{BASE}Division")
    graph.add(d, f"{BASE}name", row["Name"])

# Positions
for _, row in dfs["positions"].iterrows():
    p = uri("position", row["Id"])
    graph.add(p, f"{RDF}type", f"{BASE}Position")
    graph.add(p, f"{BASE}name", row["Name"])
    if not pd.isna(row["Description"]):
        graph.add(p, f"{BASE}description", row["Description"])

# Seasons
for _, row in dfs["seasons"].iterrows():
    s = uri("season", row["Id"])
    graph.add(s, f"{RDF}type", f"{BASE}Season")
    graph.add(s, f"{BASE}label", row["Season"])

# Season types
for _, row in dfs["seasonTypes"].iterrows():
    st = uri("seasonType", row["Id"])
    graph.add(st, f"{RDF}type", f"{BASE}SeasonType")
    graph.add(st, f"{BASE}name", row["Name"])

# Teams
division_conference_map = {}
for _, row in dfs["teams"].iterrows():
    t = uri("team", row["Id"])
    graph.add(t, f"{RDF}type", f"{BASE}Team")
    graph.add(t, f"{BASE}name", row["Name"])
    graph.add(t, f"{BASE}acronym", row["Acronym"])
    graph.add(t, f"{BASE}city", row["City"])

    if not pd.isna(row["History"]):
        clean_history = str(row["History"]).replace("\n", " ").replace("\r", " ").strip()
        graph.add(t, f"{BASE}history", clean_history)
    
    if not pd.isna(row["Logo"]):
        graph.add(t, f"{BASE}logo", row["Logo"])

    if not pd.isna(row["ConferenceId"]):
        conf_uri = uri("conference", int(row["ConferenceId"]))
        graph.add(t, f"{BASE}conference", conf_uri)

    if not pd.isna(row["DivisionId"]):
        div_uri = uri("division", int(row["DivisionId"]))
        graph.add(t, f"{BASE}division", div_uri)
        if not pd.isna(row["ConferenceId"]):
            division_conference_map[int(row["DivisionId"])] = int(row["ConferenceId"])

    if not pd.isna(row["StateId"]):
        state_uri = uri("state", row["StateId"])
        graph.add(t, f"{BASE}state", state_uri)
        graph.add(t, f"{BASE}locatedIn", state_uri)

    if not pd.isna(row["Seasons"]):
        for season in str(row["Seasons"]).split(","):
            if season.strip().isdigit():
                graph.add(t, f"{BASE}participatedIn", uri("season", season.strip()))

# Division → Conference relation
for division_id, conference_id in division_conference_map.items():
    graph.add(uri("division", division_id), f"{BASE}conference", uri("conference", conference_id))

# Arenas
for _, row in dfs["arenas"].iterrows():
    a = uri("arena", row["Id"])
    graph.add(a, f"{RDF}type", f"{BASE}Arena")
    graph.add(a, f"{BASE}name", row["Name"])
    graph.add(a, f"{BASE}location", row["Location"])
    if not pd.isna(row["Opened"]):
        graph.add(a, f"{BASE}opened", str(int(row["Opened"])))
    if not pd.isna(row["Capacity"]):
        graph.add(a, f"{BASE}capacity", str(int(row["Capacity"])))
    if not pd.isna(row["StateId"]):
        graph.add(a, f"{BASE}locatedIn", uri("state", row["StateId"]))
    
    if not pd.isna(row['Photo']):
        graph.add(a, f"{BASE}photo", row["Photo"])

    if not pd.isna(row["Lat"]):
        graph.add(a, f"{BASE}latitude", str(float(row["Lat"])))
    
    if not pd.isna(row["Lon"]):
        graph.add(a, f"{BASE}longitude", str(float(row["Lon"])))
    
    if not pd.isna(row["TeamId"]):
        team_uri = uri("team", row["TeamId"])
        graph.add(team_uri, f"{BASE}arena", a)
        graph.add(a, f"{BASE}homeTeam", team_uri)

# Players
for _, row in dfs["players"].iterrows():
    p = uri("player", row["Id"])
    graph.add(p, f"{RDF}type", f"{BASE}Player")
    graph.add(p, f"{BASE}name", row["Name"])

    if not pd.isna(row["Birthdate"]):
        graph.add(p, f"{BASE}birthdate", row["Birthdate"][:10])

    if not pd.isna(row['CountryName']):
        graph.add(p, f"{BASE}bornIn", row["CountryName"])
    
    if not pd.isna(row["DraftYear"]):
        graph.add(p, f"{BASE}draftYear", str(int(row["DraftYear"])))

    if not pd.isna(row["PositionId"]):
        graph.add(p, f"{BASE}position", uri("position", row["PositionId"]))

    if not pd.isna(row["Height"]):
        graph.add(p, f"{BASE}height", str(row["Height"]))
        
    if not pd.isna(row["Weight"]):
        graph.add(p, f"{BASE}weight", str(row["Weight"]))
    
    if not pd.isna(row["School"]):
        graph.add(p, f"{BASE}school", row["School"])

    if not pd.isna(row['Photo']):
        graph.add(p, f"{BASE}photo", row["Photo"])

    if not pd.isna(row["Biography"]):
        clean_biography = str(row["Biography"]).replace("\n", " ").replace("\r", " ").strip()
        graph.add(t, f"{BASE}biography", clean_biography)

# Statistics - Participation node
for _, row in dfs["stats"].iterrows():
    players = ast.literal_eval(row["Players"])
    for player in players:
        participation_uri = uri("participation", f"{player['Id']}_{row['TeamId']}_{row['SeasonId']}_{row['SeasonType']}")
        
        graph.add(participation_uri, f"{RDF}type", f"{BASE}Participation")
        graph.add(participation_uri, f"{BASE}player", uri("player", player["Id"]))
        graph.add(participation_uri, f"{BASE}team", uri("team", row["TeamId"]))
        graph.add(participation_uri, f"{BASE}season", uri("season", row["SeasonId"]))
        graph.add(participation_uri, f"{BASE}seasonType", uri("seasonType", row["SeasonType"]))

# Export CSV
graph.save("nba_triples.csv")

# Export N3 format
with open("nba_triples.n3", "w", encoding="utf-8") as f:
    f.write("@prefix ex: <http://example.org/nba/> .\n")
    f.write("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n\n")

    grouped = defaultdict(list)
    for s, p, o in graph.triples(None, None, None):
        subj = s.replace(BASE, "ex:") if isinstance(s, str) and s.startswith(BASE) else f'<{s}>'
        pred = p.replace(BASE, "ex:").replace(RDF, "rdf:") if isinstance(p, str) and (p.startswith(BASE) or p.startswith(RDF)) else f'<{p}>'

        if isinstance(o, str):
            if o.startswith(BASE):
                obj = o.replace(BASE, "ex:")
            elif o.startswith(RDF):
                obj = o.replace(RDF, "rdf:")
            elif o.startswith("http"):
                obj = f'<{o}>'
            elif "\n" in o or '"' in o or len(o) > 200:
                escaped = o.replace('"""', '\\"\\"\\"')
                obj = f'"""{escaped}"""'
            else:
                escaped = o.replace('"', '\\"')
                obj = f'"{escaped}"'
        else:
            obj = f'"{o}"'

        grouped[subj].append((pred, obj))

    for subj, predicates in grouped.items():
        f.write(f"{subj}\n")
        for i, (pred, obj) in enumerate(predicates):
            end = " ." if i == len(predicates) - 1 else " ;"
            f.write(f"    {pred} {obj}{end}\n")
        f.write("\n")