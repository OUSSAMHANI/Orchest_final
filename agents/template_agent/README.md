# Template Agent (Agent Generator)

A neutral blueprint for scaffolding new agents in the Orchest multi-agent system.
It ships with a FastAPI server, LangGraph node logic, and a resource-based prompt system.

## Quick Start: Generate a New Agent

Run the interactive generator from anywhere in the project:

```bash
python agents/template_agent/generate.py
```

The CLI will walk you through four steps:

| Step | What you provide |
|------|-----------------|
| **1 — Name** | `snake_case` agent name, e.g. `security_agent` |
| **2 — Type** | **Executor** (`uses_tests=True`) or **Thinker** (`uses_tests=False`) |
| **3 — Tools** | Numbered checklist from `data/tools.py` |
| **4 — Prompts** | Multiline system & human prompts — type `:wq!` on an empty line to finish |

### Agent Types

- **Executor** — participates in the test-run nudge loop (`uses_tests=True`). Use for agents that execute code, run sandboxes, or perform actions with side-effects.
- **Thinker** — pure reasoning / generation (`uses_tests=False`). Use for spec writers, reviewers, code generators.

### After generation

The new agent lives at `agents/<your_agent_name>/` and is **immediately runnable**:

```bash
uvicorn agents.<your_agent_name>.main:app --reload
```

All class names, import paths, FastAPI metadata, and prompt directories are
automatically renamed to match your agent name.


# This template agent is a placeholder for a new agent.

Follow the next steps to create any new agent:
1. Copy this folder and rename it to the name of your agent.
2. Update the `agent_name` variable in the `main.py` file.
3. Update the `state` in the `main.py` file to match the new agent's needs.
4. Import the tools that the agent will need to use in the tools folder.
5. Extend the `BaseAgent` class in the `agents` folder to add the new agent's logic. *(Example: `Executor_agent`)*
5.1. Override the `get_tools` method to return the tools that the agent will need to use.
5.2. Override the `run` method to add the new agent's logic.
5.3. Override the `build_context` method to add the new agent's logic if needed.
5.4. Override the `build_report` method to add the new agent's logic if needed.
6. Paste the prompts in the `resources/agents/<agent_name>/` folder. *(Example: `resources/agents/executor_agent/`)*
6.1. Human prompt: `human.yml`
```
verbose: |
  Write agent prompt here
  
compact: |
  Write agent prompt here
```
6.2. System prompt: `system.yml`
```
verbose: |
  Write agent prompt here
  
compact: |
  Write agent prompt here
```
6.3. Nudge prompt: `nudge.yml`
```
verbose: |
  Write agent prompt here
  
compact: |
  Write agent prompt here
```
6.4. Suffixes prompt: `suffixes.yml`
```
verbose: |
  Write agent prompt here
  
compact: |
  Write agent prompt here
```
---
*PS:* You can define more prompts in the `resources/agents/<agent_name>/` folder. *(Example: `resources/agents/executor_agent/tools.yml`)* 
    For that, create a new file in the `resources/agents/<agent_name>/` folder and add a method for it in this format : 
```
    @lru_cache(maxsize=None)
    def method_name() -> dict[str, dict]:
        path = AGENTS / "agent_name" / "prompts" / "file_name.yaml"
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
```
---

7. Modify the state file to match requirements.
8. Add .env to the project with env variables.

## Folder Structure

- `main.py`: Entry point for the FastAPI server.
- `agents/`: Contains the LangGraph node and core logic.
- `resources/`: Prompts and language-specific configurations.
- `llm/`: LLM configuration, tool binders, and repair logic.
- `tools/`: Reusable tools (files, folders, docker, etc.).
- `utils/`: Helper utilities (language detection, etc.).
- `generate.py`: Automation script to clone this template.

## Running the Agent

Once generated, you can run the agent locally:

```bash
python main.py
```

The agent will be available at `http://localhost:8000`.