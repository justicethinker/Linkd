#!/bin/bash

# Start Celery workers for Phase 2 distributed processing
# 
# This script starts separate worker pools optimized for different task types:
# - Transcription worker: CPU-optimized (multiprocessing)
# - Enrichment worker: I/O-optimized (Gevent)
# - Monitoring: Flower for real-time task monitoring

set -e

REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
WORKER_COUNT=${WORKER_COUNT:-4}

echo "Starting Linkd Phase 2 Workers..."
echo "Redis: $REDIS_HOST:$REDIS_PORT"
echo "Worker Count: $WORKER_COUNT"

# Start transcription worker (cpu-bound, multiprocessing)
echo "[1/3] Starting Transcription Worker..."
celery -A src.celery_app worker \
    --queue transcription \
    --concurrency=$WORKER_COUNT \
    --pool=prefork \
    --loglevel=info \
    --hostname=transcription@%h \
    --logfile=logs/transcription.log &
TRANSCRIPTION_PID=$!
echo "Transcription worker started (PID: $TRANSCRIPTION_PID)"

# Start enrichment worker (i/o-bound, gevent)
echo "[2/3] Starting Enrichment Worker (Gevent)..."
celery -A src.celery_app worker \
    --queue enrichment \
    --concurrency=$((WORKER_COUNT * 4)) \
    --pool=gevent \
    --loglevel=info \
    --hostname=enrichment@%h \
    --logfile=logs/enrichment.log &
ENRICHMENT_PID=$!
echo "Enrichment worker started (PID: $ENRICHMENT_PID)"

# Start Flower monitoring
echo "[3/3] Starting Flower Monitoring (http://localhost:5555)..."
celery -A src.celery_app flower \
    --port=5555 \
    --logfile=logs/flower.log &
FLOWER_PID=$!
echo "Flower monitoring started (PID: $FLOWER_PID)"

# Trap signals to gracefully shut down
trap "kill $TRANSCRIPTION_PID $ENRICHMENT_PID $FLOWER_PID" EXIT

# Wait for all background processes
wait

echo "All workers stopped."
