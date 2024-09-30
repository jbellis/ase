import os
import time
from collections import deque

import google.generativeai as gemini
import requests

JINA_API_KEY = os.environ.get("JINA_API_KEY")
if not JINA_API_KEY:
    raise Exception('JINA_API_KEY environment variable not set')


class RateLimiter:
    def __init__(self, max_tokens, time_window):
        self.max_tokens = max_tokens
        self.time_window = time_window
        self.tokens = max_tokens
        self.start_time = time.time()
        self.last_refill = self.start_time
        self.requests = deque()
        self.total_requests = 0

    def wait(self, tokens):
        self._refill()
        while self.tokens < tokens:
            time.sleep(0.1)
            self._refill()
        self.tokens -= tokens
        self.requests.append((time.time(), tokens))
        self.total_requests += tokens

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * (self.max_tokens / self.time_window))
        self.last_refill = now
        while self.requests and now - self.requests[0][0] > self.time_window:
            _, tokens = self.requests.popleft()
            self.tokens = min(self.max_tokens, self.tokens + tokens)

    def status(self):
        now = time.time()
        elapsed = now - self.start_time
        rps = self.total_requests / elapsed
        return f"RateLimiter allowed {self.total_requests} requests in {elapsed}s = {rps:.2f} RPS"


rate_limiter = RateLimiter(50, 60) # 1000 tokens per minute with a buffer
def encode(inputs: list[str]) -> list[list[float]]:
    limited_inputs = [text[:30000] for text in inputs] # 8k tokens * 0.9 words/token * 4.7 bytes/word, conservatively
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

    rate_limiter.wait(1)
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except:
        print(rate_limiter.status())
        raise

    result = response.json()
    return [item['embedding'] for item in result['data']]
