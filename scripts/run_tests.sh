#!/bin/bash

echo "Building Docker images..."
docker-compose build

echo "Running tests..."
docker-compose --profile testing run --rm test

echo "Tests completed!"