"""
Outputs a JSON of wired nodes so the audit can trust runtime graph truth.
"""
import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.langgraph.graph import get_wired_nodes_snapshot

def main():
    snapshot = get_wired_nodes_snapshot()
    print(json.dumps({"wired_nodes": snapshot}, ensure_ascii=False))

if __name__ == "__main__":
    main()