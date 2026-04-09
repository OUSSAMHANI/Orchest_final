"""
Orchestrator Test Script
Bypasses HTTP and calls orchestrator directly.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.graph.builder import run_orchestrator

# Test ticket
test_ticket = {
    "event_id": "test-001",
    "issue_id": 123,
    "project": "test-project",
    "title": "[AGENT:fix] test fix",
    "intent": "fix",
    "scope": "test",
    "summary": "test summary",
    "description": "This is a test description",
    "acceptance_criteria": ["test passes"],
    "priority": "normal",
    "routing_key": "fix.normal.test",
    "action": "open",
    "author": "tester",
    "url": "http://localhost",
    "workspace_path": "./workspace/test"
}

if __name__ == "__main__":
    print("=" * 50)
    print("Running Orchestrator Test")
    print("=" * 50)
    print(f"Ticket: {test_ticket.get('event_id')}")
    print("-" * 50)
    
    try:
        result = run_orchestrator(test_ticket)
        print("\n[PASS] Result:")
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)