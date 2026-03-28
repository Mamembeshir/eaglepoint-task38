#!/usr/bin/env bash

# The test service is profile-gated in docker-compose.yml.
docker compose --profile test run --rm test
