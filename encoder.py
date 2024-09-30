import os
import time
from collections import deque

import google.generativeai as gemini
import requests

JINA_API_KEY = os.environ.get("JINA_API_KEY")
if not JINA_API_KEY:
    raise Exception('JINA_API_KEY environment variable not set')


class RateLimiter:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.total_requests = 0

    def wait(self):
        now = time.time()
        
        # Remove old requests
        while self.requests and now - self.requests[0] > self.time_window:
            self.requests.popleft()
        
        # If at capacity, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] + self.time_window - now
            time.sleep(max(0, sleep_time))
        
        # Add current request
        self.requests.append(time.time())
        self.total_requests += 1

    def status(self):
        now = time.time()
        elapsed = now - self.requests[0] if self.requests else 0
        rps = len(self.requests) / self.time_window
        return f"RateLimiter allowed {self.total_requests} requests in {elapsed:.2f}s = {rps:.2f} RPS"


rate_limiter = RateLimiter(50, 60)  # 50 requests per 60 seconds
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

    rate_limiter.wait()
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except:
        print(rate_limiter.status())
        raise

    result = response.json()
    return [item['embedding'] for item in result['data']]
