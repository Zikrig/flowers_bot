#!/bin/bash
# Скрипт для пересборки Docker образа без кэша
docker-compose down
docker-compose build --no-cache
docker-compose up -d


