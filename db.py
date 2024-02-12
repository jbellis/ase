import os

from astrapy.db import AstraDB

# Initialize the client. The namespace parameter is optional if you use
# "default_keyspace".
_db = AstraDB(
    token=os.environ["ASTRA_DB_APPLICATION_TOKEN"],
    api_endpoint=os.environ["ASTRA_DB_API_ENDPOINT"],
    namespace="default_keyspace",
)


_collection = _db.create_collection("vector_test", dimension=768, metric="cosine")


def insert_embeddings(full_path, chunks, encoded_chunks):
    documents = [{'path': full_path, 'chunk': chunk, '$vector': embedding}
                 for chunk, embedding in zip(chunks, encoded_chunks)]
    # call insert_many once per batch of 20 documents
    for i in range(0, len(documents), 20):
        _collection.insert_many(documents[i:i + 20])

def search(query_embedding, limit=10):
    return _collection.vector_find(query_embedding, limit=limit, fields={"path", "chunk"})
