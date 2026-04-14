"""File management tools — wraps LangChain FileManagementToolkit (SRP: filesystem I/O only)."""
import os
import shutil
from langchain_community.agent_toolkits import FileManagementToolkit


def initiate_directory(workspace_dir: str) -> list:
    """
    Create a directory at the specified path.

    Args:
        workspace_dir: The path to the directory to create.
    """
    os.makedirs(workspace_dir, exist_ok=True)
    return ["Directory created successfully"]


def clear_directory(workspace_dir: str) -> list:
    """
    Remove every file and sub-directory inside *workspace_dir*,
    then recreate the (now-empty) directory so callers can write
    into it immediately.

    Args:
        workspace_dir: The path to the directory to clear.
    """
    if not os.path.isdir(workspace_dir):
        os.makedirs(workspace_dir, exist_ok=True)
        return ["Directory did not exist — created fresh"]

    removed = 0
    for item in os.listdir(workspace_dir):
        item_path = os.path.join(workspace_dir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            else:
                shutil.rmtree(item_path)
            removed += 1
        except Exception as e:
            print(f"[clear_directory] Could not remove {item_path}: {e}")

    return [f"Directory cleared successfully ({removed} items removed)"]