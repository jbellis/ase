import os
import time
from collections import deque

import google.generativeai as gemini

gemini_key = os.environ["GEMINI_KEY"]
if not gemini_key:
    raise Exception('GEMINI_KEY environment variable not set')
gemini.configure(api_key=gemini_key)

class RateLimiter:
    def __init__(self, max_tokens, time_window):
        self.max_tokens = max_tokens
        self.time_window = time_window
        self.tokens = max_tokens
        self.last_refill = time.time()
        self.requests = deque()

    def wait(self, tokens):
        self._refill()
        while self.tokens < tokens:
            time.sleep(0.1)
            self._refill()
        self.tokens -= tokens
        self.requests.append((time.time(), tokens))

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * (self.max_tokens / self.time_window))
        self.last_refill = now
        while self.requests and now - self.requests[0][0] > self.time_window:
            _, tokens = self.requests.popleft()
            self.tokens = min(self.max_tokens, self.tokens + tokens)

rate_limiter = RateLimiter(980, 60) # 1000 tokens per minute with a buffer

def encode(inputs: list[str]) -> list[list[float]]:
    rate_limiter.wait(len(inputs))
    model = "models/text-embedding-004"
    result = gemini.embed_content(model=model, content=inputs)
    return result['embedding']
