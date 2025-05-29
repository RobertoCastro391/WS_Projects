import pandas as pd
import requests
import time

# This file paths are relative to the script location
seasons_csv = "../datasets/seasons.csv"
teams_csv = "../datasets/teams.csv"

df_seasons = pd.read_csv(seasons_csv)
df_teams = pd.read_csv(teams_csv)

estatisticas = []

def get_statistics(season_id, team_id):
    url = f"http://192.168.182.58/NBA/api/Statistics/PlayersBySeason?seasonId={season_id}&teamid={team_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting season {season_id}, team {team_id}: {e}")
        return None

for _, season_row in df_seasons.iterrows():
    season_id = season_row['Id']
    season_name = season_row['Season']

    for _, team_row in df_teams.iterrows():
        team_id = team_row['Id']
        team_name = team_row['Name']

        print(f"Getting data from Season {season_name} (ID: {season_id}) for team {team_name} (ID: {team_id})...")
        
        dados = get_statistics(season_id, team_id)
        if dados:
            for jogador in dados:
                jogador["SeasonId"] = season_id
                jogador["SeasonName"] = season_name
                jogador["TeamId"] = team_id
                jogador["TeamName"] = team_name
                estatisticas.append(jogador)

        time.sleep(1)

df_resultado = pd.DataFrame(estatisticas)

df_resultado.to_csv("estatisticas_completas.csv", index=False)
print("Exporting Conclude: estatisticas_completas.csv")