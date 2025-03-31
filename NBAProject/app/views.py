import json
import re
from collections import defaultdict
from django.views.decorators.cache import cache_page
import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from SPARQLWrapper import JSON, SPARQLWrapper
import random


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

def get_all_teams():
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?team ?actualName ?name ?acronym ?logo WHERE {
            ?team a nba:Team ;
                  nba:name ?name .
            OPTIONAL { ?team nba:actualName ?actualName . }
            OPTIONAL { ?team nba:acronym ?acronym . }
            OPTIONAL { ?team nba:logo ?logo . }
        }
        ORDER BY ?name
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    teams_dict = defaultdict(lambda: {
        "id": "",
        "actualName": "",
        "names": [],
        "acronyms": [],
        "logos": []
    })

    for result in results["results"]["bindings"]:
        team_id = result["team"]["value"]
        team = teams_dict[team_id]
        team["id"] = team_id

        if "actualName" in result:
            team["actualName"] = result["actualName"]["value"]

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
            "name": team["actualName"] if team["actualName"] else team["names"][0],
            "acronym": team["acronyms"][0] if team["acronyms"] else "",
            "logo": team["logos"][0] if team["logos"] else "",
            "other_names": team["names"] if len(team["names"]) > 1 else [],
            "other_acronyms": team["acronyms"][1:] if len(team["acronyms"]) > 1 else [],
            "other_logos": team["logos"][1:] if len(team["logos"]) > 1 else []
        })

    return equipas

def list_equipas(request):
    equipas = get_all_teams()
    return JsonResponse({"equipas": equipas})

def equipas_page(request):
    """Render the teams page with all teams"""
    equipas = get_all_teams()
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

    return render(request, "temporadas.html", {"temporadas": temporadas})
    #return JsonResponse({"temporadas": temporadas})

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
                nba:name ?nome .
            
            OPTIONAL { ?id nba:position ?posObj . 
                        ?posObj nba:name ?position . }
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
        filters.append(f'FILTER(STR(?teamId) = "{team_filter}")')

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
        
    print("Filtered players:", len(jogadores))
    
    return JsonResponse({"jogadores": jogadores})

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
        
            OPTIONAL {{ ?player nba:position ?posObj.
                        ?posObj nba:name ?position. }}
            OPTIONAL {{ ?player nba:birthdate ?birthdate. }}
            OPTIONAL {{ ?player nba:bornIn ?bornIn. }}
            OPTIONAL {{ ?player nba:draftYear ?draftYear. }}
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

        SELECT ?team ?teamName ?teamLogo ?season ?seasonType WHERE {{
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season ;
               nba:seasonType ?seasonType .
            ?team nba:actualName ?teamName ;
                    nba:logo ?teamLogo .
            FILTER(STR(?player) = "{jogador_uri}")
        }}
        ORDER BY DESC(?season)
        LIMIT 1
    """)
    sparql.setReturnFormat(JSON)
    team_data = sparql.query().convert()["results"]["bindings"]

    # Add team data to player info if available
    if team_data:
        dados["teamId"] = team_data[0]["team"]["value"]
        dados["teamName"] = team_data[0]["teamName"]["value"]
        dados["teamLogo"] = team_data[0]["teamLogo"]["value"]
        dados["lastSeason"] = team_data[0]["season"]["value"].split("_")[-1]

    dados["id"] = id

    return render(request, "player.html", dados)

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

    total_participations = 0

    for team_uri, data in teams.items():
        team_participations = len(data["players"])
        total_participations += team_participations
        has_playoff = any("Playoffs" in p["seasonType"] for p in data["players"])

        season_data["teams"].append({
            "team": team_uri,
            "teamName": data["teamName"],
            "players": data["players"],
            "participations": team_participations,
            "has_playoffs": has_playoff
        })

    season_data["total_participations"] = total_participations

    return render(request, "temporada.html", {"season": season_data})
    #return JsonResponse(season_data)

def list_arenas(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?arena ?name ?photo ?location ?opened ?capacity ?homeTeam ?homeTeamName WHERE {
        ?arena a nba:Arena ;
                nba:name ?name .
        OPTIONAL { ?arena nba:photo ?photo . }
        OPTIONAL { ?arena nba:location ?location . }
        OPTIONAL { ?arena nba:capacity ?capacity . }
        OPTIONAL { 
            ?arena nba:homeTeam ?homeTeam .
            ?homeTeam nba:name ?homeTeamName .
        }
        }
        ORDER BY ?name
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    arenas = []
    locations = set()
    years = set()
    home_teams = set()

    seen = set()
    arenas = []

    for r in results:
        arena_id = r["arena"]["value"]
        
        # Avoid duplicates by using arena ID
        if arena_id in seen:
            continue
        seen.add(arena_id)

        arena = {
            "id": arena_id,
            "name": r["name"]["value"],
            "photo": r.get("photo", {}).get("value", ""),
            "location": r.get("location", {}).get("value", ""),
            "capacity": r.get("capacity", {}).get("value", ""),
            "home_team": r.get("homeTeamName", {}).get("value", "")
        }

        if arena["location"]:
            locations.add(arena["location"])
        if arena["home_team"]:
            home_teams.add(arena["home_team"])

        arenas.append(arena)


    return render(request, "arenas.html", {
        "arenas": arenas,
        "locations": sorted(locations),
        "years": sorted(years),
        "home_teams": sorted(home_teams)
    })

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

def page_mapa_arenas(request):
    return render(request, "mapa_arenas.html")

def timeline_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?season ?seasonLabel ?team ?teamName ?teamLogo ?seasonType WHERE {{
            ?p nba:player ?player ;
               nba:season ?season ;
               nba:team ?team ;
               nba:seasonType ?seasonType .
            ?team nba:name ?teamName .
            OPTIONAL {{ ?team nba:logo ?teamLogo . }}
            OPTIONAL {{ ?season nba:label ?seasonLabel . }}
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

        season_label = r.get("seasonLabel", {}).get("value", "")

        timeline.append({
            "season": r["season"]["value"],
            "seasonLabel": season_label,
            "team": r["team"]["value"],
            "teamName": r["teamName"]["value"],
            "teamLogo": r.get("teamLogo", {}).get("value", ""),
            "seasonType": r["seasonType"]["value"]
        })

    # Sort timeline by season (most recent first)
    timeline.sort(key=lambda x: x["season"], reverse=True)

    print("Timeline:", timeline)

    return JsonResponse({
        "player": player_uri,
        "timeline": timeline
    })


def grafo_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    # Get basic player info
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT ?name WHERE {{
            <{player_uri}> nba:name ?name .
        }}
    """)
    sparql.setReturnFormat(JSON)
    player_result = sparql.query().convert()["results"]["bindings"]
    
    # Get player name for better display
    player_name = "Player"
    if player_result and "name" in player_result[0]:
        player_name = player_result[0]["name"]["value"]

    # Query for teams and seasons the player played in
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?team ?teamName ?season ?seasonLabel WHERE {{
            ?p nba:player <{player_uri}> ;
               nba:team ?team ;
               nba:season ?season .
            ?team nba:actualName ?teamName .
            OPTIONAL {{ ?season nba:label ?seasonLabel . }}
        }}
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    # Query for teammates who played with this player on the same teams and seasons
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?teammate ?teammateName ?teammatePhoto ?team ?teamName ?season WHERE {{
            # Find teams and seasons where our player played
            ?p1 nba:player <{player_uri}> ;
                nba:team ?team ;
                nba:season ?season .
            
            # Find all other players who played for those same teams in those same seasons
            ?p2 nba:player ?teammate ;
                nba:team ?team ;
                nba:season ?season .
            
            # Get teammate name and team name
            ?teammate nba:name ?teammateName .
            OPTIONAL {{ ?teammate nba:photo ?teammatePhoto . }}
            ?team nba:actualName ?teamName .
            
            # Exclude the player themselves
            FILTER(?teammate != <{player_uri}>)
        }}
        ORDER BY ?season ?team ?teammateName
    """)
    sparql.setReturnFormat(JSON)
    teammates_results = sparql.query().convert()["results"]["bindings"]

    # Initialize nodes and edges
    nodes = []
    edges = []
    seen_nodes = set()
    seen_edges = set()

    # Add player node
    nodes.append({
        "id": player_uri,
        "label": player_name,
        "type": "player"
    })
    seen_nodes.add(player_uri)

    # Process teams and seasons
    for r in results:
        team_uri = r["team"]["value"]
        team_name = r["teamName"]["value"]
        season = r["season"]["value"]

        # Add team node if not seen yet
        if team_uri not in seen_nodes:
            nodes.append({
                "id": team_uri,
                "label": team_name,
                "type": "team"
            })
            seen_nodes.add(team_uri)

        # Edge: player - team
        edge1 = (player_uri, team_uri)
        if edge1 not in seen_edges:
            edges.append({
                "source": player_uri,
                "target": team_uri,
                "label": "played for"
            })
            seen_edges.add(edge1)

    # Process teammates
    for r in teammates_results:
        teammate_uri = r["teammate"]["value"]
        teammate_name = r["teammateName"]["value"]
        teammate_photo = r["teammatePhoto"]["value"] if "teammatePhoto" in r and r["teammatePhoto"]["value"] else None
        team_uri = r["team"]["value"]
        season = r["season"]["value"]
        
        # Add teammate node if not seen yet
        if teammate_uri not in seen_nodes:
            nodes.append({
                "id": teammate_uri,
                "label": teammate_name,
                "photo": teammate_photo,
                "type": "teammate"
            })
            seen_nodes.add(teammate_uri)
            
        # Edge: teammate - team (same as player)
        edge_to_team = (teammate_uri, team_uri)
        if edge_to_team not in seen_edges:
            edges.append({
                "source": teammate_uri,
                "target": team_uri,
                "label": "played for"
            })
            seen_edges.add(edge_to_team)
            
        # Direct edge: player - teammate (with team and season context)
        edge_to_teammate = (player_uri, teammate_uri, team_uri, season)
        if edge_to_teammate not in seen_edges:
            edges.append({
                "source": player_uri,
                "target": teammate_uri,
                "label": "played with",
                "team": team_uri,
                "season": season,
                "type": "teammate"
            })
            seen_edges.add(edge_to_teammate)

        print("nodes:", nodes)

    return JsonResponse({
        "player": player_uri,
        "playerName": player_name,
        "nodes": nodes,
        "edges": edges
    })

def companheiros_jogador(request, id):
    player_uri = f"http://example.org/nba/player_{id}"
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)

    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>

        SELECT DISTINCT ?season ?seasonLabel ?team ?teamName ?teamLogo ?companion ?companionName ?companionPhoto ?seasonType WHERE {{
            # Find teams and seasons where this player played
            ?p1 nba:player <{player_uri}> ;
                nba:team ?team ;
                nba:season ?season ;
                nba:seasonType ?seasonType .
            
            # Find all other players who played for those same teams in those same seasons
            ?p2 nba:player ?companion ;
                nba:team ?team ;
                nba:season ?season ;
                nba:seasonType ?seasonType .
            
            # Get team information
            ?team nba:name ?teamName .
            OPTIONAL {{ ?team nba:logo ?teamLogo . }}
            
            # Get companion information
            ?companion nba:name ?companionName .
            OPTIONAL {{ ?companion nba:photo ?companionPhoto . }}
            
            # Get season label if available
            OPTIONAL {{ ?season nba:label ?seasonLabel . }}
            
            # Exclude the player themselves
            FILTER(?companion != <{player_uri}>)
        }}
        ORDER BY DESC(?season) ?teamName ?companionName
    """)

    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    # Initialize the response structure
    grouped_data = {
        "player": player_uri,
        "companions": {}
    }

    # Process each result row
    for row in results:
        season = row["season"]["value"]
        team = row["team"]["value"]
        team_name = row["teamName"]["value"]
        companion = row["companion"]["value"]
        companion_name = row["companionName"]["value"]
        season_type = row["seasonType"]["value"]
        
        # Get the season label if available, otherwise format the season ID
        if "seasonLabel" in row:
            season_label = row["seasonLabel"]["value"]
        else:
            season_label = season.split("_")[-1]
            
        # Set default values for optional fields
        team_logo = row.get("teamLogo", {}).get("value", "")
        companion_photo = row.get("companionPhoto", {}).get("value", "")
        
        # Create season entry if it doesn't exist
        if season not in grouped_data["companions"]:
            grouped_data["companions"][season] = {
                "seasonLabel": season_label,
                "teams": {}
            }
            
        # Create team entry if it doesn't exist
        if team not in grouped_data["companions"][season]["teams"]:
            grouped_data["companions"][season]["teams"][team] = {
                "teamName": team_name,
                "teamLogo": team_logo,
                "players": []
            }
            
        # Check if this companion is already added (avoid duplicates)
        player_exists = any(p["player"] == companion for p in grouped_data["companions"][season]["teams"][team]["players"])
        
        # Add player if not already added
        if not player_exists:
            grouped_data["companions"][season]["teams"][team]["players"].append({
                "player": companion,
                "playerName": companion_name,
                "playerPhoto": companion_photo
            })

    # Convert the response to a more frontend-friendly format
    response_data = {
        "player": player_uri,
        "companions": {}
    }
    
    # Process each season
    for season, season_data in grouped_data["companions"].items():
        response_data["companions"][season] = {
            "seasonLabel": season_data["seasonLabel"],
        }
        
        # Process each team in this season
        for team, team_data in season_data["teams"].items():
            response_data["companions"][season][team] = {
                "teamName": team_data["teamName"],
                "teamLogo": team_data["teamLogo"],
                "players": team_data["players"]
            }
    
    return JsonResponse(response_data)

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

def get_all_seasons():
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT DISTINCT ?season WHERE {
            ?p nba:season ?season .
        }
        ORDER BY ?season
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]
    seasons = [r["season"]["value"].split("_")[-1] for r in results]
    return sorted(seasons)

@cache_page(60 * 60)
def rede_jogadores(request):
    season = request.GET.get("season", "2022")
    full_season_uri = f"http://example.org/nba/season_{season}"

    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>
        SELECT DISTINCT ?player ?playerName ?team ?season WHERE {{
            ?p a nba:Participation ;
               nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
            ?player nba:name ?playerName .
            FILTER(?season = <{full_season_uri}>)
        }}
        LIMIT 50
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
        season_val = r["season"]["value"]
        key = f"{team}_{season_val}"
        nodes[player] = {"id": player, "label": name}
        participations.setdefault(key, []).append(player)

    for players in participations.values():
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                a, b = sorted([players[i], players[j]])
                edges_set.add((a, b))

    edges = [{"from": a, "to": b} for (a, b) in edges_set]

    context = {
        "nodes_json": json.dumps(list(nodes.values())),
        "edges_json": json.dumps(edges),
        "selected_season": season,
        "season_range": list(range(2000, 2024))  # Podes ajustar aqui as seasons disponíveis
    }

    return render(request, "playerNetwork.html", context)


@cache_page(60 * 60)
def expandir_jogador(request, player_id):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setQuery(f"""
        PREFIX nba: <http://example.org/nba/>
        SELECT DISTINCT ?player ?playerName ?team ?season WHERE {{
            ?p a nba:Participation ;
               nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
            ?player nba:name ?playerName .
            FILTER EXISTS {{
                ?p2 nba:player <{player_id}> ;
                     nba:team ?team ;
                     nba:season ?season .
            }}
        }}
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()["results"]["bindings"]

    participations = {}
    nodes = {}
    edges_set = set()

    for r in results:
        p_uri = r["player"]["value"]
        name = r["playerName"]["value"]
        team = r["team"]["value"]
        season = r["season"]["value"]
        key = f"{team}_{season}"

        nodes[p_uri] = {"id": p_uri, "label": name}
        participations.setdefault(key, []).append(p_uri)

    for players in participations.values():
        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                a, b = sorted([players[i], players[j]])
                edges_set.add((a, b))

    edges = [{"from": a, "to": b} for (a, b) in edges_set]

    return JsonResponse({"nodes": list(nodes.values()), "edges": edges})

def extract_id(uri):
    return uri.split("_")[-1] if "_" in uri else uri

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
        {"season": extract_id(r["season"]["value"]), "total": int(r["total"]["value"])}
        for r in result
    ]

    # 2. Jogadores por equipa
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?team_id ?team_name (COUNT(DISTINCT ?player) AS ?total) WHERE {
            ?p nba:team ?team ;
               nba:player ?player .
            ?team nba:name ?team_name .
            BIND(STRAFTER(STR(?team), "_") AS ?team_id)
        } GROUP BY ?team_id ?team_name
    """)
    result = sparql.query().convert()["results"]["bindings"]
    seen_teams = {}
    for r in result:
        team_id = r["team_id"]["value"]
        name = r["team_name"]["value"]
        total = int(r["total"]["value"])
        # Se já vimos o ID, não sobrescrevemos o nome
        if team_id not in seen_teams:
            seen_teams[team_id] = {"team": team_id, "name": name, "total": total}
    stats_data["jogadores_por_equipa"] = list(seen_teams.values())

    # 3. Jogadores com mais temporadas
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT ?player ?name (COUNT(DISTINCT ?season) AS ?total) WHERE {
            ?p nba:player ?player ;
               nba:season ?season .
            ?player nba:name ?name .
        } GROUP BY ?player ?name ORDER BY DESC(?total) LIMIT 10
    """)
    result = sparql.query().convert()["results"]["bindings"]
    stats_data["jogadores_mais_temporadas"] = [
        {
            "player": extract_id(r["player"]["value"]),
            "name": r["name"]["value"],
            "total": int(r["total"]["value"])
        }
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
        {
            "position": extract_id(r["position"]["value"]),
            "total": int(r["total"]["value"])
        }
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
        pos = extract_id(r["position"]["value"])
        altura = r["height"]["value"]
        cm = None
        match = re.match(r"(\d+)-(\d+)", altura)
        if match:
            feet, inches = int(match.group(1)), int(match.group(2))
            cm = round((feet * 12 + inches) * 2.54, 1)
        else:
            try:
                cm = float(altura)
            except ValueError:
                continue
        if cm:
            altura_por_posicao[pos].append(cm)
    stats_data["altura_media_por_posicao"] = [
        {"position": pos, "media_cm": round(sum(vals)/len(vals), 1)}
        for pos, vals in altura_por_posicao.items()
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
        pos = extract_id(r["position"]["value"])
        try:
            peso = int(r["weight"]["value"])
            peso_por_posicao[pos].append(peso)
        except ValueError:
            continue
    stats_data["peso_medio_por_posicao"] = [
        {"position": pos, "media_lb": round(sum(val)/len(val), 1)}
        for pos, val in peso_por_posicao.items()
    ]

    # 7. Jogadores por ano de nascimento
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
        if year.isdigit():
            anos[year] += 1
    stats_data["jogadores_por_ano_nascimento"] = [
        {"year": year, "total": total} for year, total in sorted(anos.items())
    ]

    return render(request, "stats.html", {
        "stats_json": json.dumps(stats_data),
        "stats_data": stats_data
    })


def quiz_questions(request):
    sparql = SPARQLWrapper(settings.SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)

    # 1. Player-Team-Season Questions
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT DISTINCT ?player ?playerName ?team ?teamName ?season WHERE {
            ?p nba:player ?player ;
               nba:team ?team ;
               nba:season ?season .
            ?player nba:name ?playerName .
            ?team nba:name ?teamName .
        } LIMIT 300
    """)
    results = sparql.query().convert()["results"]["bindings"]

    player_team_q = []
    for r in results:
        player_name = r["playerName"]["value"]
        team_name = r["teamName"]["value"]
        season = r["season"]["value"].split("_")[-1]

        # 💡 skip invalid names
        if not team_name.strip() or team_name.strip().lower() == "u":
            continue

        player_team_q.append({
            "type": "player-team-season",
            "text": f"Which team did {player_name} play for in season {season}?",
            "correct": team_name
        })

    # 2. Arena-HomeTeam Questions
    sparql.setQuery("""
        PREFIX nba: <http://example.org/nba/>
        SELECT DISTINCT ?arenaName ?teamName WHERE {
            ?arena a nba:Arena ;
                   nba:name ?arenaName ;
                   nba:homeTeam ?team .
            ?team nba:name ?teamName .
        } LIMIT 100
    """)
    results = sparql.query().convert()["results"]["bindings"]

    arena_team_q = []
    for r in results:
        arena_name = r["arenaName"]["value"]
        team_name = r["teamName"]["value"]
        arena_team_q.append({
            "type": "arena-home-team",
            "text": f"What is the home team of the arena {arena_name}?",
            "correct": team_name
        })

    # Combine and prepare options
    all = player_team_q + arena_team_q
    random.shuffle(all)
    selected = all[:20]

    # Get pool of all teams
    all_teams = list({q["correct"] for q in all})

    for q in selected:
        wrong = [t for t in all_teams if t != q["correct"]]
        options = [q["correct"]] + random.sample(wrong, min(3, len(wrong)))
        random.shuffle(options)
        q["options"] = [{"text": opt, "is_correct": opt == q["correct"]} for opt in options]
        del q["correct"]  # no need to expose it

    return JsonResponse({"questions": selected})

def quiz_page(request):
    return render(request, "quiz.html")
