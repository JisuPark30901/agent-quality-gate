FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=YES

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY agent.py tools.py test_agent.py pytest.ini ./
COPY docs ./docs

# GOOGLE_API_KEY comes from `docker run --env-file .env`. Pass extra pytest
# args after the image name, e.g. `-m core`.
ENTRYPOINT ["deepeval", "test", "run", "test_agent.py"]
