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