FROM python:3.12-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY agents/coder_agent/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "agents.coder_agent.main:app", "--host", "0.0.0.0", "--port", "8002"]