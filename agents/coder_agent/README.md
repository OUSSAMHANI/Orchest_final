# Coder Agent

The **Coder Agent** is responsible for generating and modifying code based on specifications and task descriptions.

## Running Independently

You can run the Coder Agent in two modes:

### 1. Manual Test Script (Recommended for Debugging)
A dedicated script allows you to run the agent logic directly from your terminal without starting the full orchestration system.

**Command:**
```powershell
python scripts/test_coder.py --spec "Your task here" --workspace "workspace/test_coder"
```
**Exemple of a command:**
```powershell
python scripts/test_coder.py --spec "Create a simple hello_world.py file that prints 'Hello World'" --workspace "workspace/test_coder"
```

**Options:**
- `--spec`: The code generation task description.
- `--workspace`: The directory where the agent will perform operations (relative to project root).
- `--model`: Specify an LLM model (e.g., `groq/llama-3.3-70b-versatile` or `google_genai/gemma-4-31b-it`).

### 2. FastAPI Server
Run the agent as a standalone API server.

**Command:**
```powershell
uvicorn agents.coder_agent.main:app --host 0.0.0.0 --port 8002
```
The agent will be available at `http://localhost:8002`.

## Configuration
Ensure your environment variables are set in `agents/coder_agent/.env`. Key variables:
- `GOOGLE_API_KEY`: Required for Google models.
- `GROQ_API_KEY`: Required for Groq models.
- `LLM_MODEL`: Default model to use.
