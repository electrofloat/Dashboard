FROM python:3.12-alpine

RUN mkdir -p /app/dashboard/static
RUN mkdir -p /app/dashboard/templates

COPY dashboard/auth.py dashboard/config.py dashboard/main.py dashboard/json.schema dashboard/__init__.py requirements.txt LICENSE /app/dashboard/

COPY dashboard/static/app.css dashboard/static/background.jpg dashboard/static/bulma.css dashboard/static/favicon.png /app/dashboard/static/

COPY dashboard/templates/base.html dashboard/templates/index.html dashboard/templates/color.html dashboard/templates/tile_fragment.html /app/dashboard/templates/

ENV PIP_ROOT_USER_ACTION=ignore

RUN python3 -m pip install --upgrade pip && python3 -m pip install --no-cache-dir -r /app/dashboard/requirements.txt

RUN python3 -m pip install gunicorn

EXPOSE 5000

WORKDIR /app

CMD ["gunicorn", "dashboard:create_app()", "-b", "0.0.0.0:5000", "-w", "1", "--no-control-socket"]
