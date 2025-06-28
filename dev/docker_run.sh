#!/bin/bash

docker build -t dashboard:dev ../

docker-compose up
docker-compose down
