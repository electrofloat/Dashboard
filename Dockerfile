FROM python:3.12-alpine

ENV PIP_ROOT_USER_ACTION=ignore \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install -r /app/requirements.txt

COPY LICENSE /app/
COPY dashboard/ /app/dashboard/

RUN adduser -D -H -u 1000 dashboard
USER dashboard

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD wget -q -O /dev/null http://127.0.0.1:5000/healthz || exit 1

WORKDIR /app

# gthread lets slow Authelia checks of one page load run without blocking every other request
CMD ["gunicorn", "dashboard:create_app()", "-b", "0.0.0.0:5000", "-w", "1", "-k", "gthread", "--threads", "8", "--no-control-socket"]
