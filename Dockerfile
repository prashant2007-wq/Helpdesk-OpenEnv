FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md openenv.yaml /app/
COPY src /app/src
COPY scripts /app/scripts
COPY app.py /app/app.py
COPY inference.py /app/inference.py

RUN pip install --upgrade pip && pip install -e .

EXPOSE 7860

CMD ["python", "app.py"]
 
