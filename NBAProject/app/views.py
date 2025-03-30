from collections import defaultdict

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from SPARQLWrapper import JSON, SPARQLWrapper


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

    equipas = []
    for result in results["results"]["bindings"]:
        equipa = {
            "id": result["team"]["value"],
            "nome": result["name"]["value"],
            "acronym": result.get("acronym", {}).get("value", ""),
            "logo": result.get("logo", {}).get("value", "")
        }
        equipas.append(equipa)

    return JsonResponse({"equipas": equipas})


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

def players_page(request):
    """
    Render the players listing page with filters
    """
    return render(request, 'players.html')

def get_player_countries(request):
    """Get all available player countries for the filter dropdown"""
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?bornIn WHERE {
            ?player rdf:type nba:Player ;
                    nba:bornIn ?bornIn .
            FILTER(?bornIn != "")
        }
        ORDER BY ?bornIn
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    countries = []
    for result in results["results"]["bindings"]:
        country_name = result["bornIn"]["value"]
        if country_name:  # Only add non-empty countries
            countries.append({"name": country_name})
    
    return JsonResponse({"countries": countries})

def get_player_schools(request):
    """Get all available player schools for the filter dropdown"""
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?school WHERE {
            ?player rdf:type nba:Player ;
                    nba:school ?school .
            FILTER(?school != "")
        }
        ORDER BY ?school
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    schools = []
    for result in results["results"]["bindings"]:
        school_name = result["school"]["value"]
        if school_name:  # Only add non-empty schools
            schools.append({"name": school_name})
    
    return JsonResponse({"schools": schools})

def filter_players(request):
    """
    API endpoint to filter players based on search criteria
    """
    # Get filter parameters from request
    name_filter = request.GET.get('name', '')
    position_filter = request.GET.get('position', '')
    team_filter = request.GET.get('team', '')
    nationality_filter = request.GET.get('nationality', '')
    school_filter = request.GET.get('school', '')
    draft_year_min = request.GET.get('draftYearMin', '')
    draft_year_max = request.GET.get('draftYearMax', '')
    height_min = request.GET.get('heightMin', '')
    height_max = request.GET.get('heightMax', '')
    
    # Initialize SPARQL wrapper
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    
    # Build query with filters
    query = """
        PREFIX nba: <http://example.org/nba/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?id ?nome ?position ?height ?weight ?draftYear ?birthdate ?bornIn ?school ?photo ?teamId ?teamName
        WHERE {
            ?id rdf:type nba:Player ;
                nba:name ?nome ;
                nba:position ?posObj .
            ?posObj nba:name ?position .
            
            OPTIONAL { ?id nba:height ?height . }
            OPTIONAL { ?id nba:weight ?weight . }
            OPTIONAL { ?id nba:draftYear ?draftYear . }
            OPTIONAL { ?id nba:birthdate ?birthdate . }
            OPTIONAL { ?id nba:bornIn ?bornIn . }
            OPTIONAL { ?id nba:school ?school . }
            OPTIONAL { ?id nba:photo ?photo . }

            OPTIONAL {
                ?participation nba:player ?id ;
                              nba:team ?teamId ;
                              nba:season nba:season_2022 .
                ?teamId nba:actualName ?teamName .
            }
    """
    
    # Add filters
    filters = []
    
    # Name filter (case insensitive)
    if name_filter:
        filters.append(f'FILTER(REGEX(?nome, "{name_filter}", "i"))')
    
    # Position filter
    if position_filter:
        filters.append(f'FILTER(?position = "{position_filter}")')
    
    # Team filter
    if team_filter:
        if "?participation nba:player ?id" not in query:
            query += """
                ?participation nba:player ?id ;
                              nba:team ?teamId .
                ?teamId nba:actualName ?teamName .
            """
        filters.append(f'FILTER(STR(?team) = "{team_filter}")')

    # Nationality filter
    if nationality_filter:
        filters.append(f'FILTER(?bornIn = "{nationality_filter}")')
    
    # School filter
    if school_filter:
        filters.append(f'FILTER(?school = "{school_filter}")')
    
    # Draft year range filter
    if draft_year_min:
        filters.append(f'FILTER(xsd:integer(?draftYear) >= {draft_year_min})')
    
    if draft_year_max:
        filters.append(f'FILTER(xsd:integer(?draftYear) <= {draft_year_max})')
    
    # Height range filter (requires parsing the height format "6-9")
    if height_min:
        # Convert height format like "6-9" to total inches for comparison
        feet, inches = height_min.split('-')
        min_inches = int(feet) * 12 + int(inches)
        
        # Create a custom filter to compare the height string
        height_filter = f"""
            FILTER(
                IF(REGEX(?height, "^[0-9]-[0-9]+$"),
                    (xsd:integer(SUBSTR(?height, 1, 1)) * 12 + xsd:integer(SUBSTR(?height, 3))),
                    0
                ) >= {min_inches}
            )
        """
        filters.append(height_filter)
    
    if height_max:
        feet, inches = height_max.split('-')
        max_inches = int(feet) * 12 + int(inches)
        
        height_filter = f"""
            FILTER(
                IF(REGEX(?height, "^[0-9]-[0-9]+$"),
                    (xsd:integer(SUBSTR(?height, 1, 1)) * 12 + xsd:integer(SUBSTR(?height, 3))),
                    1000
                ) <= {max_inches}
            )
        """
        filters.append(height_filter)
    
    # Add all filters to the query
    for filter_stmt in filters:
        query += f"    {filter_stmt}\n"
    
    # Close the query
    query += """
        }
        ORDER BY ?nome
    """
    
    # Execute the query
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    # Process results
    jogadores = []
    for result in results["results"]["bindings"]:
        jogador = {
            "id": result["id"]["value"],
            "nome": result["nome"]["value"],
            "position": result.get("position", {}).get("value", ""),
            "height": result.get("height", {}).get("value", ""),
            "weight": result.get("weight", {}).get("value", ""),
            "draftYear": result.get("draftYear", {}).get("value", ""),
            "birthdate": result.get("birthdate", {}).get("value", ""),
            "bornIn": result.get("bornIn", {}).get("value", ""),
            "school": result.get("school", {}).get("value", ""),
            "photo": result.get("photo", {}).get("value", ""),
            "teamId": result.get("teamId", {}).get("value", ""),
            "teamName": result.get("teamName", {}).get("value", "")
        }
        jogadores.append(jogador)
    
    return JsonResponse({"jogadores": jogadores})

def pagina_jogador(request, id):
    jogador_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    # Query de dados do jogador
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?name ?birthdate ?bornIn ?draftYear ?position ?height ?weight ?school ?photo WHERE {{
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
            FILTER(STR(?player) = "{jogador_uri}")
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

        SELECT ?name ?acronym ?logo ?city ?state ?conference ?division ?arena WHERE {{
            ?team a nba:Team ;
                  nba:name ?name .
            OPTIONAL {{ ?team nba:acronym ?acronym . }}
            OPTIONAL {{ ?team nba:logo ?logo . }}
            OPTIONAL {{ ?team nba:city ?city . }}
            OPTIONAL {{ ?team nba:state ?state . }}
            OPTIONAL {{ ?team nba:conference ?conference . }}
            OPTIONAL {{ ?team nba:division ?division . }}
            OPTIONAL {{ ?team nba:arena ?arena . }}
            FILTER(STR(?team) = "{team_uri}")
        }}
    """)
    sparql.setReturnFormat(JSON)
    result = sparql.query().convert()["results"]["bindings"]

    if not result:
        return JsonResponse({"error": "Team not found"}, status=404)

    team_data = result[0]
    team_info = {
        "id": team_uri,
        "name": team_data["name"]["value"],
        "acronym": team_data.get("acronym", {}).get("value", ""),
        "logo": team_data.get("logo", {}).get("value", ""),
        "city": team_data.get("city", {}).get("value", ""),
        "state": team_data.get("state", {}).get("value", ""),
        "conference": team_data.get("conference", {}).get("value", ""),
        "division": team_data.get("division", {}).get("value", ""),
        "arena": team_data.get("arena", {}).get("value", "")
    }

    # 2. Jogadores por temporada (agrupado)
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?player ?playerName ?season ?seasonType WHERE {{
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

    return JsonResponse(team_info)


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
            SELECT ?name ?birthdate ?bornIn ?draftYear ?position ?height ?weight ?school ?photo WHERE {{
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

        return {
            "jogador": jogador_uri,
            **dados,
            "participacoes": participacoes
        }

    jogador1 = get_player_data(player1_id)
    jogador2 = get_player_data(player2_id)

    if not jogador1 or not jogador2:
        return JsonResponse({"error": "One or both players not found."}, status=404)

    return JsonResponse({
        "player1": jogador1,
        "player2": jogador2
    })