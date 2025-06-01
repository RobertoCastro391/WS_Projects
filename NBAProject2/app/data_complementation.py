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
            
            SELECT DISTINCT ?coach ?coachLabel ?teamLabel WHERE {{
                ?team wdt:P31 wd:Q13393265 ;  # instance of basketball team
                    wdt:P118 wd:Q155223 ;    # league: National Basketball Association
                    rdfs:label ?teamLabel .
                
                ?coach wdt:P106 wd:Q5137571 ;  # occupation: basketball coach
                       wdt:P54 ?team ;         # member of sports team
                       rdfs:label ?coachLabel .
                
                FILTER(LANG(?teamLabel) = "en")
                FILTER(LANG(?coachLabel) = "en") 
                FILTER(CONTAINS(LCASE(?teamLabel), LCASE("{clean_name}")))
                
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            LIMIT 20
            """

            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()

            coaches = []
            for result in results.bindings:
                coach_data = {
                    "coach_id": result.get("coach", {}).get("value", "").split("/")[-1],
                    "name": result.get("coachLabel", {}).get("value", ""),
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
                    wd:{coach_entity_id} wdt:P54 ?team .
                    OPTIONAL {{ wd:{coach_entity_id} p:P54 ?teamStatement .
                               ?teamStatement ps:P54 ?team ;
                                              pq:P2031 ?start ;
                                              pq:P2032 ?end .
                    }}
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
                coach_info["name"] = result.get("coachLabel", {}).get("value", coach_info["name"])
                coach_info["date_of_birth"] = result.get("dob", {}).get("value", coach_info["date_of_birth"])
                coach_info["place_of_birth"] = result.get("pobLabel", {}).get("value", coach_info["place_of_birth"])
                coach_info["gender"] = result.get("genderLabel", {}).get("value", coach_info["gender"])
                coach_info["citizenship"] = result.get("citizenshipLabel", {}).get("value", coach_info["citizenship"])
                coach_info["native_language"] = result.get("languageLabel", {}).get("value",
                                                                                    coach_info["native_language"])
                coach_info["position"] = result.get("positionLabel", {}).get("value", coach_info["position"])
                coach_info["image"] = result.get("image", {}).get("value", coach_info["image"])

                if "schoolLabel" in result:
                    coach_info["educated_at"].add(result["schoolLabel"]["value"])
                if "trainerLabel" in result:
                    coach_info["trained_by"].add(result["trainerLabel"]["value"])

                # Add teams with optional period
                if "teamLabel" in result:
                    team = {
                        "name": result["teamLabel"]["value"],
                        "start": result.get("start", {}).get("value", ""),
                        "end": result.get("end", {}).get("value", "")
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
            query = f"""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?player ?playerLabel ?award ?awardLabel WHERE {{
                ?player wdt:P106 wd:Q3665646 ;      # occupation: basketball player
                        wdt:P118 wd:Q5372 ;         # league: NBA
                        rdfs:label ?playerLabel ;
                        wdt:P166 ?award .           # award received
                
                ?award rdfs:label ?awardLabel .
                
                FILTER(LANG(?playerLabel) = "en")
                FILTER(LANG(?awardLabel) = "en")
                FILTER(CONTAINS(LCASE(?playerLabel), LCASE("{player_name}")))
                
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            LIMIT 15
            """
            
            self.wikidata_sparql.setQuery(query)
            results = self.wikidata_sparql.query()
            
            awards = []
            for result in results.bindings:
                award_data = {
                    "player": result.get("playerLabel", {}).get("value", ""),
                    "award": result.get("awardLabel", {}).get("value", ""),
                    "award_link": result.get("award", {}).get("value", ""),
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
            clean_name = arena_name.replace(" Arena", "").replace(" Center", "").strip()

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
            LIMIT 20
            """

            self.dbpedia_sparql.setQuery(query)
            results = self.dbpedia_sparql.query()

            arena_info = {}
            architects = []

            for result in results.bindings:
                # Build basic arena info (only once)
                if not arena_info:
                    arena_info = {
                        "name": result.get("label", {}).get("value", ""),
                        "construction_cost": result.get("constructionCost", {}).get("value", ""),
                        "opening_date": result.get("openingDate", {}).get("value", ""),
                        "building_start_date": result.get("buildingStartDate", {}).get("value", ""),
                        "source": "dbpedia"
                    }

                # Collect architect information
                architect_uri = result.get("architect", {}).get("value", "")
                architect_name = result.get("architectName", {}).get("value", "")
                architect_thumbnail = result.get("architectThumbnail", {}).get("value", "")

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
