import redis
import os
import hashlib

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_client = redis.from_url(REDIS_URL)

def get_redirect_key(short_code):
    return f"redirect:{short_code}"

def get_link_key(short_code):
    return f"link:{short_code}"

def get_search_key(original_url):
    return f"search:{hashlib.md5(original_url.encode()).hexdigest()}"
