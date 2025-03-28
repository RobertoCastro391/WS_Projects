import pandas as pd
import requests
import json
import time

# Caminho para seu CSV
csv_path = "players.csv"

# Carrega os dados do CSV
df = pd.read_csv(csv_path)

# Função para buscar dados adicionais por ID
def get_additional_info(player_id):
    url = f"http://192.168.182.58/nba/api/Players/{player_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao buscar ID {player_id}: {e}")
        return None

# Lista para armazenar os resultados
players_extended = []

# Itera sobre os jogadores do CSV
for index, row in df.iterrows():
    player_id = row['Id']
    print(f"Buscando dados do jogador ID {player_id}...")
    
    additional_info = get_additional_info(player_id)
    if additional_info:
        full_info = {**row.to_dict(), **additional_info}
        players_extended.append(full_info)
    else:
        players_extended.append(row.to_dict())

    time.sleep(1)  # Pequena pausa entre as requisições para não sobrecarregar o servidor

# Converte para DataFrame para visualização ou exportação
df_extended = pd.DataFrame(players_extended)

# Salva em um novo CSV (opcional)
df_extended.to_csv("jogadores_completos.csv", index=False)

print("Processo concluído.")