import pandas as pd
import requests
import time

# === Caminhos dos arquivos CSV ===
season_csv = "season.csv"
team_csv = "team.csv"

# === Carregando CSVs ===
df_seasons = pd.read_csv("seasons.csv")
df_teams = pd.read_csv("teams.csv")

# === Lista para armazenar todos os dados ===
estatisticas = []

# === Função para buscar estatísticas por temporada e time ===
def buscar_estatisticas(season_id, team_id):
    url = f"http://192.168.182.58/NBA/api/Statistics/PlayersBySeason?seasonId={season_id}&teamid={team_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar season {season_id}, team {team_id}: {e}")
        return None

# === Loop por cada combinação de season x team ===
for _, season_row in df_seasons.iterrows():
    season_id = season_row['Id']
    season_name = season_row['Season']

    for _, team_row in df_teams.iterrows():
        team_id = team_row['Id']
        team_name = team_row['Name']

        print(f"🔎 Buscando dados da Season {season_name} (ID: {season_id}) para o time {team_name} (ID: {team_id})...")
        
        dados = buscar_estatisticas(season_id, team_id)
        if dados:
            for jogador in dados:
                jogador["SeasonId"] = season_id
                jogador["SeasonName"] = season_name
                jogador["TeamId"] = team_id
                jogador["TeamName"] = team_name
                estatisticas.append(jogador)

        time.sleep(1)  # Evita sobrecarregar o servidor

# === Convertendo para DataFrame e exportando ===
df_resultado = pd.DataFrame(estatisticas)

df_resultado.to_csv("estatisticas_completas.csv", index=False)
print("✅ Exportação concluída: estatisticas_completas.csv")