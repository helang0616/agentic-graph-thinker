import json
import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

GRAPH_DIR = ".opencode/agentic-graph"
ACTIVE_FILE = os.path.join(GRAPH_DIR, "active.json")
ARCHIVE_FILE = os.path.join(GRAPH_DIR, "archive.json")
EMBED_DIR = os.path.join(GRAPH_DIR, "embeddings")
VERSIONS_DIR = os.path.join(GRAPH_DIR, "versions")
GROUND_TRUTH_FILE = os.path.join(GRAPH_DIR, "ground_truth.json")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def load_active():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "version" not in data:
                data["version"] = "3.0"
            return data
    return {"version": "3.0", "execution_state": {"config": {"strategy": "DFS", "max_depth": 5, "archive_threshold": 30, "auto_visualize": True, "embedding_enabled": False}, "current_stack": [], "current_queue": []}, "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}}, "version_control": {"enabled": True, "git_commit": None}}

def save_active(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "3.0", "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}}}

def save_archive(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_node(args):
    data = load_active()
    node_id = args.id
    node = {
        "id": node_id,
        "title": args.title,
        "description": args.description,
        "keywords": args.keywords.split(",") if args.keywords else [],
        "status": args.status,
        "resolution": None,
        "artifacts": {"inputs": [], "outputs": []},
        "layer": getattr(args, "layer", "L0"),
        "semantic_type": getattr(args, "semantic_type", ""),
        "abstraction_path": getattr(args, "abstraction_path", "").split(",") if getattr(args, "abstraction_path", "") else []
    }
    data["knowledge_graph"]["nodes"][node_id] = node
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
    print(f"Created node: {node_id} (Layer: {node['layer']})")

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

def get_git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd="."
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except Exception:
        pass
    return None

def ensure_dirs():
    os.makedirs(GRAPH_DIR, exist_ok=True)
    os.makedirs(EMBED_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)

def load_ground_truth():
    if os.path.exists(GROUND_TRUTH_FILE):
        with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"ground_truth": []}

def save_ground_truth(data):
    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def semantic_search_nodes(args):
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("Error: sentence-transformers not installed. Run: pip install sentence-transformers")
        return
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = model.encode(args.query)
    
    active_data = load_active()
    archive_data = load_archive()
    
    results = {"active": [], "archive": []}
    
    def search_in_nodes(nodes, source):
        scored = []
        for node_id, node in nodes.items():
            text = f"{node.get('title', '')} {node.get('description', '')} {' '.join(node.get('keywords', []))}"
            if node.get('layer') == "L1" and node.get('semantic_type'):
                text += f" {node.get('semantic_type')}"
            node_emb = model.encode(text)
            sim = float(np.dot(query_embedding, node_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(node_emb)))
            scored.append((sim, node_id, node))
        
        scored.sort(reverse=True)
        for sim, node_id, node in scored[:args.top_k]:
            formatted = format_node(node)
            formatted["similarity"] = round(sim, 4)
            results[source].append(formatted)
    
    search_in_nodes(active_data.get("knowledge_graph", {}).get("nodes", {}), "active")
    search_in_nodes(archive_data.get("knowledge_graph", {}).get("nodes", {}), "archive")
    
    print_results(results, args.json)

def create_akg_snapshot(args):
    ensure_dirs()
    commit_hash = get_git_commit() or "no-git"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"{commit_hash}_{timestamp}.json"
    snapshot_path = os.path.join(VERSIONS_DIR, snapshot_name)
    
    active_data = load_active()
    snapshot = {
        "commit": commit_hash,
        "timestamp": datetime.now().isoformat(),
        "data": active_data
    }
    
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    print(f"Created AKG snapshot: {snapshot_name}")
    
    data = load_active()
    data["version_control"] = {
        "enabled": True,
        "git_commit": commit_hash,
        "last_snapshot": snapshot_name
    }
    save_active(data)
    print(f"Linked to git commit: {commit_hash}")

def list_snapshots(args):
    if not os.path.exists(VERSIONS_DIR):
        print("No snapshots found")
        return
    
    snapshots = sorted(Path(VERSIONS_DIR).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    print(f"\n=== AKG Snapshots ({len(snapshots)} total) ===")
    for sp in snapshots[:args.limit]:
        with open(sp, "r", encoding="utf-8") as f:
            data = json.load(f)
        commit = data.get("commit", "unknown")
        ts = data.get("timestamp", "")
        node_count = len(data.get("data", {}).get("knowledge_graph", {}).get("nodes", {}))
        print(f"  {sp.name} | Commit: {commit} | Nodes: {node_count} | {ts}")

def checkout_snapshot(args):
    snapshot_path = os.path.join(VERSIONS_DIR, args.snapshot)
    if not os.path.exists(snapshot_path):
        print(f"Snapshot not found: {args.snapshot}")
        return
    
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    
    if args.preview:
        print(f"Preview of {args.snapshot}:")
        print(f"  Commit: {snapshot.get('commit')}")
        print(f"  Timestamp: {snapshot.get('timestamp')}")
        print(f"  Nodes: {len(snapshot.get('data', {}).get('knowledge_graph', {}).get('nodes', {}))}")
        return
    
    save_active(snapshot["data"])
    print(f"Checked out snapshot: {args.snapshot}")

def add_ground_truth(args):
    data = load_ground_truth()
    new_entry = {
        "id": f"gt_{len(data['ground_truth']) + 1:03d}",
        "description": args.description,
        "expected_nodes": json.loads(args.expected_nodes) if isinstance(args.expected_nodes, str) else args.expected_nodes,
        "expected_edges": json.loads(args.expected_edges) if isinstance(args.expected_edges, str) else args.expected_edges,
        "keywords": args.keywords.split(","),
        "quality_score": 1.0
    }
    data["ground_truth"].append(new_entry)
    save_ground_truth(data)
    print(f"Added ground truth: {new_entry['id']}")

def benchmark_evaluation(args):
    data = load_ground_truth()
    gt_list = data.get("ground_truth", [])
    
    if not gt_list:
        print("No ground truth data. Add examples first.")
        return
    
    active_data = load_active()
    active_nodes = active_data.get("knowledge_graph", {}).get("nodes", {})
    active_edges = active_data.get("knowledge_graph", {}).get("edges", [])
    
    metrics = {"node_precision": [], "node_recall": [], "edge_precision": [], "edge_recall": []}
    
    for gt in gt_list:
        expected_nodes = {n["id"] for n in gt.get("expected_nodes", [])}
        actual_nodes = set(active_nodes.keys())
        
        tp_nodes = expected_nodes & actual_nodes
        fp_nodes = actual_nodes - expected_nodes
        fn_nodes = expected_nodes - actual_nodes
        
        prec = len(tp_nodes) / (len(tp_nodes) + len(fp_nodes)) if (len(tp_nodes) + len(fp_nodes)) > 0 else 0
        rec = len(tp_nodes) / (len(tp_nodes) + len(fn_nodes)) if (len(tp_nodes) + len(fn_nodes)) > 0 else 0
        
        metrics["node_precision"].append(prec)
        metrics["node_recall"].append(rec)
        
        expected_edges = {(e["source"], e["target"], e["relation"]) for e in gt.get("expected_edges", [])}
        actual_edges = {(e["source"], e["target"], e["relation"]) for e in active_edges}
        
        tp_edges = expected_edges & actual_edges
        fp_edges = actual_edges - expected_edges
        fn_edges = expected_edges - actual_edges
        
        e_prec = len(tp_edges) / (len(tp_edges) + len(fp_edges)) if (len(tp_edges) + len(fp_edges)) > 0 else 0
        e_rec = len(tp_edges) / (len(tp_edges) + len(fn_edges)) if (len(tp_edges) + len(fn_edges)) > 0 else 0
        
        metrics["edge_precision"].append(e_prec)
        metrics["edge_recall"].append(e_rec)
    
    print("\n=== Benchmark Results ===")
    print(f"Node Precision: {sum(metrics['node_precision'])/len(metrics['node_precision']):.2%}")
    print(f"Node Recall:    {sum(metrics['node_recall'])/len(metrics['node_recall']):.2%}")
    print(f"Edge Precision: {sum(metrics['edge_precision'])/len(metrics['edge_precision']):.2%}")
    print(f"Edge Recall:    {sum(metrics['edge_recall'])/len(metrics['edge_recall']):.2%}")
    
    f1_node = 2 * (sum(metrics['node_precision'])/len(metrics['node_precision'])) * (sum(metrics['node_recall'])/len(metrics['node_recall'])) / \
              ((sum(metrics['node_precision'])/len(metrics['node_precision'])) + (sum(metrics['node_recall'])/len(metrics['node_recall']))) if \
              ((sum(metrics['node_precision'])/len(metrics['node_precision'])) + (sum(metrics['node_recall'])/len(metrics['node_recall']))) > 0 else 0
    print(f"Node F1-Score: {f1_node:.2%}")

def main():
    parser = argparse.ArgumentParser(description="Agentic Graph CLI (v3.0 Enhanced)")
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
    p_create.add_argument("--layer", default="L0", choices=["L0", "L1", "L2"])
    p_create.add_argument("--semantic-type", default="")
    p_create.add_argument("--abstraction-path", default="")
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
    
    p_semantic = subparsers.add_parser("semantic-search")
    p_semantic.add_argument("--query", required=True, help="自然语言查询")
    p_semantic.add_argument("--top-k", type=int, default=5, help="返回结果数量")
    p_semantic.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_semantic.set_defaults(func=semantic_search_nodes)
    
    p_snapshot = subparsers.add_parser("snapshot")
    p_snapshot.add_argument("--message", default="", help="快照描述")
    p_snapshot.set_defaults(func=create_akg_snapshot)
    
    p_snapshots = subparsers.add_parser("snapshots")
    p_snapshots.add_argument("--limit", type=int, default=10, help="显示数量")
    p_snapshots.set_defaults(func=list_snapshots)
    
    p_checkout = subparsers.add_parser("checkout")
    p_checkout.add_argument("--snapshot", required=True, help="快照文件名")
    p_checkout.add_argument("--preview", action="store_true", help="仅预览")
    p_checkout.set_defaults(func=checkout_snapshot)
    
    p_gt = subparsers.add_parser("add-gt")
    p_gt.add_argument("--description", required=True, help="任务描述")
    p_gt.add_argument("--expected-nodes", required=True, help="预期节点 JSON 数组")
    p_gt.add_argument("--expected-edges", required=True, help="预期边 JSON 数组")
    p_gt.add_argument("--keywords", default="", help="关键词")
    p_gt.set_defaults(func=add_ground_truth)
    
    p_benchmark = subparsers.add_parser("benchmark")
    p_benchmark.set_defaults(func=benchmark_evaluation)
    
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()