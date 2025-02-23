import google.generativeai as gemini
from pyrate_limiter import Duration, Rate, Limiter

# Create a limiter with a rate of 59 requests per 60 seconds
limiter = Limiter(Rate(59, Duration.MINUTE))

def encode(inputs: list[str]) -> list[list[float]]:
    limiter.try_acquire('encode', len(inputs))

    # write the request to a file for debugging
    with open('/tmp/request.json', 'w') as f:
        import json
        f.write(json.dumps(inputs, indent=2))

    model = "models/text-embedding-004"
    result = gemini.embed_content(model=model, content=inputs)
    return result['embedding']
