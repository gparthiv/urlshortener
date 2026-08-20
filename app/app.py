# This file connects all services and defines the Base62 encoder/decoder.

import os
import string
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, request, redirect, jsonify, render_template
import redis
import psycopg2

app = Flask(__name__)


# --------------------------------------------------
# Base62 configuration
# --------------------------------------------------

# 62 URL-safe characters:
# 0-9, a-z, A-Z
ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


# --------------------------------------------------
# Redis connection
# --------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL")

if REDIS_URL:
    cache = redis.from_url(
        REDIS_URL,
        decode_responses=True
    )
else:
    cache = redis.Redis(
        host=os.environ.get("REDIS_HOST"),
        port=int(os.environ.get("REDIS_PORT") or 6379),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,
    )


# --------------------------------------------------
# PostgreSQL connection
# --------------------------------------------------

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
    """Create the URLs table if it does not exist."""

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


# Initialize database when Flask/Gunicorn starts
init_db()


# --------------------------------------------------
# Base62 encoder / decoder
# --------------------------------------------------

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

        if char not in ALPHABET:
            raise ValueError("Invalid short code")

        num = num * 62 + ALPHABET.index(char)

    return num


# --------------------------------------------------
# Rate limiting
# --------------------------------------------------

def rate_limit(max_requests=10, window=60):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            client_ip = request.remote_addr

            key = f"rate_limit:{client_ip}"

            current = cache.get(key)

            if current and int(current) >= max_requests:
                return jsonify({
                    "error": "Rate limit exceeded. Try again later."
                }), 429

            pipe = cache.pipeline()

            pipe.incr(key)
            pipe.expire(key, window)

            pipe.execute()

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# --------------------------------------------------
# Frontend
# --------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --------------------------------------------------
# Create shortened URL
# --------------------------------------------------

@app.route("/shorten", methods=["POST"])
@rate_limit(max_requests=10, window=60)
def shorten_url():

    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({
            "error": "Missing url field"
        }), 400

    long_url = data["url"].strip()

    # Validate URL
    parsed = urlparse(long_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({
            "error": "Please enter a valid HTTP or HTTPS URL."
        }), 400

    # Store URL permanently in PostgreSQL
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO urls (long_url) VALUES (%s) RETURNING id",
        (long_url,)
    )

    url_id = cur.fetchone()[0]

    conn.commit()

    cur.close()
    conn.close()

    # Convert database ID into Base62 short code
    short_code = base62_encode(url_id)

    # Store mapping in Redis cache
    cache.set(short_code, long_url)

    # Build final shortened URL
    short_url = request.host_url + short_code

    return jsonify({
        "short_url": short_url,
        "short_code": short_code
    }), 201


# --------------------------------------------------
# Redirect shortened URL
# --------------------------------------------------

@app.route("/<short_code>")
def redirect_url(short_code):

    try:
        url_id = base62_decode(short_code)

    except ValueError:
        return jsonify({
            "error": "Invalid short URL"
        }), 400

    # First check Redis
    long_url = cache.get(short_code)

    if long_url:

        print("CACHE HIT", flush=True)

        return redirect(
            long_url,
            code=302
        )

    # Redis miss → query PostgreSQL
    print("CACHE MISS - querying database", flush=True)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT long_url FROM urls WHERE id = %s",
        (url_id,)
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    if not result:
        return jsonify({
            "error": "Short URL not found"
        }), 404

    long_url = result[0]

    # Put result into Redis for future requests
    cache.set(short_code, long_url)

    return redirect(
        long_url,
        code=302
    )


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.route("/health")
def health():
    """Simple endpoint to verify the server is running."""

    return jsonify({
        "status": "healthy"
    }), 200


# --------------------------------------------------
# Local development
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )