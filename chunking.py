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


CHUNK_SIZE_LIMIT = 1000
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
