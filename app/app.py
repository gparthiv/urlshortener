# this file connects to all the services and 
# define and build the base62 encoder, decoder  

import os
import string
from functools import wraps

from flask import Flask, request, redirect, jsonify, render_template
import redis
import psycopg2

app = Flask(__name__)

# Define the 62 characters used for short codes (0-9, a-z, A-Z)
ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase

# Connect to Redis for fast lookups
REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    cache = redis.from_url(REDIS_URL, decode_responses=True)
else:
    cache = redis.Redis(
        host=os.environ.get("REDIS_HOST"),
        port=int(os.environ.get("REDIS_PORT") or 6379),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,
    )

# Connect to PostgreSQL for permanent storage
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """Connect to PostgreSQL for permanent storage."""
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            long_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


init_db()  # runs once when the module is imported (i.e. when gunicorn/flask starts)


# we take 0-9 , a-b , A-B total 62 char only as it is URL safe strings (no special symbols etc)
def base62_encode(num):
    """Convert a database ID into a short alphanumeric string."""
    if num == 0:
        return ALPHABET[0]
    result = []
    while num > 0:
        num, remainder = divmod(num, 62)
        result.append(ALPHABET[remainder])
    return "".join(reversed(result))


def base62_decode(code):
    """Convert a short code back into the original database ID."""
    num = 0
    for char in code:
        num = num * 62 + ALPHABET.index(char)
    return num

def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the client's IP address
            client_ip = request.remote_addr
            # Create a unique Redis key for this IP
            key = f"rate_limit:{client_ip}"
            # Check current request count
            current = cache.get(key)
            if current and int(current) >= max_requests:
                return jsonify({"error": "Rate limit exceeded. Try again later."}), 429
            # Increment counter and set expiration atomically
            pipe = cache.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# connect index.html ui to flask
@app.route("/")
def index():
    return render_template("index.html")

# build the endpoint /shorten 
@app.route("/shorten", methods=["POST"])
@rate_limit(max_requests=10, window=60)
def shorten_url():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing url field"}), 400

    long_url = data["url"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO urls (long_url) VALUES (%s) RETURNING id", (long_url,))
    url_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    short_code = base62_encode(url_id)
    cache.set(short_code, long_url)

    short_url = request.host_url + short_code   
    return jsonify({
        "short_url": short_url,
        "short_code": short_code
    }), 201

@app.route("/<short_code>")
def redirect_url(short_code):
    long_url = cache.get(short_code)

    if long_url:
        print("CACHE HIT", flush=True)
        return redirect(long_url, code=302)

    print("CACHE MISS - querying database", flush=True)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT long_url FROM urls WHERE id = %s", (base62_decode(short_code),))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if not result:
        return jsonify({"error": "Short URL not found"}), 404

    long_url = result[0]
    cache.set(short_code, long_url)

    return redirect(long_url, code=302)


@app.route("/health")
def health():
    """Simple endpoint to verify the server is running."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )