#!/bin/bash

docker buildx build -t dashboard:dev ../

docker-compose up
docker-compose down
