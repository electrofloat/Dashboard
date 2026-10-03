#!/bin/bash

if [ ! -f venv/pyvenv.cfg ]; then
  echo "Python venv does not exist!"
  exit 1
fi

source venv/bin/activate

pytest -p no:cacheprovider ../
