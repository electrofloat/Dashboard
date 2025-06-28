#!/bin/bash

if [ ! -f venv/pyvenv.cfg ]; then
  python3 -m venv venv
  source venv/bin/activate
  #python3 -c 'import sys; print(sys.prefix != sys.base_prefix)'
  python3 -m pip install -r ../requirements.txt
else
  source venv/bin/activate
fi

FLASK_APP=../dashboard FLASK_DEBUG=1 flask run
