#!/bin/sh

REPO_ID="NBA"
GDB_URL="http://graphdb:7200"

echo "⏳ Aguardando GraphDB iniciar..."
until curl -s "$GDB_URL"; do
  sleep 3
done

echo "🚀 Verificando se o repositório já existe..."
if curl -s "$GDB_URL/rest/repositories/$REPO_ID" | grep -q "$REPO_ID"; then
  echo "✅ Repositório '$REPO_ID' já existe. Nada a fazer."
else
  echo "📦 Criando repositório '$REPO_ID'..."
  curl -X POST -H "Content-Type: multipart/form-data" \
    -F "config=@/repo-config.ttl" \
    "$GDB_URL/rest/repositories"

  echo "📥 Importando RDF para o repositório..."
  curl -X POST -H "Content-Type:application/x-turtle" \
    --data-binary "@/data.rdf.n3" \
    "$GDB_URL/repositories/$REPO_ID/statements"

  echo "✅ RDF importado com sucesso."
fi