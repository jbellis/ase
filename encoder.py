import os

import google.generativeai as gemini

gemini_key = os.environ["GEMINI_KEY"]
if not gemini_key:
    raise Exception('GEMINI_KEY environment variable not set')
gemini.configure(api_key=gemini_key)

def encode(inputs: list[str]) -> list[list[float]]:
    model = "models/text-embedding-004"
    result = gemini.embed_content(model=model, content=inputs)
    return result['embedding']
