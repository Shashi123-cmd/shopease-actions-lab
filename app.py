import os
from flask import Flask, jsonify
import redis

app = Flask(__name__)

PRICES = {"laptop": 55000, "headphones": 2500, "keyboard": 1200}


def get_cache():
    return redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379,
                       socket_connect_timeout=2, decode_responses=True)


@app.route("/health")
def health():
    return jsonify(status="ok", service="shopease-api",
                   version=os.getenv("APP_VERSION", "dev"))


@app.route("/price/<item>")
def price(item):
    if item not in PRICES:
        return jsonify(error="unknown item"), 404
    return jsonify(item=item, price=PRICES[item], currency="INR")


@app.route("/visit")
def visit():
    try:
        return jsonify(visits=get_cache().incr("visits"))
    except redis.exceptions.RedisError:
        return jsonify(error="cache unavailable"), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

name: Shopease App CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-and-run:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Pull base image
        run: docker pull python:3.12-slim

      - name: Install dependencies
        run: |
          docker run --rm \
            -v $GITHUB_WORKSPACE:/app \
            -w /app \
            python:3.12-slim \
            bash -lc "pip install --no-cache-dir -r requirements.txt"

      - name: Copy application code
        run: |
          mkdir -p app
          cp -r . app/
          ls -la app

      - name: Expose port
        run: echo "App is configured to expose port 5000"

      - name: Run app.py
        run: |
          docker run -d --name shopease-app \
            -p 5000:5000 \
            -v $GITHUB_WORKSPACE:/app \
            -w /app \
            python:3.12-slim \
            bash -lc "pip install --no-cache-dir -r requirements.txt && python app.py"

      - name: Health check
        run: |
          sleep 5
          curl -f http://localhost:5000/health
