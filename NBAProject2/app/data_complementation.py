"""
NBA Data Complementation Script

This module provides functionality to complement existing NBA data with information
from Wikidata and DBpedia using SPARQL queries.

Author: NBA Project Team
"""

import json
import re
from typing import Dict, List, Optional, Any
from django.http import JsonResponse
from SPARQLWrapper import SPARQLWrapper2, JSON


class DataComplementationService:
    """Service class for complementing NBA data with external semantic sources"""
    
    def __init__(self):
        # Initialize SPARQL endpoints
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.dbpedia_endpoint = "https://dbpedia.org/sparql"
        
        # Initialize SPARQL wrappers
        self.wikidata_sparql = SPARQLWrapper2(self.wikidata_endpoint)
        self.dbpedia_sparql = SPARQLWrapper2(self.dbpedia_endpoint)
        
        # Set timeouts
        self.wikidata_sparql.setTimeout(30)
        self.dbpedia_sparql.setTimeout(30)

    def _clean_team_name(self, team_name: str) -> str:
        """Clean and normalize team names for better matching.
        Returns original name if no cleaning rule applies."""
        team_name = team_name.strip()
        # Handle common variations - if name not found, returns original
        replacements = {
            "LA Clippers": "Los Angeles Clippers",
        }
        return replacements.get(team_name, team_name)

    def _clean_construction_cost(self, cost_value: str) -> str:
        """
        Clean and format construction cost values from DBpedia
        """
        print(f"DEBUG _clean_construction_cost: Input value: '{cost_value}' (type: {type(cost_value)})")
        
        if not cost_value or cost_value.strip() == '':
            print("DEBUG _clean_construction_cost: Empty or None value, returning empty string")
            return ""
        
        try:
            # Remove language tags like "@en"
            cost_str = cost_value.split('@')[0].strip('"')
            print(f"DEBUG _clean_construction_cost: After removing @lang: '{cost_str}'")
            
            # Handle scientific notation with datatype URIs
            # Example: "1.4E9"^^<http://dbpedia.org/datatype/usDollar>
            if '^^' in cost_str:
                cost_str = cost_str.split('^^')[0].strip('"')
                print(f"DEBUG _clean_construction_cost: After removing ^^datatype: '{cost_str}'")
            
            # Handle scientific notation (e.g., "1.4E9")
            if 'E' in cost_str.upper():
                print(f"DEBUG _clean_construction_cost: Found scientific notation: '{cost_str}'")
                try:
                    # Convert scientific notation to float
                    cost_float = float(cost_str)
                    print(f"DEBUG _clean_construction_cost: Converted to float: {cost_float}")
                    
                    # Format based on magnitude
                    if cost_float >= 1e9:
                        result = f"${cost_float / 1e9:.1f} billion"
                        print(f"DEBUG _clean_construction_cost: Formatted as billion: '{result}'")
                        return result
                    elif cost_float >= 1e6:
                        result = f"${cost_float / 1e6:.1f} million"
                        print(f"DEBUG _clean_construction_cost: Formatted as million: '{result}'")
                        return result
                    elif cost_float >= 1e3:
                        result = f"${cost_float / 1e3:.1f} thousand"
                        print(f"DEBUG _clean_construction_cost: Formatted as thousand: '{result}'")
                        return result
                    else:
                        result = f"${cost_float:,.0f}"
                        print(f"DEBUG _clean_construction_cost: Formatted as dollars: '{result}'")
                        return result
                except ValueError as ve:
                    print(f"DEBUG _clean_construction_cost: ValueError converting scientific notation: {ve}")
                    pass
            
            # Handle regular numeric values
            # Remove any non-numeric characters except decimal points
            numeric_str = re.sub(r'[^\d.]', '', cost_str)
            print(f"DEBUG _clean_construction_cost: Extracted numeric string: '{numeric_str}'")
            
            if numeric_str:
                try:
                    cost_float = float(numeric_str)
                    print(f"DEBUG _clean_construction_cost: Converted numeric to float: {cost_float}")
                    
                    if cost_float >= 1e6:
                        result = f"${cost_float / 1e6:.1f} million"
                        print(f"DEBUG _clean_construction_cost: Formatted numeric as million: '{result}'")
                        return result
                    elif cost_float >= 1e3:
                        result = f"${cost_float / 1e3:.1f} thousand"
                        print(f"DEBUG _clean_construction_cost: Formatted numeric as thousand: '{result}'")
                        return result
                    else:
                        result = f"${cost_float:,.0f}"
                        print(f"DEBUG _clean_construction_cost: Formatted numeric as dollars: '{result}'")
                        return result
                except ValueError as ve:
                    print(f"DEBUG _clean_construction_cost: ValueError converting numeric: {ve}")
                    pass
            
            # If all else fails, return the cleaned string
            print(f"DEBUG _clean_construction_cost: Fallback, returning cleaned string: '{cost_str}'")
            return cost_str if cost_str else ""
            
        except Exception as e:
            print(f"ERROR _clean_construction_cost: Exception cleaning construction cost '{cost_value}': {e}")
            return cost_value

    def get_team_coaches_from_wikidata(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Get historical coaches for an NBA team from Wikidata
        """
        try:
            clean_name = self._clean_team_name(team_name)
            
            query = f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?coach ?coachLabel ?teamLabel ?image ?start_date ?end_date WHERE {{
                ?team wdt:P31 wd:Q13393265 ;  # instance of basketball team
                    wdt:P118 wd:Q155223 ;    # league: National Basketball Association
                    rdfs:label ?teamLabel .
                
                ?coach p:P6087 ?statement .      # statement where coach coached a team
                  ?statement ps:P6087 ?team .      # the actual team coached
                  OPTIONAL {{ ?statement pq:P580 ?start_date . }}  # start time
                  OPTIONAL {{ ?statement pq:P582 ?end_date . }}    # end time
                
                  ?coach wdt:P106 wd:Q5137571 ;    # occupation: basketball coach
                         rdfs:label ?coachLabel .
                  OPTIONAL {{ ?coach wdt:P18 ?image . }}            # image
                
                FILTER(LANG(?teamLabel) = "en")
                FILTER(LANG(?coachLabel) = "en") 
                FILTER(CONTAINS(LCASE(?teamLabel), LCASE("{clean_name}")))
                
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            """

            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()

            coaches = []
            for result in results.bindings:
                coach_data = {
                    "coach_id": result["coach"].value.split("/")[-1] if "coach" in result else "",
                    "name": result["coachLabel"].value if "coachLabel" in result else "",
                    "image": result["image"].value if "image" in result else "",
                    "start_date": result["start_date"].value if "start_date" in result else "",
                    "end_date": result["end_date"].value if "end_date" in result else "",
                    "source": "wikidata"
                }
                coaches.append(coach_data)
                
            return coaches
            
        except Exception as e:
            print(f"Error querying Wikidata for coaches: {e}")
            return []

    def get_coach_info_from_wikidata(self, coach_entity_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a basketball coach from Wikidata using their entity ID.
        Includes biography, career info, education, and affiliations.
        """
        try:
            query = f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX p: <http://www.wikidata.org/prop/>
            PREFIX ps: <http://www.wikidata.org/prop/statement/>
            PREFIX pq: <http://www.wikidata.org/prop/qualifier/>

            SELECT ?coachLabel ?dob ?pobLabel ?genderLabel ?citizenshipLabel ?languageLabel
                   ?positionLabel ?image ?givenNameLabel ?familyNameLabel
                   ?schoolLabel ?trainerLabel ?teamLabel ?start ?end
            WHERE {{
                wd:{coach_entity_id} rdfs:label ?coachLabel .
                FILTER(LANG(?coachLabel) = "en")

                OPTIONAL {{ wd:{coach_entity_id} wdt:P569 ?dob . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P19 ?pob . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P21 ?gender . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P27 ?citizenship . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P103 ?language . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P413 ?position . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P18 ?image . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P735 ?givenName . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P734 ?familyName . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P69 ?school . }}
                OPTIONAL {{ wd:{coach_entity_id} wdt:P1066 ?trainer . }}

                OPTIONAL {{
                    wd:{coach_entity_id} p:P6087 ?coachStatement .
                    ?coachStatement ps:P6087 ?team ;
                                   pq:P580 ?start ;
                                   pq:P582 ?end .
                    ?team rdfs:label ?teamLabel .
                    FILTER(LANG(?teamLabel) = "en")
                }}
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            """

            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()

            coach_info = {
                "coach_link": f"https://www.wikidata.org/wiki/{coach_entity_id}",
                "name": "",
                "date_of_birth": "",
                "place_of_birth": "",
                "gender": "",
                "citizenship": "",
                "native_language": "",
                "position": "",
                "image": "",
                "educated_at": set(),
                "trained_by": set(),
                "teams": [],
                "source": "wikidata"
            }

            for result in results.bindings:
                # Access Value objects properly using .value attribute
                coach_info["name"] = result["coachLabel"].value if "coachLabel" in result else coach_info["name"]
                coach_info["date_of_birth"] = result["dob"].value if "dob" in result else coach_info["date_of_birth"]
                coach_info["place_of_birth"] = result["pobLabel"].value if "pobLabel" in result else coach_info["place_of_birth"]
                coach_info["gender"] = result["genderLabel"].value if "genderLabel" in result else coach_info["gender"]
                coach_info["citizenship"] = result["citizenshipLabel"].value if "citizenshipLabel" in result else coach_info["citizenship"]
                coach_info["native_language"] = result["languageLabel"].value if "languageLabel" in result else coach_info["native_language"]
                coach_info["position"] = result["positionLabel"].value if "positionLabel" in result else coach_info["position"]
                coach_info["image"] = result["image"].value if "image" in result else coach_info["image"]

                if "schoolLabel" in result:
                    coach_info["educated_at"].add(result["schoolLabel"].value)
                if "trainerLabel" in result:
                    coach_info["trained_by"].add(result["trainerLabel"].value)

                # Add teams with optional period
                if "teamLabel" in result:
                    team = {
                        "name": result["teamLabel"].value,
                        "start": result["start"].value if "start" in result else "",
                        "end": result["end"].value if "end" in result else ""
                    }
                    if team not in coach_info["teams"]:
                        coach_info["teams"].append(team)

            # Convert sets to lists
            coach_info["educated_at"] = list(coach_info["educated_at"])
            coach_info["trained_by"] = list(coach_info["trained_by"])

            return coach_info

        except Exception as e:
            print(f"Error querying Wikidata for coach info: {e}")
            return {}

    def get_player_awards_from_wikidata(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Get awards and achievements for an NBA player from Wikidata
        """
        try:
            # Clean and prepare the player name for the query
            clean_player_name = player_name.strip()
            
            query = f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?player ?playerLabel ?award ?awardLabel WHERE {{
                ?player wdt:P106 wd:Q3665646 ;      # occupation: basketball player
                        wdt:P118 wd:Q155223 ;       # league: NBA
                        rdfs:label ?playerLabel ;
                        wdt:P166 ?award .           # award received
                
                ?award rdfs:label ?awardLabel .
                
                FILTER(LANG(?playerLabel) = "en")
                FILTER(LANG(?awardLabel) = "en")
                FILTER(CONTAINS(LCASE(?playerLabel), LCASE("{clean_player_name}")))
                
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            LIMIT 50
            """
            
            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()
            
            awards = []
            for result in results.bindings:
                award_data = {
                    "player": result["playerLabel"].value if "playerLabel" in result else "",
                    "award": result["awardLabel"].value if "awardLabel" in result else "",
                    "award_link": result["award"].value if "award" in result else "",
                    "source": "wikidata"
                }
                awards.append(award_data)
                
            return awards
            
        except Exception as e:
            print(f"Error querying Wikidata for player awards: {e}")
            return []

    def get_arena_information_from_dbpedia(self, arena_name: str) -> Dict[str, Any]:
        """
        Get additional arena information from DBpedia
        """
        try:
            # Clean arena name for better matching
            clean_name = arena_name.strip()

            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX foaf: <http://foaf.org/0.1/>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX dbp: <http://dbpedia.org/property/>

            SELECT DISTINCT ?arena ?label ?architect ?architectName ?architectThumbnail ?constructionCost ?openingDate ?buildingStartDate WHERE {{
                ?arena a dbo:Stadium ;
                       rdfs:label ?label .

                OPTIONAL {{ 
                    ?arena dbp:architect ?architect .
                    OPTIONAL {{ ?architect rdfs:label ?architectName . FILTER(LANG(?architectName) = "en") }}
                    OPTIONAL {{ ?architect dbo:thumbnail ?architectThumbnail . }}
                }}
                OPTIONAL {{ ?arena dbp:cost ?constructionCost . }}
                OPTIONAL {{ ?arena dbo:cost ?constructionCost . }}
                OPTIONAL {{ ?arena dbp:opened ?openingDate . }}
                OPTIONAL {{ ?arena dbo:buildingStartDate ?buildingStartDate . }}

                FILTER(LANG(?label) = "en")
                FILTER(CONTAINS(LCASE(?label), LCASE("{clean_name}")))
                FILTER(REGEX(?label, "(Arena|Center|Stadium)", "i"))
            }}
            """

            self.dbpedia_sparql.setQuery(query)
            results = self.dbpedia_sparql.query()

            arena_info = {}
            architects = []
            best_cost = ""

            for i, result in enumerate(results.bindings):
                print(f"DEBUG: Processing result {i}: {dict(result)}")
                
                # Build basic arena info from the first result, but keep updating cost if we find better ones
                if not arena_info:
                    arena_info = {
                        "name": result["label"].value if "label" in result else "",
                        "construction_cost": "",  # We'll update this as we find valid costs
                        "opening_date": result["openingDate"].value if "openingDate" in result else "",
                        "building_start_date": result["buildingStartDate"].value if "buildingStartDate" in result else "",
                        "source": "dbpedia"
                    }
                
                # Process construction cost from any result that has it
                if "constructionCost" in result:
                    raw_cost = result["constructionCost"].value
                    print(f"DEBUG: Raw construction cost from result {i}: '{raw_cost}' (type: {type(raw_cost)})")
                    
                    if raw_cost and raw_cost.strip() != '':  # Only process non-empty costs
                        cleaned_cost = self._clean_construction_cost(raw_cost)
                        print(f"DEBUG: Cleaned construction cost from result {i}: '{cleaned_cost}'")
                        
                        if cleaned_cost and not best_cost:  # Use the first valid cost we find
                            best_cost = cleaned_cost
                            arena_info["construction_cost"] = cleaned_cost
                            print(f"DEBUG: Using cost from result {i}: '{cleaned_cost}'")
                    else:
                        print(f"DEBUG: Skipping empty cost from result {i}")

                # Collect architect information
                architect_uri = result["architect"].value if "architect" in result else ""
                architect_name = result["architectName"].value if "architectName" in result else ""
                architect_thumbnail = result["architectThumbnail"].value if "architectThumbnail" in result else ""

                if architect_uri and architect_name:
                    # Check if this architect is already in our list
                    existing_architect = next((arch for arch in architects if arch["uri"] == architect_uri), None)
                    if not existing_architect:
                        architects.append({
                            "uri": architect_uri,
                            "name": architect_name,
                            "thumbnail": architect_thumbnail if architect_thumbnail else None
                        })

            # Add architects to arena info
            arena_info["architects"] = architects

            return arena_info

        except Exception as e:
            print(f"Error querying DBpedia for arena info: {e}")
            return {}

    def get_all_nba_coaches_from_wikidata(self) -> List[Dict[str, Any]]:
        """
        Get all NBA coaches from Wikidata
        """
        try:
            query = """
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX p: <http://www.wikidata.org/prop/>
            PREFIX ps: <http://www.wikidata.org/prop/statement/>
            PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
            
            SELECT DISTINCT ?coach ?coachLabel ?image ?birthDate ?nationalityLabel ?teamLabel ?startTime ?endTime WHERE {
              ?coach wdt:P106 wd:Q5137571 ;  # occupation: basketball coach
                     rdfs:label ?coachLabel .
              
              # Filter for coaches who have coached NBA teams
              ?coach p:P6087 ?coachStatement .
              ?coachStatement ps:P6087 ?team .
              ?team wdt:P31 wd:Q13393265 ;     # instance of basketball team
                    wdt:P118 wd:Q155223 ;      # league: NBA
                    rdfs:label ?teamLabel .
              
              OPTIONAL { ?coachStatement pq:P580 ?startTime . }
              OPTIONAL { ?coachStatement pq:P582 ?endTime . }
              OPTIONAL { ?coach wdt:P18 ?image . }
              OPTIONAL { ?coach wdt:P569 ?birthDate . }
              OPTIONAL { ?coach wdt:P27 ?nationality . 
                        ?nationality rdfs:label ?nationalityLabel .
                        FILTER(LANG(?nationalityLabel) = "en") }
              
              FILTER(LANG(?coachLabel) = "en")
              FILTER(LANG(?teamLabel) = "en")
              
              SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
            }
            ORDER BY ?coachLabel
            """

            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()

            coaches_dict = {}
            
            for result in results.bindings:
                coach_uri = result["coach"].value if "coach" in result else ""
                coach_id = coach_uri.split('/')[-1] if coach_uri else ""
                coach_name = result["coachLabel"].value if "coachLabel" in result else ""
                coach_image = result["image"].value if "image" in result else None
                birth_date = result["birthDate"].value if "birthDate" in result else ""
                nationality = result["nationalityLabel"].value if "nationalityLabel" in result else ""
                team_name = result["teamLabel"].value if "teamLabel" in result else ""
                start_time = result["startTime"].value if "startTime" in result else ""
                end_time = result["endTime"].value if "endTime" in result else ""
                
                # Group by coach to avoid duplicates and collect teams
                if coach_id not in coaches_dict:
                    coaches_dict[coach_id] = {
                        'coach_id': coach_id,
                        'name': coach_name,
                        'image': coach_image,
                        'birth_date': birth_date,
                        'nationality': nationality,
                        'teams': [],
                        'source': 'wikidata'
                    }
                
                # Add team information if not already present
                if team_name:
                    team_info = {
                        'team_name': team_name,
                        'start_year': start_time[:4] if start_time else None,
                        'end_year': end_time[:4] if end_time else None
                    }
                    
                    # Check if this team info is already added
                    existing_team = next((t for t in coaches_dict[coach_id]['teams'] 
                                        if t['team_name'] == team_name and 
                                           t['start_year'] == team_info['start_year']), None)
                    
                    if not existing_team:
                        coaches_dict[coach_id]['teams'].append(team_info)
            
            # Convert to list and sort
            coaches_list = list(coaches_dict.values())
            coaches_list.sort(key=lambda x: x['name'])
            
            return coaches_list
            
        except Exception as e:
            print(f"Error querying Wikidata for all NBA coaches: {e}")
            return []


# Instantiate the service
data_service = DataComplementationService()


def get_team_coaches(request):
    """
    API endpoint to get historical coaches for NBA teams
    """
    team_name = request.GET.get('team_name', '')
    
    if not team_name:
        return JsonResponse({
            "error": "team_name parameter is required"
        }, status=400)
    
    try:
        coaches = data_service.get_team_coaches_from_wikidata(team_name)
        
        return JsonResponse({
            "team_name": team_name,
            "coaches": coaches,
            "total_coaches": len(coaches)
        })
        
    except Exception as e:
        return JsonResponse({
            "error": f"Error retrieving coaches: {str(e)}"
        }, status=500)

def get_coach_info(request):
    """
    API endpoint to get detailed information about a basketball coach
    """
    coach_entity_id = request.GET.get('coach_entity_id', '')

    if not coach_entity_id:
        return JsonResponse({
            "error": "coach_entity_id parameter is required"
        }, status=400)

    try:
        coach_info = data_service.get_coach_info_from_wikidata(coach_entity_id)

        if not coach_info:
            return JsonResponse({
                "error": "Coach not found or no information available"
            }, status=404)

        return JsonResponse(coach_info)

    except Exception as e:
        return JsonResponse({
            "error": f"Error retrieving coach information: {str(e)}"
        }, status=500)


def get_player_awards(request):
    """
    API endpoint to get awards and achievements for NBA players
    """
    player_name = request.GET.get('player_name', '')
    
    if not player_name:
        return JsonResponse({
            "error": "player_name parameter is required"
        }, status=400)
    
    try:
        awards = data_service.get_player_awards_from_wikidata(player_name)
        
        return JsonResponse({
            "player_name": player_name,
            "awards": awards,
            "total_awards": len(awards)
        })
        
    except Exception as e:
        return JsonResponse({
            "error": f"Error retrieving awards: {str(e)}"
        }, status=500)


def get_arena_details(request):
    """
    API endpoint to get additional arena information
    """
    arena_name = request.GET.get('arena_name', '')
    
    if not arena_name:
        return JsonResponse({
            "error": "arena_name parameter is required"
        }, status=400)
    
    try:
        arena_info = data_service.get_arena_information_from_dbpedia(arena_name)
        
        return JsonResponse({
            "arena_name": arena_name,
            "arena_info": arena_info
        })
        
    except Exception as e:
        return JsonResponse({
            "error": f"Error retrieving arena information: {str(e)}"
        }, status=500)


def get_all_coaches(request):
    """
    API endpoint to get all NBA coaches from Wikidata
    """
    try:
        coaches = data_service.get_all_nba_coaches_from_wikidata()
        
        return JsonResponse({
            "coaches": coaches,
            "total_coaches": len(coaches),
            "source": "wikidata"
        })
        
    except Exception as e:
        return JsonResponse({
            "error": f"Error retrieving coaches: {str(e)}"
        }, status=500)
