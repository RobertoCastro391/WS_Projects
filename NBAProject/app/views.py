from collections import defaultdict

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from SPARQLWrapper import JSON, SPARQLWrapper
import requests


def home_page(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    # Obter estatísticas globais
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT (COUNT(DISTINCT ?player) AS ?players)
               (COUNT(DISTINCT ?team) AS ?teams)
               (COUNT(DISTINCT ?season) AS ?seasons)
               (COUNT(?p) AS ?participations)
        WHERE {
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
        }
    """)
    sparql.setReturnFormat(JSON)
    stats_results = sparql.query().convert()
    row = stats_results["results"]["bindings"][0]

    stats = {
        "players": int(row["players"]["value"]),
        "teams": int(row["teams"]["value"]),
        "seasons": int(row["seasons"]["value"]),
        "participations": int(row["participations"]["value"]),
    }

    # Obter participações por temporada
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?season (COUNT(?p) AS ?count) WHERE {
            ?p nba:season ?season .
        }
        GROUP BY ?season
        ORDER BY DESC(?count)
        LIMIT 5
    """)
    sparql.setReturnFormat(JSON)
    participacoes_result = sparql.query().convert()

    top_temporadas = []
    for result in participacoes_result["results"]["bindings"]:
        season_uri = result["season"]["value"]
        season_label = season_uri.split("_")[-1]  # ex: season_2001 → 2001
        participacao = int(result["count"]["value"])
        top_temporadas.append((season_label, participacao))

    news_items = get_nba_news()

    return render(request, 'home.html', {
    'stats': stats,
    'top_temporadas': top_temporadas,
    'news_items': news_items,
    'kpi_cards': [
        ("Players", stats["players"], "👤"),
        ("Teams", stats["teams"], "🏢"),
        ("Seasons", stats["seasons"], "📅"),
        ("Participations", stats["participations"], "📝"),
    ]
})


def get_nba_news():
    url = f"https://newsdata.io/api/1/news?apikey=pub_770327c839a88d933295237cfe34bfdc196c3&q=nba&language=pt,en&category=sports"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        articles = data.get("results", [])[:5]
        news_items = []
        for article in articles:
            news_items.append({
                "title": article.get("title", "Notícia sem título"),
                "summary": article.get("description", ""),
                "image": article.get("image_url") or "https://cdn.nba.com/logos/nba/nba-logoman-word-white.svg",
                "link": article.get("link", "#")
            })
        return news_items
    except Exception as e:
        print(f"Erro ao buscar notícias: {e}")
        return []

def list_jogadores(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        PREFIX schema: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?player ?playerName WHERE {
            ?p nba:player ?player .
            ?player nba:name ?playerName .
        }
        ORDER BY ?playerName
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    jogadores = [
        {
            "id": result["player"]["value"],
            "nome": result["playerName"]["value"]
        }
        for result in results["results"]["bindings"]
    ]
    
    return JsonResponse({"jogadores": jogadores})

def list_equipas(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?team ?name ?acronym ?logo WHERE {
            ?team a nba:Team ;
                  nba:name ?name .
            OPTIONAL { ?team nba:acronym ?acronym . }
            OPTIONAL { ?team nba:logo ?logo . }
        }
        ORDER BY ?name
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    teams_dict = defaultdict(lambda: {
        "id": "",
        "names": [],
        "acronyms": [],
        "logos": []
    })

    for result in results["results"]["bindings"]:
        team_id = result["team"]["value"]
        team = teams_dict[team_id]
        team["id"] = team_id

        name = result.get("name", {}).get("value")
        acronym = result.get("acronym", {}).get("value")
        logo = result.get("logo", {}).get("value")

        if name and name not in team["names"]:
            team["names"].append(name)
        if acronym and acronym not in team["acronyms"]:
            team["acronyms"].append(acronym)
        if logo and logo not in team["logos"]:
            team["logos"].append(logo)

    equipas = []
    for team in teams_dict.values():
        equipas.append({
            "id": team["id"],
            "name": team["names"][0] if team["names"] else "",
            "acronym": team["acronyms"][0] if team["acronyms"] else "",
            "logo": team["logos"][0] if team["logos"] else "",
            "other_names": team["names"][1:] if len(team["names"]) > 1 else [],
            "other_acronyms": team["acronyms"][1:] if len(team["acronyms"]) > 1 else [],
            "other_logos": team["logos"][1:] if len(team["logos"]) > 1 else []
        })

    return render(request, "teams.html", {"equipas": equipas})


def list_temporadas(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?season WHERE {
            ?p nba:season ?season .
        }
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    temporadas = [result["season"]["value"] for result in results["results"]["bindings"]]

    return JsonResponse({"temporadas": temporadas})

def list_participacoes(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?player ?team ?season ?seasonType WHERE {
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season ;
               nba:seasonType ?seasonType .
        }
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    participacoes = []
    for result in results["results"]["bindings"]:
        participacoes.append({
            "player": result["player"]["value"],
            "team": result["team"]["value"],
            "season": result["season"]["value"],
            "seasonType": result["seasonType"]["value"]
        })

    return JsonResponse({"participacoes": participacoes})

def stats_geral(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT (COUNT(DISTINCT ?player) AS ?players)
               (COUNT(DISTINCT ?team) AS ?teams)
               (COUNT(DISTINCT ?season) AS ?seasons)
        WHERE {
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
        }
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    row = results["results"]["bindings"][0]

    stats = {
        "players": int(row["players"]["value"]),
        "teams": int(row["teams"]["value"]),
        "seasons": int(row["seasons"]["value"])
    }

    return JsonResponse(stats)

def pagina_jogador(request, id):
    jogador_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    # Query de dados do jogador
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?name ?birthdate ?bornIn ?draftYear ?position ?height ?weight ?school ?photo WHERE {{
            ?player a nba:Player ;
                    nba:name ?name .
            FILTER(STR(?player) = "{jogador_uri}")

            OPTIONAL {{ ?player nba:birthdate ?birthdate. }}
            OPTIONAL {{ ?player nba:bornIn ?bornIn. }}
            OPTIONAL {{ ?player nba:draftYear ?draftYear. }}
            OPTIONAL {{ ?player nba:position ?position. }}
            OPTIONAL {{ ?player nba:height ?height. }}
            OPTIONAL {{ ?player nba:weight ?weight. }}
            OPTIONAL {{ ?player nba:school ?school. }}
            OPTIONAL {{ ?player nba:photo ?photo. }}
        }}
    """)

    sparql.setReturnFormat(JSON)
    profile_data = sparql.query().convert()["results"]["bindings"]

    if not profile_data:
        return JsonResponse({"erro": "Jogador não encontrado"}, status=404)

    player_info = profile_data[0]
    dados = {k: player_info[k]["value"] for k in player_info}

    # Query para participações com nome da equipa
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?team ?teamName ?season ?seasonType WHERE {{
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season ;
               nba:seasonType ?seasonType .
            ?team nba:name ?teamName .
            FILTER(STR(?player) = "{jogador_uri}")
        }}
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    participacoes_data = sparql.query().convert()["results"]["bindings"]

    participacoes = []
    for p in participacoes_data:
        participacoes.append({
            "team": p["team"]["value"],
            "teamName": p["teamName"]["value"],
            "season": p["season"]["value"],
            "seasonType": p["seasonType"]["value"]
        })

    return JsonResponse({
        "jogador": jogador_uri,
        **dados,
        "participacoes": participacoes
    })

def pagina_equipa(request, id):
    from collections import defaultdict

    team_uri = f"http://example.org/nba/team_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    # 1. Info da equipa
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?name ?acronym ?logo ?city ?statename ?conference ?conferencename ?divison ?divisionname ?arena ?arenaname WHERE {{
            ?team a nba:Team ;
                  nba:name ?name .
            OPTIONAL {{ ?team nba:acronym ?acronym . }}
            OPTIONAL {{ ?team nba:logo ?logo . }}
            OPTIONAL {{ ?team nba:city ?city . }}
            OPTIONAL {{ ?team nba:state ?state . }}
            OPTIONAL {{ ?state nba:name ?statename . }}
            OPTIONAL {{ ?team nba:conference ?conference . }}
            OPTIONAL {{ ?conference nba:name ?conferencename . }}
            OPTIONAL {{ ?team nba:division ?division . }}
            OPTIONAL {{ ?division nba:name ?divisionname . }}
            OPTIONAL {{ ?team nba:arena ?arena . }}
            OPTIONAL {{ ?arena nba:name ?arenaname . }}
            FILTER(STR(?team) = "{team_uri}")
        }}
    """)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()["results"]["bindings"]

    if not result:
        return JsonResponse({"error": "Team not found"}, status=404)

    names = set()
    acronyms = set()
    logos = set()
    states = set()

    city = state = conference = division = arenaname = arena = ""

    for row in result:
        names.add(row.get("name", {}).get("value", ""))
        acronyms.add(row.get("acronym", {}).get("value", ""))
        logos.add(row.get("logo", {}).get("value", ""))
        states.add(row.get("statename", {}).get("value", state))

        city = row.get("city", {}).get("value", city)
        conference = row.get("conferencename", {}).get("value", conference)
        division = row.get("divisionname", {}).get("value", division)
        arena = row.get("arena", {}).get("value", arena)
        arenaname = row.get("arenaname", {}).get("value", arenaname)

    def clean(s): return sorted(v for v in s if v)

    names_list = clean(names)
    acronyms_list = clean(acronyms)
    logos_list = clean(logos)

    team_info = {
        "id": team_uri,
        "name": names_list[0] if names_list else "",
        "acronym": acronyms_list[0] if acronyms_list else "",
        "logo": logos_list[0] if logos_list else "",
        "other_names": names_list[1:] if len(names_list) > 1 else [],
        "other_acronyms": acronyms_list[1:] if len(acronyms_list) > 1 else [],
        "other_logos": logos_list[1:] if len(logos_list) > 1 else [],
        "city": city,
        "state": state,
        "conference": conference,
        "division": division,
        "arena": arena,
        "arenaName": arenaname
    }

    # 2. Jogadores por temporada (agrupado)
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?player ?playerName ?playerPhoto ?season ?seasonType WHERE {{
            ?p nba:team ?team ;
               nba:player ?player ;
               nba:season ?season ;
               nba:seasonType ?seasonType .
            ?player nba:name ?playerName .
            FILTER(STR(?team) = "{team_uri}")
        }}
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    participations = sparql.query().convert()["results"]["bindings"]

    # Agrupar por temporada
    seasons = {}
    for p in participations:
        season = p["season"]["value"]
        if season not in seasons:
            seasons[season] = {
                "seasonName": season.split("_")[-1],  # ex: season_2001 → 2001
                "seasonType": p["seasonType"]["value"],
                "players": []
            }

        player_uri = p["player"]["value"]
        if player_uri not in [pl["player"] for pl in seasons[season]["players"]]:
            seasons[season]["players"].append({
                "player": player_uri,
                "playerName": p["playerName"]["value"]
            })

    team_info["seasons"] = seasons

    #return JsonResponse(team_info)
    return render(request, "team.html", {"team": team_info})


def pagina_temporada(request, ano):
    season_uri = f"http://example.org/nba/season_{ano}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?team ?teamName ?player ?playerName ?seasonType WHERE {{
            ?p nba:season ?season ;
               nba:team ?team ;
               nba:player ?player ;
               nba:seasonType ?seasonType .
            ?team nba:name ?teamName .
            ?player nba:name ?playerName .
            FILTER(STR(?season) = "{season_uri}")
        }}
        ORDER BY ?team ?player
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    # Group by team and deduplicate player+seasonType
    teams = defaultdict(lambda: {
        "teamName": "",
        "players": []
    })

    seen = set()  # to deduplicate

    for r in results:
        team_uri = r["team"]["value"]
        player_uri = r["player"]["value"]
        season_type = r["seasonType"]["value"]

        key = (team_uri, player_uri, season_type)
        if key in seen:
            continue
        seen.add(key)

        teams[team_uri]["teamName"] = r["teamName"]["value"]
        teams[team_uri]["players"].append({
            "player": player_uri,
            "playerName": r["playerName"]["value"],
            "seasonType": season_type
        })

    # Format response
    season_data = {
        "season": season_uri,
        "teams": []
    }

    for team_uri, data in teams.items():
        season_data["teams"].append({
            "team": team_uri,
            "teamName": data["teamName"],
            "players": data["players"]
        })

    return JsonResponse(season_data)

def list_arenas(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?arena ?name ?photo WHERE {
            ?arena a nba:Arena ;
                   nba:name ?name .
            OPTIONAL { ?arena nba:photo ?photo . }
        }
        ORDER BY ?name
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    arenas = []
    for r in results:
        arenas.append({
            "id": r["arena"]["value"],
            "name": r["name"]["value"],
            "photo": r.get("photo", {}).get("value", "")
        })

    return render(request, "arenas.html", {"arenas": arenas})

def pagina_arena(request, id):
    # Garante que só o número seja usado para montar o URI corretamente
    arena_uri = f"http://example.org/nba/arena_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?name ?location ?opened ?capacity ?latitude ?longitude ?photo ?homeTeam ?homeTeamName WHERE {{
            <{arena_uri}> a nba:Arena ;
                          nba:name ?name ;
                          nba:location ?location ;
                          nba:homeTeam ?homeTeam .
            OPTIONAL {{ <{arena_uri}> nba:opened ?opened. }}
            OPTIONAL {{ <{arena_uri}> nba:capacity ?capacity. }}
            OPTIONAL {{ <{arena_uri}> nba:latitude ?latitude. }}
            OPTIONAL {{ <{arena_uri}> nba:longitude ?longitude. }}
            OPTIONAL {{ <{arena_uri}> nba:photo ?photo. }}
            OPTIONAL {{ ?homeTeam nba:name ?homeTeamName. }}
        }}
    """)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()["results"]["bindings"]

    if not result:
        return JsonResponse({"error": "Arena not found"}, status=404)

    data = result[0]
    arena = {
        "id": arena_uri,
        "name": data["name"]["value"],
        "location": data["location"]["value"],
        "opened": data.get("opened", {}).get("value"),
        "capacity": data.get("capacity", {}).get("value"),
        "latitude": data.get("latitude", {}).get("value"),
        "longitude": data.get("longitude", {}).get("value"),
        "photo": data.get("photo", {}).get("value"),
        "homeTeam": data["homeTeam"]["value"],
        "homeTeamName": data.get("homeTeamName", {}).get("value")
    }

    return render(request, "arena.html", {"arena": arena})

def mapa_arenas(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?arena ?name ?latitude ?longitude ?photo WHERE {
            ?arena a nba:Arena ;
                   nba:name ?name ;
                   nba:latitude ?latitude ;
                   nba:longitude ?longitude .
            OPTIONAL { ?arena nba:photo ?photo . }
        }
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    arenas = []
    for r in results:
        arenas.append({
            "id": r["arena"]["value"],
            "name": r["name"]["value"],
            "latitude": r["latitude"]["value"],
            "longitude": r["longitude"]["value"],
            "photo": r.get("photo", {}).get("value", "")
        })

    return JsonResponse({"arenas": arenas})

def timeline_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?season ?team ?teamName ?seasonType WHERE {{
            ?p nba:player ?player ;
               nba:season ?season ;
               nba:team ?team ;
               nba:seasonType ?seasonType .
            ?team nba:name ?teamName .
            FILTER(STR(?player) = "{player_uri}")
        }}
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    timeline = []
    seen = set()

    for r in results:
        key = (r["season"]["value"], r["team"]["value"], r["seasonType"]["value"])
        if key in seen:
            continue
        seen.add(key)

        timeline.append({
            "season": r["season"]["value"],
            "team": r["team"]["value"],
            "teamName": r["teamName"]["value"],
            "seasonType": r["seasonType"]["value"]
        })

    return JsonResponse({
        "player": player_uri,
        "timeline": timeline
    })


def grafo_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?team ?teamName ?season WHERE {{
            ?p nba:player <{player_uri}> ;
               nba:team ?team ;
               nba:season ?season .
            ?team nba:name ?teamName .
        }}
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    # Nó do jogador
    nodes.append({
        "id": player_uri,
        "label": f"Player {id}",
        "type": "player"
    })

    for r in results:
        team_uri = r["team"]["value"]
        team_name = r["teamName"]["value"]
        season = r["season"]["value"]

        # Nó da equipa
        if team_uri not in seen_nodes:
            nodes.append({
                "id": team_uri,
                "label": team_name,
                "type": "team"
            })
            seen_nodes.add(team_uri)

        # Nó da season
        if season not in seen_nodes:
            nodes.append({
                "id": season,
                "label": season.split("_")[-1],
                "type": "season"
            })
            seen_nodes.add(season)

        # Aresta jogador → equipa
        edge1 = (player_uri, team_uri)
        if edge1 not in seen_edges:
            edges.append({
                "source": player_uri,
                "target": team_uri,
                "label": "played for"
            })
            seen_edges.add(edge1)

        # Aresta equipa → temporada
        edge2 = (team_uri, season)
        if edge2 not in seen_edges:
            edges.append({
                "source": team_uri,
                "target": season,
                "label": "in season"
            })
            seen_edges.add(edge2)

    return JsonResponse({
        "player": player_uri,
        "nodes": nodes,
        "edges": edges
    })

def companheiros_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?season ?team ?teamName ?companion ?companionName WHERE {{
            ?stat nba:player <{player_uri}> ;
                  nba:season ?season ;
                  nba:team ?team .

            ?stat2 nba:player ?companion ;
                   nba:season ?season ;
                   nba:team ?team .

            ?team nba:name ?teamName .
            ?companion nba:name ?companionName .

            FILTER(?companion != <{player_uri}>)
        }}
        ORDER BY ?season ?team ?companionName
    """)

    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    grouped_data = {
        "player": player_uri,
        "companions": {}
    }

    # Estrutura auxiliar para evitar duplicados
    seen_companions = {}

    for row in results:
        season = row["season"]["value"]
        team = row["team"]["value"]
        team_name = row["teamName"]["value"]
        companion = row["companion"]["value"]
        companion_name = row["companionName"]["value"]

        # Cria as chaves se não existirem
        if season not in grouped_data["companions"]:
            grouped_data["companions"][season] = {}
            seen_companions[season] = {}

        if team not in grouped_data["companions"][season]:
            grouped_data["companions"][season][team] = {
                "teamName": team_name,
                "players": []
            }
            seen_companions[season][team] = set()

        # Adiciona apenas se ainda não foi adicionado para a época e equipa
        if companion not in seen_companions[season][team]:
            grouped_data["companions"][season][team]["players"].append({
                "player": companion,
                "playerName": companion_name
            })
            seen_companions[season][team].add(companion)

    return JsonResponse(grouped_data)

def comparar_jogadores(request):
    player1_id = request.GET.get("player1")
    player2_id = request.GET.get("player2")

    if not player1_id or not player2_id:
        return JsonResponse({
            "message": "Please provide both 'player1' and 'player2' IDs to compare."
        })

    def get_player_data(player_id):
        jogador_uri = f"http://example.org/nba/player_{player_id}"
        sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

        # Dados do jogador
        sparql.setQuery(f"""
            PREFIX nba: <http://example.org/nba/>
            SELECT ?name ?birthdate ?bornIn ?draftYear ?position ?positionName ?height ?weight ?school ?photo WHERE {{
                ?player a nba:Player ;
                        nba:name ?name ;
                        nba:birthdate ?birthdate ;
                        nba:bornIn ?bornIn ;
                        nba:draftYear ?draftYear ;
                        nba:position ?position ;
                        nba:height ?height ;
                        nba:weight ?weight ;
                        nba:school ?school ;
                        nba:photo ?photo .
                ?position nba:name ?positionName .
                FILTER(STR(?player) = "{jogador_uri}")
            }}
        """)
        sparql.setReturnFormat(JSON)
        profile_data = sparql.query().convert()["results"]["bindings"]

        if not profile_data:
            return None

        player_info = profile_data[0]
        dados = {k: player_info[k]["value"] for k in player_info}

        # Participações
        sparql.setQuery(f"""
            PREFIX nba: <http://example.org/nba/>
            SELECT ?team ?teamName ?season ?seasonType WHERE {{
                ?p nba:player ?player ;
                   nba:team ?team ;
                   nba:season ?season ;
                   nba:seasonType ?seasonType .
                ?team nba:name ?teamName .
                FILTER(STR(?player) = "{jogador_uri}")
            }}
            ORDER BY ?season
        """)
        sparql.setReturnFormat(JSON)
        participacoes_data = sparql.query().convert()["results"]["bindings"]

        participacoes = []
        for p in participacoes_data:
            participacoes.append({
                "team": p["team"]["value"],
                "teamName": p["teamName"]["value"],
                "season": p["season"]["value"],
                "seasonType": p["seasonType"]["value"]
            })

        num_teams = len(set(p["team"]["value"] for p in participacoes_data))
        num_seasons = len(set(p["season"]["value"] for p in participacoes_data))

        return {
            "jogador": jogador_uri,
            **dados,
            "participacoes": participacoes,
            "totalTeams": num_teams,
            "totalSeasons": num_seasons
        }

    jogador1 = get_player_data(player1_id)
    jogador2 = get_player_data(player2_id)

    if not jogador1 or not jogador2:
        return JsonResponse({"error": "One or both players not found."}, status=404)

    return JsonResponse({
        "player1": jogador1,
        "player2": jogador2
    })

def comparar_jogadores_template(request):

    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        PREFIX schema: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?player ?playerName WHERE {
            ?p nba:player ?player .
            ?player nba:name ?playerName .
        }
        ORDER BY ?playerName
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    jogadores = [
        {
            "id": result["player"]["value"],
            "nome": result["playerName"]["value"]
        }
        for result in results["results"]["bindings"]
    ]

    return render(request, "compare.html", {"jogadores": jogadores})

def rede_jogadores(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?player ?playerName ?team ?season WHERE {
            ?p a nba:Participation ;
               nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
            ?player nba:name ?playerName .
        }
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    participations = {}
    nodes = {}
    edges_set = set()

    for r in results:
        player = r["player"]["value"]
        name = r["playerName"]["value"]
        team = r["team"]["value"]
        season = r["season"]["value"]
        key = f"{team}_{season}"

        nodes[player] = {"id": player, "label": name}

        if key not in participations:
            participations[key] = []
        participations[key].append(player)

    for players in participations.values():
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                a, b = sorted([players[i], players[j]])
                edges_set.add((a, b))

    edges = [{"from": a, "to": b} for (a, b) in edges_set]

    return JsonResponse({
        "nodes": list(nodes.values()),
        "edges": edges
    })

from SPARQLWrapper import SPARQLWrapper, JSON
from django.conf import settings
from django.http import JsonResponse
from collections import defaultdict
import re

def stats(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)

    stats_data = {}

    # 1. Participações por temporada
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?season (COUNT(?player) AS ?total) WHERE {
            ?p nba:season ?season ;
               nba:player ?player .
        } GROUP BY ?season ORDER BY ?season
    """)
    result = sparql.query().convert()["results"]["bindings"]
    stats_data["participacoes_por_temporada"] = [
        {"season": r["season"]["value"], "total": int(r["total"]["value"])}
        for r in result
    ]

    # 2. Número de jogadores por equipa
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?team (COUNT(DISTINCT ?player) AS ?total) WHERE {
            ?p nba:team ?team ;
               nba:player ?player .
        } GROUP BY ?team
    """)
    result = sparql.query().convert()["results"]["bindings"]
    stats_data["jogadores_por_equipa"] = [
        {"team": r["team"]["value"], "total": int(r["total"]["value"])}
        for r in result
    ]

    # 3. Jogadores com mais temporadas
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?player (COUNT(DISTINCT ?season) AS ?total) WHERE {
            ?p nba:player ?player ;
               nba:season ?season .
        } GROUP BY ?player ORDER BY DESC(?total) LIMIT 10
    """)
    result = sparql.query().convert()["results"]["bindings"]
    stats_data["jogadores_mais_temporadas"] = [
        {"player": r["player"]["value"], "total": int(r["total"]["value"])}
        for r in result
    ]

    # 4. Distribuição por posições
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?position (COUNT(?player) AS ?total) WHERE {
            ?player a nba:Player ;
                    nba:position ?position .
        } GROUP BY ?position
    """)
    result = sparql.query().convert()["results"]["bindings"]
    stats_data["distribuicao_posicoes"] = [
        {"position": r["position"]["value"], "total": int(r["total"]["value"])}
        for r in result
    ]

    # 5. Altura média por posição
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?position ?height WHERE {
            ?player a nba:Player ;
                    nba:position ?position ;
                    nba:height ?height .
        }
    """)
    result = sparql.query().convert()["results"]["bindings"]
    altura_por_posicao = defaultdict(list)
    for r in result:
        pos = r["position"]["value"]
        altura = r["height"]["value"]
        match = re.match(r"(\d+)-(\d+)", altura)
        if match:
            feet, inches = int(match.group(1)), int(match.group(2))
            cm = round((feet * 12 + inches) * 2.54, 1)
            altura_por_posicao[pos].append(cm)
    stats_data["altura_media_por_posicao"] = [
        {"position": pos, "media_cm": round(sum(val)/len(val), 1)}
        for pos, val in altura_por_posicao.items()
    ]

    # 6. Peso médio por posição
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?position ?weight WHERE {
            ?player a nba:Player ;
                    nba:position ?position ;
                    nba:weight ?weight .
        }
    """)
    result = sparql.query().convert()["results"]["bindings"]
    peso_por_posicao = defaultdict(list)
    for r in result:
        pos = r["position"]["value"]
        try:
            peso = int(r["weight"]["value"])
            peso_por_posicao[pos].append(peso)
        except ValueError:
            continue
    stats_data["peso_medio_por_posicao"] = [
        {"position": pos, "media_lb": round(sum(val)/len(val), 1)}
        for pos, val in peso_por_posicao.items()
    ]

    # 7. Distribuição por ano de nascimento
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?birthdate WHERE {
            ?player a nba:Player ;
                    nba:birthdate ?birthdate .
        }
    """)
    result = sparql.query().convert()["results"]["bindings"]
    anos = defaultdict(int)
    for r in result:
        year = r["birthdate"]["value"][:4]
        anos[year] += 1
    stats_data["jogadores_por_ano_nascimento"] = [
        {"year": year, "total": total} for year, total in sorted(anos.items())
    ]

    return JsonResponse(stats_data)
