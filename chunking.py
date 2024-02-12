import os
from typing import List


def chunkify_code(code: str, language: str) -> List[str]:
    """
    Splits code into semantically meaningful chunks based on simple heuristics.
    """
    chunks = []
    if language in {'C', 'C++', 'Java', 'JavaScript', 'Rust'}:
        # Simple heuristic for languages using braces
        chunks = [chunk + '}' for chunk in code.split('}')]
    elif language == 'Python':
        chunks = [chunk + ':' for chunk in code.split(':')]
    else:
        # Fallback for unrecognized languages, split by empty lines as a very basic heuristic.
        chunks = code.split('\n\n')

    return chunks


# CHUNK_SIZE_LIMIT = 1000
# blows up with
# astrapy.api.APIRequestError: {"errors":[{"message":"Document size limitation violated: indexed String value length (9974 bytes) exceeds maximum allowed (8000 bytes)","errorCode":"SHRED_DOC_LIMIT_VIOLATION"}]}
# not sure how 1k turns into 9k+ but let's try 800
CHUNK_SIZE_LIMIT = 800
def combine_chunks(chunks: List[str]) -> List[str]:
    """
    Combines consecutive chunks up to our size limit.
    """
    combined_chunks = []
    for chunk in chunks:
        if combined_chunks and len(combined_chunks[-1] + chunk) < CHUNK_SIZE_LIMIT:
            combined_chunks[-1] += chunk
        else:
            combined_chunks.append(chunk)
    return combined_chunks
