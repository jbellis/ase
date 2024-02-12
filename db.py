import os
import time

from astrapy.db import AstraDB

from util import hexdigest

# Initialize the client. The namespace parameter is optional if you use
# "default_keyspace".
_db = AstraDB(
    token=os.environ["ASTRA_DB_APPLICATION_TOKEN"],
    api_endpoint=os.environ["ASTRA_DB_API_ENDPOINT"],
    namespace="default_keyspace",
)

_embeddings = None
_files = None
def connect(collection_name):
    global _embeddings, _files
    _embeddings = _db.create_collection(collection_name + "_embeddings", dimension=768, metric="cosine")
    _files = _db.create_collection(collection_name + "_files")


def load_hashes():
    """Return the document associated with the given path, or None if not found."""
    return list(_files.paginated_find())


def delete(file_doc):
    _embeddings.delete_many({"file_id": file_doc['_id']})
    _files.delete_one(file_doc['_id'])


def insert(file_id, full_path, chunks, encoded_chunks):
    file_doc = {"path": full_path, "hash": hexdigest(full_path)}
    if file_id:
        file_doc["_id"] = file_id
    file_id = _files.upsert_one(file_doc)
    embeddings_docs = [{'file_id': file_id, 'chunk': chunk, '$vector': embedding}
                 for chunk, embedding in zip(chunks, encoded_chunks)]
    # call insert_many once per batch of 20 embeddings
    for i in range(0, len(embeddings_docs), 20):
        _embeddings.insert_many(embeddings_docs[i:i + 20])


def search(query_embedding, limit=10):
    return _embeddings.vector_find(query_embedding, limit=limit, fields={"path", "chunk"})
