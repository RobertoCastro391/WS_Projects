# app/startup.py
import os
import requests
import time
import django
from django.conf import settings

# Import the SPIN rules functions
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.spin_rules import rule_1_conference_from_division, rule_2_last_team_from_latest_participation

endpoint_update = settings.SPARQL_ENDPOINT_UPDATE

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NBAProject.settings')
    django.setup()

GRAPHDB_BASE_URL = "http://localhost:7200"
REPO_ID = "NBA_G4"
USERNAME = "admin"
PASSWORD = "admin"

REPO_CONFIG_PATH = os.path.join('data', 'nba-config.ttl')
RDF_FILE_PATH = os.path.join('data', 'facts.n3')
ONTOLOGY_FILE_PATH = os.path.join('data', 'nba_ontology.n3')

def wait_for_graphdb():
    print("Waiting for GraphDB to start...")
    while True:
        try:
            response = requests.get(f"{GRAPHDB_BASE_URL}/rest/repositories")
            if response.status_code == 200:
                print("GraphDB is running.")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(3)

def repo_exists():
    response = requests.get(
        f"{GRAPHDB_BASE_URL}/rest/repositories/{REPO_ID}",
        auth=(USERNAME, PASSWORD)
    )
    return response.status_code == 200

def create_repo():
    print(f"Creating repository '{REPO_ID}'...")
    with open(REPO_CONFIG_PATH, 'rb') as config_file:
        files = {'config': ('repo-config.ttl', config_file, 'application/x-turtle')}
        response = requests.post(
            f"{GRAPHDB_BASE_URL}/rest/repositories",
            files=files,
            auth=(USERNAME, PASSWORD)
        )
    return response.status_code in [200, 201, 204]

def load_rdf():
    print("Importing RDF data...")
    with open(RDF_FILE_PATH, 'rb') as rdf_file:
        headers = {'Content-Type': 'application/x-turtle'}
        response = requests.post(
            f"{GRAPHDB_BASE_URL}/repositories/{REPO_ID}/statements",
            data=rdf_file,
            headers=headers,
            auth=(USERNAME, PASSWORD)
        )
    print("Importing ontology...")
    with open(ONTOLOGY_FILE_PATH, 'rb') as ontology_file:
        headers2 = {'Content-Type': 'application/x-turtle'}
        response2 = requests.post(
            f"{GRAPHDB_BASE_URL}/repositories/{REPO_ID}/statements",
            data=ontology_file,
            headers=headers2,
            auth=(USERNAME, PASSWORD)
        )

    if response.status_code and response2.status_code in [200, 201, 204]:
        print("RDF and ontology data imported successfully.")
        return True
    else:
        print(f"RDF or ontology import failed: {response.status_code}, {response.text} / {response2.status_code}, {response2.text}")
        return False


def load_spin_rules():
    """Load and execute SPARQL SPIN rules to infer new data."""
    try:
        print("Loading SPIN rules...")
        
        # Execute Rule 1: Infer team conferences from divisions
        print("Executing Rule 1: Conference from Division...")
        rule_1_conference_from_division(endpoint_update)
        print("Rule 1 completed successfully.")
        
        # Execute Rule 2: Infer player's last team from latest participation
        print("Executing Rule 2: Last Team from Latest Participation...")
        rule_2_last_team_from_latest_participation(endpoint_update)
        print("Rule 2 completed successfully.")
        
        print("SPIN rules loaded and executed successfully.")
        return True
        
    except Exception as e:
        print(f"Error loading SPIN rules: {str(e)}")
        return False

def setup_graphdb():
    
    wait_for_graphdb()

    if repo_exists():
        print(f"Repository '{REPO_ID}' already exists.")
    else:
        if create_repo():
            print(f"Repository '{REPO_ID}' created successfully.")
            time.sleep(5)
        else:
            print("Error: creating repository creation failed.")
            return
    
        if load_rdf():
            print("RDF and ontology data imported successfully.")
        else:
            print("RDF or ontology import failed.")

        if load_spin_rules():
            print("SPIN rules loaded successfully.")
        else:
            print("Error loading SPIN rules.")