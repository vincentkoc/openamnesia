FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml setup.py README.md /app/
COPY amnesia /app/amnesia
COPY amnesia_daemon.py /app/

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "amnesia.api.server"]
