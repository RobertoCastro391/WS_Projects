import pandas as pd
import requests
import json
import time


# This file paths are relative to the script location
csv_path = "../datasets/players.csv"

df = pd.read_csv(csv_path)

def get_additional_info(player_id):
    url = f"http://192.168.182.58/nba/api/Players/{player_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar ID {player_id}: {e}")
        return None

players_extended = []

for index, row in df.iterrows():
    player_id = row['Id']
    print(f"Getting data from player ID {player_id}...")
    
    additional_info = get_additional_info(player_id)
    if additional_info:
        full_info = {**row.to_dict(), **additional_info}
        players_extended.append(full_info)
    else:
        players_extended.append(row.to_dict())

    time.sleep(1) 

df_extended = pd.DataFrame(players_extended)
df_extended.to_csv("jogadores_completos.csv", index=False)

print("Process conluded.")