"""
Outputs a JSON of wired nodes so the audit can trust runtime graph truth.

This script imports only from wiring_registry (no heavy graph dependencies)
to provide fast introspection of the node registry for audit tooling.
"""
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from wiring_registry (lightweight) instead of graph (heavy)
from app.core.langgraph.wiring_registry import (
    get_wired_nodes_snapshot,
    initialize_phase4_registry,
    initialize_phase5_registry,
    initialize_phase6_registry,
    initialize_phase7_registry,
    initialize_phase8_registry,
)

def main():
    # Initialize all phase registries
    initialize_phase4_registry()
    initialize_phase5_registry()
    initialize_phase6_registry()
    initialize_phase7_registry()
    initialize_phase8_registry()

    # Get snapshot and output JSON
    snapshot = get_wired_nodes_snapshot()

    # Convert int keys to strings for JSON compatibility
    json_snapshot = {str(k): v for k, v in snapshot.items()}

    print(json.dumps({"wired_nodes": json_snapshot}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()