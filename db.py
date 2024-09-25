import os

from astrapy.db import AstraDB, AstraDBCollection

from util import hexdigest

# set up api endpoint and secret token
_db = AstraDB(token=os.environ["ASTRA_DB_APPLICATION_TOKEN"],
              api_endpoint=os.environ["ASTRA_DB_API_ENDPOINT"],
              namespace="default_keyspace",)

_embeddings = None
_files = None


def init(collection_name):
    """
    Create the embeddings and files collections if they don't exist.
    """
    global _embeddings, _files
    print('Connecting to database for collection ' + collection_name)
    # get_collections is fast enough that I haven't bothered to optimize this further with local caching
    all_collections = set(_db.get_collections()['status']['collections'])

    embeddings_collection_name = collection_name + "_embeddings"
    if embeddings_collection_name in all_collections:
        _embeddings = AstraDBCollection(embeddings_collection_name, _db)
    else:
        _embeddings = _db.create_collection(embeddings_collection_name, dimension=768, metric="cosine",
                                            options={'indexing': {'deny': ['chunk']}})

    files_collection_name = collection_name + "_files"
    if files_collection_name in all_collections:
        _files = AstraDBCollection(files_collection_name, _db)
    else:
        _files = _db.create_collection(files_collection_name)


def load_hashes():
    """Return the document associated with the given path, or None if not found."""
    return list(_files.paginated_find())


def file_by_id(file_id):
    """Return the document with the given id.  Raises an exception if not found."""
    return _files.find_one({'_id': file_id})['data']['document']


def delete(file_id):
    """Delete the file and embeddings documents associated with the given file"""
    _embeddings.delete_many({"file_id": file_id})
    _files.delete_one(file_id)


def insert(file_id, full_path, chunks, encoded_chunks):
    """
    Insert the file and embeddings documents associated with the given file.
    If file_id is None, a new id is generated.
    """
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
    """Return the top `limit` chunks that are most similar to the given query embedding."""
    return _embeddings.vector_find(query_embedding, limit=limit, fields={"file_id", "chunk"})
