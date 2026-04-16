FROM python:3.12-slim

# Install system dependencies (git for gitpython and PyGithub)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first to leverage Docker cache
COPY agents/tester_agent/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

ENV PYTHONPATH=/app

# Expose the API port that the application runs on
EXPOSE 8003

# Command to run the application
CMD ["uvicorn", "agents.tester_agent.main:app", "--host", "0.0.0.0", "--port", "8003"]