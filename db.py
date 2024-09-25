import os
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric

from util import hexdigest

# set up api endpoint and secret token
_client = DataAPIClient(token=os.environ["ASTRA_DB_TOKEN"])
_db = _client.get_database(os.environ["ASTRA_DB_ID"])

_embeddings = None
_files = None


def init(collection_name):
    """
    Create the embeddings and files collections if they don't exist.
    """
    global _embeddings, _files
    print('Connecting to database for collection ' + collection_name)
    
    embeddings_collection_name = collection_name + "_embeddings"
    files_collection_name = collection_name + "_files"
    
    collections = set(c.name for c in _db.list_collections())

    if embeddings_collection_name in collections:
        _embeddings = _db[embeddings_collection_name]
    else:
        _embeddings = _db.create_collection(embeddings_collection_name,
                                            indexing={'deny': ['chunk']},
                                            dimension=768,
                                            metric=VectorMetric.COSINE)

    if files_collection_name in collections:
        _files = _db[files_collection_name]
    else:
        _files = _db.create_collection(files_collection_name)


def hashes_cursor():
    """Return all documents in the files collection."""
    return _files.find({})


def file_by_id(file_id):
    """Return the document with the given id. Raises an exception if not found."""
    return _files.find_one({'_id': file_id})


def delete(file_id):
    """Delete the file and embeddings documents associated with the given file"""
    _embeddings.delete_many({"file_id": file_id})
    _files.delete_one({"_id": file_id})


def insert(file_id, full_path, chunks, encoded_chunks):
    """
    Insert the file and embeddings documents associated with the given file.
    If file_id is None, a new id is generated.
    """
    file_doc = {"path": full_path, "hash": hexdigest(full_path)}
    if file_id:
        file_doc["_id"] = file_id
    result = _files.insert_one(file_doc)
    file_id = result.inserted_id
    
    embeddings_docs = [{'file_id': file_id, 'chunk': chunk, '$vector': embedding}
                       for chunk, embedding in zip(chunks, encoded_chunks)]
    # call insert_many once per batch of 20 embeddings
    for i in range(0, len(embeddings_docs), 20):
        _embeddings.insert_many(embeddings_docs[i:i + 20])


def search(query_embedding, limit):
    """Return the top `limit` chunks that are most similar to the given query embedding."""
    return _embeddings.find(
        {},
        sort={"$vector": query_embedding},
        limit=limit,
        projection={"file_id": 1, "chunk": 1}
    )

def get_chunks_by_file_id(file_id):
    """Return all chunks associated with the given file_id."""
    return list(_embeddings.find({"file_id": file_id}, projection={"chunk": 1, "_id": 0}))
