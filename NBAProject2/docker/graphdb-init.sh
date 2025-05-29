#!/bin/sh

REPO_ID="NBA_G4"
GDB_URL="http://graphdb:7200"

echo "Waiting GraphDB ..."
until curl -s "$GDB_URL"; do
  sleep 3
done

echo "Checking if the repository already exists..."
if curl -s "$GDB_URL/rest/repositories/$REPO_ID" | grep -q "$REPO_ID"; then
  echo "Repository '$REPO_ID' already exists."
else
  echo "Creating repository '$REPO_ID'..."
  curl -X POST -H "Content-Type: multipart/form-data" \
    -F "config=@/repo-config.ttl" \
    "$GDB_URL/rest/repositories"

  echo "Importing RDF file..."
  curl -X POST -H "Content-Type:application/x-turtle" \
    --data-binary "@/data.rdf.n3" \
    "$GDB_URL/repositories/$REPO_ID/statements"

  echo "RDF succefully imported."
fi