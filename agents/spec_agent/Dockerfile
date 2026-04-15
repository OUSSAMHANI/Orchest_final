# agents/spec_agent/Dockerfile
FROM spec-agent-base:latest

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "agents.spec_agent.main:app", "--host", "0.0.0.0", "--port", "8001"]