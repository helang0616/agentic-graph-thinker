import json
import os
import sys
import argparse
from datetime import datetime

GRAPH_DIR = ".opencode/agentic-graph"
ACTIVE_FILE = os.path.join(GRAPH_DIR, "active.json")
ARCHIVE_FILE = os.path.join(GRAPH_DIR, "archive.json")

def load_active():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "2.1", "execution_state": {"config": {"strategy": "DFS", "max_depth": 5, "archive_threshold": 30, "auto_visualize": True}, "current_stack": [], "current_queue": []}, "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}}}

def save_active(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "2.1", "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}}}

def save_archive(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_node(args):
    data = load_active()
    node_id = args.id
    data["knowledge_graph"]["nodes"][node_id] = {
        "id": node_id,
        "title": args.title,
        "description": args.description,
        "keywords": args.keywords.split(",") if args.keywords else [],
        "status": args.status,
        "resolution": None,
        "artifacts": {"inputs": [], "outputs": []}
    }
    if args.relation and args.target:
        data["knowledge_graph"]["edges"].append({
            "source": node_id,
            "target": args.target,
            "relation": args.relation
        })
    if args.stack:
        data["execution_state"]["current_stack"].append(node_id)
    if args.queue:
        data["execution_state"]["current_queue"].append(node_id)
    save_active(data)
    print(f"Created node: {node_id}")

def resolve_node(args):
    data = load_active()
    node_id = args.id
    if node_id not in data["knowledge_graph"]["nodes"]:
        print(f"Error: Node {node_id} not found")
        return
    node = data["knowledge_graph"]["nodes"][node_id]
    node["status"] = args.status
    node["resolution"] = {
        "summary": args.summary,
        "context_injected": args.context_injected,
        "learnings": args.learnings.split("|") if args.learnings else [],
        "artifacts_diff": args.artifacts_diff.split("|") if args.artifacts_diff else [],
        "validation_status": args.validation_status or "",
        "timestamp": datetime.now().isoformat()
    }
    if args.inputs:
        node["artifacts"]["inputs"] = args.inputs.split(",")
    if args.outputs:
        node["artifacts"]["outputs"] = args.outputs.split(",")
    if args.stack:
        if node_id in data["execution_state"]["current_stack"]:
            data["execution_state"]["current_stack"].remove(node_id)
    if args.queue:
        if node_id in data["execution_state"]["current_queue"]:
            data["execution_state"]["current_queue"].remove(node_id)
    save_active(data)
    print(f"Resolved node: {node_id} as {args.status}")

def register_artifact(args):
    data = load_active()
    path = args.path
    data["knowledge_graph"]["artifact_registry"][path] = {
        "generated_by": args.task_id,
        "description": args.description,
        "last_updated": datetime.now().isoformat()
    }
    save_active(data)
    print(f"Registered artifact: {path}")

def update_config(args):
    data = load_active()
    if args.strategy:
        data["execution_state"]["config"]["strategy"] = args.strategy
    if args.max_depth:
        data["execution_state"]["config"]["max_depth"] = int(args.max_depth)
    if args.archive_threshold:
        data["execution_state"]["config"]["archive_threshold"] = int(args.archive_threshold)
    if args.auto_visualize is not None:
        data["execution_state"]["config"]["auto_visualize"] = args.auto_visualize.lower() == "true" if isinstance(args.auto_visualize, str) else args.auto_visualize
    save_active(data)
    print(f"Updated config")

def gc_archive(args):
    data = load_active()
    threshold = data["execution_state"]["config"].get("archive_threshold", 30)
    nodes = data["knowledge_graph"]["nodes"]
    if len(nodes) <= threshold:
        print("No GC needed")
        return
    to_archive = []
    for node_id, node in nodes.items():
        if node["status"] == "resolved":
            has_dependency = False
            for edge in data["knowledge_graph"]["edges"]:
                if edge["target"] == node_id:
                    target_node = data["knowledge_graph"]["nodes"].get(edge["source"])
                    if target_node and target_node["status"] == "in_progress":
                        has_dependency = True
                        break
            if not has_dependency:
                to_archive.append(node_id)
    if not to_archive:
        print("No nodes to archive")
        return
    archive_data = load_archive()
    for node_id in to_archive:
        node = nodes.pop(node_id)
        archive_data["knowledge_graph"]["nodes"][node_id] = node
    data["knowledge_graph"]["edges"] = [e for e in data["knowledge_graph"]["edges"] if e["source"] not in to_archive and e["target"] not in to_archive]
    for path, art in list(data["knowledge_graph"]["artifact_registry"].items()):
        if art["generated_by"] in to_archive:
            archive_data["knowledge_graph"]["artifact_registry"][path] = art
            del data["knowledge_graph"]["artifact_registry"][path]
    save_active(data)
    save_archive(archive_data)
    print(f"Archived {len(to_archive)} nodes")

def match_keywords(node, keywords):
    text = " ".join([
        node.get("title", ""),
        node.get("description", ""),
        " ".join(node.get("keywords", []))
    ]).lower()
    return all(k in text for k in keywords)

def format_node(node):
    res = node.get("resolution", {}) or {}
    return {
        "id": node.get("id"),
        "title": node.get("title"),
        "status": node.get("status"),
        "keywords": node.get("keywords", []),
        "summary": res.get("summary", ""),
        "learnings": res.get("learnings", []),
        "context_injected": res.get("context_injected", "")
    }

def print_results(results, json_output):
    if json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return
    
    for source, nodes in results.items():
        if nodes:
            print(f"\n=== {source.upper()} ===")
            for n in nodes:
                print(f"  [{n['id']}] {n['title']} ({n['status']})")
                print(f"      Keywords: {', '.join(n['keywords'])}")
                if n['summary']:
                    print(f"      Summary: {n['summary']}")
                if n['learnings']:
                    print(f"      Learnings: {n['learnings']}")
    total = sum(len(nodes) for nodes in results.values())
    print(f"\nTotal: {total} result(s) found")

def search_nodes(args):
    keyword_list = [k.strip().lower() for k in args.keywords.split(",") if k.strip()]
    search_archive = not args.only_active
    
    results = {"active": [], "archive": []}
    
    active_data = load_active()
    for node_id, node in active_data.get("knowledge_graph", {}).get("nodes", {}).items():
        if match_keywords(node, keyword_list):
            results["active"].append(format_node(node))
    
    if search_archive and os.path.exists(ARCHIVE_FILE):
        archive_data = load_archive()
        for node_id, node in archive_data.get("knowledge_graph", {}).get("nodes", {}).items():
            if match_keywords(node, keyword_list):
                results["archive"].append(format_node(node))
    
    print_results(results, args.json)

def main():
    parser = argparse.ArgumentParser(description="Agentic Graph CLI")
    subparsers = parser.add_subparsers()
    
    p_create = subparsers.add_parser("create")
    p_create.add_argument("--id", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--description", required=True)
    p_create.add_argument("--keywords", default="")
    p_create.add_argument("--status", default="in_progress")
    p_create.add_argument("--relation", default="")
    p_create.add_argument("--target", default="")
    p_create.add_argument("--stack", action="store_true")
    p_create.add_argument("--queue", action="store_true")
    p_create.set_defaults(func=create_node)
    
    p_resolve = subparsers.add_parser("resolve")
    p_resolve.add_argument("--id", required=True)
    p_resolve.add_argument("--status", required=True)
    p_resolve.add_argument("--summary", required=True)
    p_resolve.add_argument("--context_injected", default="")
    p_resolve.add_argument("--learnings", default="")
    p_resolve.add_argument("--artifacts_diff", default="")
    p_resolve.add_argument("--validation_status", default="")
    p_resolve.add_argument("--inputs", default="")
    p_resolve.add_argument("--outputs", default="")
    p_resolve.add_argument("--stack", action="store_true")
    p_resolve.add_argument("--queue", action="store_true")
    p_resolve.set_defaults(func=resolve_node)
    
    p_reg = subparsers.add_parser("register")
    p_reg.add_argument("--path", required=True)
    p_reg.add_argument("--description", required=True)
    p_reg.add_argument("--task-id", required=True)
    p_reg.set_defaults(func=register_artifact)
    
    p_config = subparsers.add_parser("config")
    p_config.add_argument("--strategy", default="")
    p_config.add_argument("--max_depth", default="")
    p_config.add_argument("--archive_threshold", default="")
    p_config.add_argument("--auto_visualize", default=None, choices=["true", "false"])
    p_config.set_defaults(func=update_config)
    
    p_gc = subparsers.add_parser("gc")
    p_gc.set_defaults(func=gc_archive)
    
    p_search = subparsers.add_parser("search")
    p_search.add_argument("--keywords", required=True, help="搜索关键词，逗号分隔")
    p_search.add_argument("--only-active", action="store_true", help="仅搜索 active.json")
    p_search.add_argument("--only-archive", action="store_true", help="仅搜索 archive.json")
    p_search.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_search.set_defaults(func=search_nodes)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()