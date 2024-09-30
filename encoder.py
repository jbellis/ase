import os

import requests
from ratelimit import limits, sleep_and_retry


JINA_API_KEY = os.environ.get("JINA_API_KEY")
if not JINA_API_KEY:
    raise Exception('JINA_API_KEY environment variable not set')


@sleep_and_retry
@limits(calls=59, period=60)
def encode(inputs: list[str]) -> list[list[float]]:
    # by experiment this seems to be the approximate upper limit
    # (TODO: use an actual tokenizer instead: the limit for "normal" tokens is around 20k,
    # but we have to use a lower amount because of pathological cases like Cassandra's StandardTokenizerImpl)
    limited_inputs = [text[:10000] for text in inputs]
    url = 'https://api.jina.ai/v1/embeddings'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JINA_API_KEY}"
    }
    data = {
        "model": "jina-embeddings-v2-base-code",
        "normalized": True,
        "embedding_type": "float",
        "input": limited_inputs
    }

    # write the request to a file for debugging
    with open('/tmp/request.json', 'w') as f:
        import json
        f.write(json.dumps(data, indent=2))

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raise an exception for HTTP errors

    result = response.json()
    return [item['embedding'] for item in result['data']]
