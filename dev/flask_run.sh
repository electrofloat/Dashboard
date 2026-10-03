#!/bin/bash

if [ ! -f venv/pyvenv.cfg ]; then
  python3 -m venv venv
  source venv/bin/activate
  #python3 -c 'import sys; print(sys.prefix != sys.base_prefix)'
  python3 -m pip install -r ../requirements-dev.txt
else
  source venv/bin/activate
fi

# DASHBOARD_DEV_FAKE_AUTH logs everyone in as 'testuser' and skips Authelia
DASHBOARD_USER_DATA=. DASHBOARD_DEV_FAKE_AUTH=1 FLASK_APP=../dashboard FLASK_DEBUG=1 flask run
