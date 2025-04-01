# NBA Semantic Web Project

This project is a semantic web application that represents NBA data using RDF and SPARQL. It uses:
- **Django** for the web interface
- **GraphDB** for the RDF triplestore

The system automatically creates a GraphDB repository and loads RDF data when first started.

##  Project Structure
```
NBAProject/
├── app/                   # Django application code
├── data/
|   ├── datasets           # Folder with the original dataset in .csv
|   ├── scripts            # Folder with Python scripts used to extract data and to transfom it to rdf .n3 format          
│   ├── nba_triples.n3     # Main RDF triples file (in Turtle/N3 format)
│   └── nba-config.ttl     # GraphDB repository configuration (Turtle format)
├── docker/
│   └── graphdb-init.sh    # Shell script that creats a repository and load rdf .n3 data, when running the application via docker
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # Dockerfile for Django container
├── manage.py              # Django entry point
├── requirements.txt       # Python dependencies
```

## How to Run the Project

There is currently two ways of running the project:
1. Running manually
2. Using docker

### Running Manually
#### Prerequisites
- Have the GraphDB program running.
- Create a Virtual Environment

When running the project manually, you'll need to:

#### Create a Virtual Environment
First, create and activate a Python virtual environment (make sure you are on `../NBAProject` folder):
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
- When the last command is made the all will be configured in GraphDB.
- The application uses `app/startup.py` to interact with GraphDB
- The startup script performs several key functions:
  - Waits for GraphDB to be accessible
  - Checks if the NBA_G4 repository already exists
  - Creates the repository if it doesn't exist using the configuration in `data/nba-config.ttl`
  - Loads the RDF data from `data/nba_triples.n3` into the repository
  - Provides status updates throughout the process

- The Django `apps.py` file triggers this setup automatically when the application starts in development mode
- It also creates an admin user if one doesn't exist

### Using Docker
### Prerequisites
- Docker and Docker Compose installed on your machine

### Run the full system:
From the **root of the project** (where `docker-compose.yml` is located), run:

```bash
docker compose up --build
```

This will:
- Build the Django application container
- Start GraphDB on port 7200
- Create the GraphDB repository named NBA_G4
- Load RDF data (nba_triples.n3) into that repository
- Start the Django app on port 8000

## Access the Services

- Django App: http://localhost:8000
- GraphDB UI: http://localhost:7200

From the GraphDB interface, you can explore the repository, run SPARQL queries, and inspect the imported RDF data.

---
Work done by:
- Roberto Rolão de Castro - 107133
- Tiago Caridade Gomes - 108307
- Sara Figueiredo Almeida - 108796
- Joaquim Vertentes Rosa - 1090