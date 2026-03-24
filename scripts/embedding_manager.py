"""
Embedding Manager for Agentic Graph Thinker
Provides local vector embeddings using sentence-transformers
"""
import json
import os
import numpy as np
from pathlib import Path

GRAPH_DIR = ".opencode/agentic-graph"
EMBED_DIR = os.path.join(GRAPH_DIR, "embeddings")
EMBED_CACHE = os.path.join(EMBED_DIR, "cache.json")

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

class EmbeddingManager:
    def __init__(self, model_name=DEFAULT_MODEL):
        self.model_name = model_name
        self.model = None
        self.cache = self._load_cache()
    
    def _load_cache(self):
        if os.path.exists(EMBED_CACHE):
            with open(EMBED_CACHE, "r") as f:
                return json.load(f)
        return {"nodes": {}, "last_update": None}
    
    def _save_cache(self):
        os.makedirs(EMBED_DIR, exist_ok=True)
        self.cache["last_update"] = str(np.datetime64('now'))
        with open(EMBED_CACHE, "w") as f:
            json.dump(self.cache, f, indent=2)
    
    def _get_model(self):
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        return self.model
    
    def encode_text(self, text):
        model = self._get_model()
        return model.encode(text)
    
    def encode_node(self, node):
        text = self._node_to_text(node)
        return self.encode_text(text)
    
    def _node_to_text(self, node):
        parts = [
            node.get("title", ""),
            node.get("description", ""),
            " ".join(node.get("keywords", []))
        ]
        if node.get("layer") and node.get("semantic_type"):
            parts.append(node["semantic_type"])
        return " ".join(parts)
    
    def get_embedding(self, node_id, node_data):
        node_key = f"node_{node_id}"
        if node_key not in self.cache["nodes"]:
            emb = self.encode_node(node_data)
            self.cache["nodes"][node_key] = emb.tolist()
            self._save_cache()
        return np.array(self.cache["nodes"][node_key])
    
    def compute_similarity(self, emb1, emb2):
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
    
    def search_similar(self, nodes_dict, query, top_k=5):
        query_emb = self.encode_text(query)
        results = []
        
        for node_id, node_data in nodes_dict.items():
            node_emb = self.get_embedding(node_id, node_data)
            sim = self.compute_similarity(query_emb, node_emb)
            results.append({
                "id": node_id,
                "title": node_data.get("title"),
                "similarity": sim,
                "layer": node_data.get("layer", "L0"),
                "semantic_type": node_data.get("semantic_type", "")
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def rebuild_index(self, nodes_dict, force=False):
        if force:
            self.cache = {"nodes": {}, "last_update": None}
        
        for node_id, node_data in nodes_dict.items():
            self.get_embedding(node_id, node_data)
        
        print(f"Indexed {len(nodes_dict)} nodes")
        return self.cache


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Embedding Manager")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild index")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    args = parser.parse_args()
    
    manager = EmbeddingManager(args.model)
    
    active_file = os.path.join(GRAPH_DIR, "active.json")
    if os.path.exists(active_file):
        with open(active_file) as f:
            data = json.load(f)
        nodes = data.get("knowledge_graph", {}).get("nodes", {})
        manager.rebuild_index(nodes, force=args.rebuild)
    else:
        print("No active.json found")


if __name__ == "__main__":
    main()
