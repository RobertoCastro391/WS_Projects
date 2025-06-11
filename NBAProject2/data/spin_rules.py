from SPARQLWrapper import SPARQLWrapper, POST

PREFIXES = """
PREFIX nba: <http://example.org/nba/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

def run_sparql_update(query, endpoint_update):
    sparql = SPARQLWrapper(endpoint_update)
    sparql.setMethod(POST)
    sparql.setQuery(PREFIXES + query)
    sparql.query()

def rule_1_conference_from_division(endpoint_update):
    query = """
    INSERT {
        ?team nba:conference ?conference .
    }
    WHERE {
        ?team nba:division ?division .
        ?division nba:divisionConference ?conference .
        FILTER NOT EXISTS { ?team nba:conference ?conference }
    }
    """
    run_sparql_update(query, endpoint_update)

def rule_2_last_team_from_latest_participation(endpoint_update):
    query = """
    INSERT {
        ?player nba:lastTeam ?team .
    }
    WHERE {
        ?participation nba:player ?player .
        ?participation nba:team ?team .
        ?participation nba:season ?season .
        ?participation nba:seasonType nba:seasonType_1 .
        {
            SELECT ?player (MAX(?seasonLabel) AS ?maxSeason) WHERE {
                ?participation nba:player ?player .
                ?participation nba:season ?season .
                ?season nba:seasonLabel ?seasonLabel .
                ?participation nba:seasonType nba:seasonType_1 .
            } GROUP BY ?player
        }
        ?season nba:seasonLabel ?maxSeason .
        FILTER NOT EXISTS { ?player nba:lastTeam ?team }
    }
    """
    run_sparql_update(query, endpoint_update)

def rule_3_career_span(endpoint_update):
    query = """
    INSERT {
        ?player nba:careerStart ?firstSeason ;
                nba:careerEnd ?lastSeason .
    }
    WHERE {
        {
            SELECT ?player (MIN(?seasonLabel) AS ?firstSeason) (MAX(?seasonLabel) AS ?lastSeason) WHERE {
                ?participation nba:player ?player .
                ?participation nba:season ?season .
                ?season nba:seasonLabel ?seasonLabel .
                ?participation nba:seasonType nba:seasonType_1 .
            } GROUP BY ?player
        }
        FILTER NOT EXISTS {
            ?player nba:careerStart ?firstSeason ;
                    nba:careerEnd ?lastSeason .
        }
    }
    """
    run_sparql_update(query, endpoint_update)

def rule_4_draft_age(endpoint_update):
    query = """
    INSERT {
        ?player nba:draftAge ?age .
    }
    WHERE {
        ?player nba:birthdate ?birthdate .
        ?player nba:draftYear ?draftYearStr .
        BIND(xsd:integer(?draftYearStr) AS ?draftYearInt)
        BIND(?draftYearInt - YEAR(xsd:date(?birthdate)) AS ?age)
    }
    """
    run_sparql_update(query, endpoint_update)

def rule_5_draft_classmates(endpoint_update):
    query = """
    INSERT {
        ?player1 nba:draftedInSameYearAs ?player2 .
    }
    WHERE {
        ?player1 nba:draftYear ?year .
        ?player2 nba:draftYear ?year .
        FILTER(?player1 != ?player2)
        FILTER NOT EXISTS { ?player1 nba:draftedInSameYearAs ?player2 }
    }
    """
    run_sparql_update(query, endpoint_update)
