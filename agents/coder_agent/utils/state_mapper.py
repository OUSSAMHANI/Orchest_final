"""
Helper utility for parsing and mapping state outputs between agents.
"""
from typing import List, Dict, Any

def map_previous_outputs(
    previous_outputs: Dict[str, Any], 
    target_key: str, 
    fields: List[str], 
    fallback: str = ""
) -> str:
    """
    Standardized mapper to convert structured previous outputs from the orchestrator 
    into a flattened text format suitable for agent prompts.
    """
    if not previous_outputs:
        return fallback

    prev_data = previous_outputs.get(target_key, {})
    if not prev_data:
        return fallback
        
    result_text = ""
    if isinstance(prev_data, str):
        result_text = prev_data
    elif isinstance(prev_data, dict):
        direct_text_key = f"{target_key}_text"
        if direct_text_key in prev_data:
            result_text = prev_data[direct_text_key]
        else:
            parts = []
            for field in fields:
                val = prev_data.get(field)
                if val:
                    title = field.replace('_', ' ').title()
                    if isinstance(val, list):
                        parts.append(f"{title}:\n- " + "\n- ".join(str(v) for v in val))
                    else:
                        parts.append(f"{title}:\n{val}")
            
            result_text = "\n\n".join(parts)
    
    return result_text.strip() if result_text.strip() else fallback
