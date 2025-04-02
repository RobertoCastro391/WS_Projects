# app/startup.py
import os
import requests
import time

GRAPHDB_BASE_URL = "http://localhost:7200"
REPO_ID = "NBA_G4"
USERNAME = "admin"
PASSWORD = "admin"

REPO_CONFIG_PATH = os.path.join('data', 'nba-config.ttl')
RDF_FILE_PATH = os.path.join('data', 'nba_triples.n3')

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

    if response.status_code in [200, 201, 204]:
        print("RDF data imported successfully.")
        return True
    else:
        print(f"RDF import failed: {response.status_code}, {response.text}")
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
            print("RDF data imported successfully.")
        else:
            print("RDF import failed.")