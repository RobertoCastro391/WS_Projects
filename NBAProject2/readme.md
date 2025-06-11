# NBA Semantic Web Project

This project is a semantic web application that represents NBA data using RDF and SPARQL. It uses:
- **Django** for the web interface
- **GraphDB** for the RDF triplestore

The system automatically creates a GraphDB repository and loads the facts and the ontology to it when it first starts.

##  Project Structure
```
NBAProject/
├── app/                        # Django application code
├── data/                  
|   ├── datasets                # Folder with the original dataset in .csv
|   ├── scripts                 # Folder with Python scripts used to extract data and to transfom it to rdf .n3 format 
|   ├── facts.n3                # File with pure facts (triples), without the ontology
|   ├── nba_ontology_facts.n3   # Integration of facts with ontology. Combined file for validation in Protégé and for testing inferences
|   ├── nba_spin__rules.ttl     # SPIN rules written in SPARQL, applied to data to infer new relationships and properties
│   ├── nba_triples.n3          # Main RDF triples file (in Turtle/N3 format)
│   ├── nba-config.ttl          # GraphDB repository configuration (Turtle format)
|   └── spin_rules.py           # Python module with SPIN rules implemented in SPARQL (INSERT/WHERE), applicable via SPARQLWrapper
|
├── manage.py                   # Django entry point
├── requirements.txt            # Python dependencies
```

## How to Run the Project

#### Prerequisites
- Have the GraphDB program running. 
- Create a Virtual Environment

When running the project, you'll need to:

#### Create a Virtual Environment
First, create and activate a Python virtual environment (make sure you are on `../NBAProject2` folder):
```bash
# Create virtual environment
python3 -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Run the Aplication

```bash
python manage.py runserver
```

#### Setup Process
- When the last command is made all will be configured in GraphDB.
- The application uses `app/startup.py` to interact with GraphDB
- The startup script performs several key functions:
  - Waits for GraphDB to be accessible
  - Checks if the NBA_G4 repository already exists
  - Creates the repository if it doesn't exist using the configuration in `data/nba-config.ttl`
  - Loads the facts and ontology from `data/facts.n3` and `data/nba_ontology.n3` into the repository
  - Provides status updates throughout the process

- The Django `apps.py` file triggers this setup automatically when the application starts in development mode
- It also creates an admin user if one doesn't exist

## Access the Services

- Django App: http://localhost:8000
- GraphDB UI: http://localhost:7200

From the GraphDB interface, you can explore the repository, run SPARQL queries, and inspect the imported RDF data.

## Admin Access

- Username: `NBAAdmin`
- Password: `adminpass123`

---
Work done by:
- Roberto Rolão de Castro - 107133
- Tiago Caridade Gomes - 108307
- Sara Figueiredo Almeida - 108796
- Joaquim Vertentes Rosa - 109089