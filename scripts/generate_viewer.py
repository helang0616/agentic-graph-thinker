"""
Enhanced Agentic Graph Viewer with Interactive Features
- Real-time task visualization
- Node CRUD operations (Create, Edit, Cancel)
- Auto-refresh with change detection
- AI change notification system
"""
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, render_template_string, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

GRAPH_DIR = ".opencode/agentic-graph"
ACTIVE_FILE = os.path.join(GRAPH_DIR, "active.json")
ARCHIVE_FILE = os.path.join(GRAPH_DIR, "archive.json")
CHANGES_FILE = os.path.join(GRAPH_DIR, "pending_changes.json")

def load_active():
    if os.path.exists(ACTIVE_FILE):
        with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": "3.0", "execution_state": {"config": {"strategy": "DFS", "max_depth": 5, "archive_threshold": 30, "auto_visualize": True}, "current_stack": [], "current_queue": []}, "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}}, "version_control": {"enabled": True}}

def save_active(data):
    os.makedirs(GRAPH_DIR, exist_ok=True)
    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_changes():
    if os.path.exists(CHANGES_FILE):
        with open(CHANGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"pending": [], "last_check": None}

def save_changes(data):
    with open(CHANGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_change(change_type, node_id, details):
    changes = load_changes()
    changes["pending"].append({
        "type": change_type,
        "node_id": node_id,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    changes["last_check"] = datetime.now().isoformat()
    save_changes(changes)

def generate_html(workspace="."):
    active_path = os.path.join(workspace, ".opencode", "agentic-graph", "active.json")
    archive_path = os.path.join(workspace, ".opencode", "agentic-graph", "archive.json")
    out_path = os.path.join(workspace, "agentic_graph_viewer.html")

    if not os.path.exists(active_path):
        print(f"Error: Could not find {active_path}")
        sys.exit(1)

    try:
        with open(active_path, "r", encoding="utf-8") as f:
            active_data = json.load(f)
    except Exception as e:
        print(f"Error reading active.json: {e}")
        sys.exit(1)

    archive_data = {}
    if os.path.exists(archive_path):
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                archive_data = json.load(f)
        except Exception as e:
            print(f"Warning: Error reading archive.json: {e}")

    merged_data = {
        "execution_state": active_data.get("execution_state", {}),
        "knowledge_graph": {
            "nodes": {},
            "edges": [],
            "artifact_registry": {}
        }
    }

    def merge_kg(source_data, is_archived=False):
        kg = source_data.get("knowledge_graph", {})
        for node_id, node in kg.get("nodes", {}).items():
            if is_archived:
                node["_is_archived"] = True
            merged_data["knowledge_graph"]["nodes"][node_id] = node
        merged_data["knowledge_graph"]["edges"].extend(kg.get("edges", []))
        merged_data["knowledge_graph"]["artifact_registry"].update(kg.get("artifact_registry", {}))

    merge_kg(archive_data, is_archived=True)
    merge_kg(active_data, is_archived=False)

    # 不再嵌入静态数据，全部从 API 动态加载
    json_str = "{}"
    config_str = "{}"

    html = f'''<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8">
  <title>Agentic Graph Dashboard - Interactive</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            gray: {{ 900: '#111827', 800: '#1f2937', 700: '#374151', 100: '#f3f4f6' }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{ background-color: #0f172a; color: #e2e8f0; font-family: 'Inter', sans-serif; overflow: hidden; }}
    #network-container {{ min-height: 500px; height: 60vh; border-radius: 0.75rem; overflow: hidden; background: #1e293b; border: 1px solid #334155; }}
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #1e293b; }}
    ::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 4px; }}
    .modal {{ display: none; position: fixed; z-index: 50; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7); }}
    .modal.show {{ display: flex; align-items: center; justify-content: center; }}
    .toast {{ position: fixed; bottom: 20px; right: 20px; z-index: 100; animation: slideIn 0.3s ease; }}
    @keyframes slideIn {{ from {{ transform: translateX(100%); }} to {{ transform: translateX(0); }} }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
    .pulse {{ animation: pulse 2s infinite; }}
  </style>
</head>
<body class="p-4 md:p-6 flex flex-col h-screen overflow-hidden">

  <!-- Header -->
  <header class="flex flex-col md:flex-row justify-between items-center mb-4 bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-700 shrink-0">
    <div class="flex items-center gap-4">
      <h1 class="text-2xl font-extrabold text-white flex items-center gap-3">
        <i class="fa-solid fa-diagram-project text-blue-500"></i> Agentic Graph
      </h1>
      <span id="connection-status" class="px-2 py-1 rounded text-xs bg-yellow-600 text-white pulse">Loading...</span>
    </div>
    <div class="flex gap-3 mt-3 md:mt-0">
      <button onclick="refreshData()" class="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm flex items-center gap-2">
        <i class="fa-solid fa-sync-alt"></i> Refresh
      </button>
      <button onclick="openAddModal()" id="add-node-btn" class="px-3 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm flex items-center gap-2">
        <i class="fa-solid fa-plus"></i> Add Node
      </button>
      <label class="px-3 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2 cursor-pointer">
        <i class="fa-solid fa-robot"></i> AI Monitor
        <input type="checkbox" id="ai-monitor" class="hidden" onchange="toggleAIMonitor()">
      </label>
    </div>
  </header>

  <!-- Stats Bar -->
  <div class="flex gap-4 mb-4 shrink-0">
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Strategy</span>
      <div class="font-bold text-blue-400" id="stat-strategy">DFS</div>
    </div>
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Active</span>
      <div class="font-bold text-yellow-400" id="stat-active">0</div>
    </div>
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Resolved</span>
      <div class="font-bold text-green-400" id="stat-resolved">0</div>
    </div>
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Stack</span>
      <div class="font-bold text-purple-400" id="stat-stack">0</div>
    </div>
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Queue</span>
      <div class="font-bold text-cyan-400" id="stat-queue">0</div>
    </div>
    <div class="bg-gray-800 px-4 py-2 rounded-lg border border-gray-700">
      <span class="text-xs text-gray-400">Changes</span>
      <div class="font-bold text-orange-400" id="stat-changes">0</div>
    </div>
  </div>

  <main class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
    <!-- Graph -->
    <div class="lg:col-span-2 flex flex-col h-full min-h-0 overflow-hidden">
      <div class="bg-gray-800 p-3 rounded-xl shadow-lg border border-gray-700 flex flex-col h-full">
        <div class="flex justify-between items-center mb-2 shrink-0">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-network-wired text-blue-400"></i> Topology Graph
          </h2>
          <div id="node-actions" class="flex gap-2" style="display:none;">
            <button onclick="selectNodeForEdit()" class="px-2 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-xs">
              <i class="fa-solid fa-edit"></i> Edit
            </button>
            <button onclick="cancelSelectedNode()" class="px-2 py-1 bg-orange-600 hover:bg-orange-700 rounded text-xs">
              <i class="fa-solid fa-ban"></i> Cancel
            </button>
            <button onclick="deleteSelectedNode()" id="delete-btn" class="px-2 py-1 bg-red-600 hover:bg-red-700 rounded text-xs" style="display:none;">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
        </div>
        <div id="network-container" class="flex-1 w-full relative"></div>
      </div>
    </div>

    <!-- Right Panel -->
    <div class="bg-gray-800 p-3 rounded-xl shadow-lg border border-gray-700 flex flex-col h-full overflow-hidden">
      <!-- Changes Panel -->
      <div class="mb-3">
        <div class="flex items-center justify-between cursor-pointer hover:bg-gray-700 rounded p-2" onclick="togglePanel('changes-panel')">
          <h2 class="text-sm font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-bell text-orange-400"></i> Pending Changes
          </h2>
          <i class="fa-solid fa-chevron-down text-gray-400"></i>
        </div>
        <div id="changes-panel" class="overflow-y-auto max-h-32 bg-gray-900 rounded-lg p-2 space-y-1">
          <div class="text-gray-500 text-xs text-center py-2">No pending changes</div>
        </div>
      </div>

      <!-- Nodes Panel -->
      <div class="flex-1 flex flex-col min-h-0">
        <div class="flex items-center justify-between cursor-pointer hover:bg-gray-700 rounded p-2 mb-2" onclick="togglePanel('nodes-panel')">
          <h2 class="text-sm font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-list-check text-green-400"></i> Task Nodes
          </h2>
          <i class="fa-solid fa-chevron-down text-gray-400"></i>
        </div>
        <div id="nodes-panel" class="overflow-y-auto pr-2 space-y-2 flex-1 min-h-0">
        </div>
      </div>
    </div>
  </main>

  <!-- Add/Edit Modal -->
  <div id="node-modal" class="modal">
    <div class="bg-gray-800 rounded-xl p-4 w-full max-w-md border border-gray-700 shadow-2xl max-h-[90vh] overflow-y-auto">
      <h2 id="modal-title" class="text-xl font-bold text-white mb-4">Add New Node</h2>
      <form id="node-form" class="space-y-3">
        <input type="hidden" id="node-id">
        <input type="hidden" id="parent-node-id">
        <div>
          <label class="block text-gray-400 text-sm mb-1">Node ID</label>
          <input type="text" id="input-id" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm" placeholder="task_xxx" required>
        </div>
        <div>
          <label class="block text-gray-400 text-sm mb-1">Title</label>
          <input type="text" id="input-title" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm" required>
        </div>
        <div>
          <label class="block text-gray-400 text-sm mb-1">Description</label>
          <textarea id="input-description" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm" rows="2"></textarea>
        </div>
        <div>
          <label class="block text-gray-400 text-sm mb-1">Keywords (comma-separated)</label>
          <input type="text" id="input-keywords" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm">
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-gray-400 text-sm mb-1">Layer</label>
            <select id="input-layer" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm">
              <option value="L0">L0 - Raw Task</option>
              <option value="L1" selected>L1 - Semantic</option>
              <option value="L2">L2 - Strategy</option>
            </select>
          </div>
          <div>
            <label class="block text-gray-400 text-sm mb-1">Status</label>
            <select id="input-status" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm">
              <option value="in_progress">In Progress</option>
              <option value="pending" selected>Pending</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-gray-400 text-sm mb-1">Semantic Type</label>
          <input type="text" id="input-semantic-type" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm" placeholder="Service.Auth">
        </div>
        <div class="flex gap-2 pt-2">
          <button type="submit" id="save-node-btn" class="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded font-medium text-sm">Add Node</button>
          <button type="button" onclick="closeModal()" class="px-4 bg-gray-600 hover:bg-gray-700 text-white py-2 rounded text-sm">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Toast Container -->
  <div id="toast-container" class="toast-container"></div>

  <script>
    // 动态加载数据，不嵌入静态数据
    const graphData = {{ knowledge_graph: {{ nodes: {{}}, edges: [], artifact_registry: {{}} }}, execution_state: {{ config: {{}} }} }};
    const configData = {{}};
    let network = null;
    let selectedNodeId = null;
    let lastDataHash = null;
    let aiMonitorEnabled = false;
    let initialLoad = true;

    function hashData(data) {{
      return JSON.stringify(data).length;
    }}

    function togglePanel(panelId) {{
      const panel = document.getElementById(panelId);
      panel.classList.toggle('hidden');
    }}

    function showToast(message, type = 'info') {{
      const colors = {{ info: 'bg-blue-600', success: 'bg-green-600', warning: 'bg-orange-600', error: 'bg-red-600' }};
      const toast = document.createElement('div');
      toast.className = `${{colors[type] || 'bg-blue-600'}} text-white px-4 py-3 rounded-lg shadow-lg mb-2`;
      toast.innerHTML = `<i class="fa-solid fa-${{type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}}-circle"></i> ${{message}}`;
      document.getElementById('toast-container').appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }}

    function openAddModal() {{
      document.getElementById('node-form').reset();
      document.getElementById('node-id').value = '';
      
      const saveBtn = document.getElementById('save-node-btn');
      
      if (selectedNodeId) {{
        document.getElementById('modal-title').innerText = 'Add Child Node';
        document.getElementById('parent-node-id').value = selectedNodeId;
        document.getElementById('input-id').value = selectedNodeId + '_c' + Date.now().toString().slice(-4);
        saveBtn.innerText = 'Add Child Node';
      }} else {{
        document.getElementById('modal-title').innerText = 'Add New Node';
        document.getElementById('parent-node-id').value = '';
        document.getElementById('input-id').value = 'task_' + Date.now().toString().slice(-6);
        saveBtn.innerText = 'Add Node';
      }}
      
      document.getElementById('input-id').disabled = false;
      document.getElementById('node-modal').classList.add('show');
      
      // 更新 header 按钮文字
      updateAddButtonText();
    }}

    function openEditModal(nodeId) {{
      const node = graphData.knowledge_graph.nodes[nodeId];
      if (!node) return;
      document.getElementById('modal-title').innerText = 'Edit Node';
      document.getElementById('node-id').value = nodeId;
      document.getElementById('parent-node-id').value = '';
      document.getElementById('input-id').value = node.id;
      document.getElementById('input-id').disabled = true;
      document.getElementById('input-title').value = node.title || '';
      document.getElementById('input-description').value = node.description || '';
      document.getElementById('input-keywords').value = (node.keywords || []).join(', ');
      document.getElementById('input-layer').value = node.layer || 'L0';
      document.getElementById('input-status').value = node.status || 'pending';
      document.getElementById('input-semantic-type').value = node.semantic_type || '';
      document.getElementById('save-node-btn').innerText = 'Save Changes';
      document.getElementById('node-modal').classList.add('show');
    }}

    function updateAddButtonText() {{
      const btn = document.getElementById('add-node-btn');
      if (selectedNodeId) {{
        const parentNode = graphData.knowledge_graph.nodes[selectedNodeId];
        const parentTitle = parentNode ? parentNode.title : selectedNodeId;
        btn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Child of ' + parentTitle.substring(0, 12);
      }} else {{
        btn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Node';
      }}
    }}

    function closeModal() {{
      document.getElementById('node-modal').classList.remove('show');
      document.getElementById('input-id').disabled = false;
      updateAddButtonText();
    }}

    document.getElementById('node-form').addEventListener('submit', async (e) => {{
      e.preventDefault();
      const nodeId = document.getElementById('node-id').value;
      const parentNodeId = document.getElementById('parent-node-id').value;
      const isEdit = !!nodeId && graphData.knowledge_graph.nodes[nodeId];
      
      const nodeData = {{
        id: document.getElementById('input-id').value,
        title: document.getElementById('input-title').value,
        description: document.getElementById('input-description').value,
        keywords: document.getElementById('input-keywords').value.split(',').map(k => k.trim()).filter(k => k),
        layer: document.getElementById('input-layer').value,
        status: document.getElementById('input-status').value,
        semantic_type: document.getElementById('input-semantic-type').value
      }};

      try {{
        const response = await fetch('/api/node', {{
          method: isEdit ? 'PUT' : 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            action: isEdit ? 'edit' : 'create',
            node: nodeData,
            original_id: isEdit ? nodeId : null,
            parent_id: parentNodeId || null
          }})
        }});
        const result = await response.json();
        if (result.success) {{
          showToast(result.message, 'success');
          closeModal();
          refreshData();
        }} else {{
          showToast(result.error, 'error');
        }}
      }} catch (err) {{
        showToast('API Error: ' + err.message, 'error');
      }}
    }});

    async function cancelSelectedNode() {{
      if (!selectedNodeId) {{
        showToast('Please select a node first', 'warning');
        return;
      }}
      if (!confirm('Cancel this node? This will mark it as cancelled.')) return;
      
      try {{
        const response = await fetch('/api/node', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            action: 'cancel',
            node_id: selectedNodeId
          }})
        }});
        const result = await response.json();
        if (result.success) {{
          showToast('Node cancelled', 'success');
          await refreshData();
          // 更新选中节点的按钮状态
          if (selectedNodeId) {{
            const node = graphData.knowledge_graph.nodes[selectedNodeId];
            const deleteBtn = document.getElementById('delete-btn');
            if (node && node.status === 'cancelled') {{
              deleteBtn.style.display = 'inline-flex';
            }} else {{
              deleteBtn.style.display = 'none';
            }}
          }}
        }} else {{
          showToast(result.error, 'error');
        }}
      }} catch (err) {{
        showToast('API Error: ' + err.message, 'error');
      }}
    }}

    function selectNodeForEdit() {{
      if (!selectedNodeId) {{
        showToast('Please select a node from the graph first', 'warning');
        return;
      }}
      openEditModal(selectedNodeId);
    }}

    async function deleteSelectedNode() {{
      if (!selectedNodeId) {{
        showToast('Please select a node first', 'warning');
        return;
      }}
      const node = graphData.knowledge_graph.nodes[selectedNodeId];
      if (!node || node.status !== 'cancelled') {{
        showToast('Only cancelled nodes can be deleted', 'warning');
        return;
      }}
      if (!confirm('Delete this node permanently?')) return;
      
      try {{
        const response = await fetch('/api/node', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            action: 'delete',
            node_id: selectedNodeId
          }})
        }});
        const result = await response.json();
        if (result.success) {{
          showToast('Node deleted', 'success');
          selectedNodeId = null;
          document.getElementById('node-actions').style.display = 'none';
          refreshData();
        }} else {{
          showToast(result.error, 'error');
        }}
      }} catch (err) {{
        showToast('API Error: ' + err.message, 'error');
      }}
    }}

    async function refreshData() {{
      try {{
        const response = await fetch('/api/data');
        const data = await response.json();
        
        // Update connection status
        document.getElementById('connection-status').className = 'px-2 py-1 rounded text-xs bg-green-600 text-white pulse';
        document.getElementById('connection-status').innerText = 'Connected';
        
        const newHash = hashData(data);
        if (newHash !== lastDataHash) {{
          graphData.knowledge_graph.nodes = data.knowledge_graph.nodes;
          graphData.knowledge_graph.edges = data.knowledge_graph.edges;
          graphData.knowledge_graph.artifact_registry = data.knowledge_graph.artifact_registry;
          graphData.execution_state = data.execution_state;
          lastDataHash = newHash;
          renderGraph();
          renderNodes();
          updateStats();
          
          if (aiMonitorEnabled && initialLoad) {{
            showToast('Task data loaded!', 'success');
            initialLoad = false;
          }} else if (aiMonitorEnabled) {{
            showToast('Task data changed!', 'info');
          }}
        }}
        
        // Check pending changes
        const changesResp = await fetch('/api/changes');
        const changes = await changesResp.json();
        renderChanges(changes);
        
        // Update Add button text based on selection
        updateAddButtonText();
        
      }} catch (err) {{
        console.error('Refresh error:', err);
        document.getElementById('connection-status').className = 'px-2 py-1 rounded text-xs bg-red-600 text-white';
        document.getElementById('connection-status').innerText = 'Disconnected';
      }}
    }}

    function renderChanges(changes) {{
      const container = document.getElementById('changes-panel');
      if (!changes.pending || changes.pending.length === 0) {{
        container.innerHTML = '<div class="text-gray-500 text-xs text-center py-2">No pending changes</div>';
      }} else {{
        container.innerHTML = changes.pending.map(c => `
          <div class="flex items-center gap-2 text-xs bg-gray-800 p-2 rounded">
            <i class="fa-solid fa-${{c.type === 'create' ? 'plus' : c.type === 'edit' ? 'edit' : 'times'}} text-${{c.type === 'create' ? 'green' : c.type === 'edit' ? 'yellow' : 'red'}}-400"></i>
            <span class="text-gray-300">${{c.node_id}}</span>
            <span class="text-gray-500">${{c.type}}</span>
          </div>
        `).join('');
      }}
      document.getElementById('stat-changes').innerText = changes.pending?.length || 0;
    }}

    function updateStats() {{
      const state = graphData.execution_state || {{}};
      const config = state.config || {{}};
      const nodes = graphData.knowledge_graph.nodes || {{}};
      
      document.getElementById('stat-strategy').innerText = config.strategy || 'DFS';
      document.getElementById('stat-active').innerText = Object.values(nodes).filter(n => n.status === 'in_progress').length;
      document.getElementById('stat-resolved').innerText = Object.values(nodes).filter(n => n.status === 'resolved').length;
      document.getElementById('stat-stack').innerText = state.current_stack?.length || 0;
      document.getElementById('stat-queue').innerText = state.current_queue?.length || 0;
    }}

    function renderNodes() {{
      const container = document.getElementById('nodes-panel');
      const nodes = graphData.knowledge_graph.nodes || {{}};
      
      container.innerHTML = Object.values(nodes).map(n => {{
        const statusColors = {{ in_progress: 'text-yellow-400', resolved: 'text-green-400', failed: 'text-red-400', pending: 'text-gray-400', cancelled: 'text-gray-500' }};
        const icon = {{ in_progress: 'fa-spinner fa-spin', resolved: 'fa-check', failed: 'fa-times', pending: 'fa-clock', cancelled: 'fa-ban' }}[n.status] || 'fa-circle';
        
        const outputs = n.artifacts?.outputs || [];
        const inputs = n.artifacts?.inputs || [];
        
        return `
          <div class="bg-gray-700 p-3 rounded-lg border border-gray-600 hover:border-blue-500 cursor-pointer transition" onclick="selectNode('${{n.id}}')">
            <div class="flex justify-between items-start">
              <div class="font-medium text-white text-sm">${{n.title}}</div>
              <i class="fa-solid ${{icon}} ${{statusColors[n.status]}} text-xs"></i>
            </div>
            <div class="text-gray-400 text-xs mt-1 truncate">${{n.description || ''}}</div>
            <div class="flex gap-2 mt-2">
              <span class="px-2 py-0.5 bg-gray-600 rounded text-xs">${{n.layer || 'L0'}}</span>
              ${{n.semantic_type ? `<span class="px-2 py-0.5 bg-blue-900 rounded text-xs text-blue-300">${{n.semantic_type}}</span>` : ''}}
              ${{n.resolution ? `<span class="px-2 py-0.5 bg-purple-900 rounded text-xs text-purple-300">${{n.resolution.timestamp ? new Date(n.resolution.timestamp).toLocaleString() : ''}}</span>` : ''}}
            </div>
            ${{n.resolution ? `
            <div class="mt-2 pt-2 border-t border-gray-600">
              ${{n.resolution.summary ? `
              <div class="text-yellow-400 text-xs font-medium">Summary:</div>
              <div class="text-gray-300 text-xs mt-1">${{n.resolution.summary}}</div>
              ` : ''}}
              ${{n.resolution.context_injected ? `
              <div class="text-blue-400 text-xs font-medium mt-1">Context:</div>
              <div class="text-gray-300 text-xs mt-1">${{n.resolution.context_injected}}</div>
              ` : ''}}
              ${{n.resolution.learnings && n.resolution.learnings.length > 0 ? `
              <div class="text-green-400 text-xs font-medium mt-1">Learnings:</div>
              <div class="flex flex-wrap gap-1 mt-1">
                ${{n.resolution.learnings.map(l => `<span class="px-1.5 py-0.5 bg-green-900/50 text-green-300 rounded text-xs">${{l}}</span>`).join('')}}
              </div>
              ` : ''}}
              ${{n.resolution.validation_status ? `
              <div class="text-orange-400 text-xs font-medium mt-1">Validation:</div>
              <div class="text-gray-300 text-xs mt-1">${{n.resolution.validation_status}}</div>
              ` : ''}}
            </div>
            ` : ''}}
            ${{outputs.length > 0 ? `
            <div class="mt-2 pt-2 border-t border-gray-600">
              <div class="text-green-400 text-xs font-medium">Outputs:</div>
              <div class="flex flex-wrap gap-1 mt-1">
                ${{outputs.map(f => `<span class="px-1.5 py-0.5 bg-green-900/50 text-green-300 rounded text-xs">${{f}}</span>`).join('')}}
              </div>
            </div>
            ` : ''}}
            ${{inputs.length > 0 ? `
            <div class="mt-1">
              <div class="text-blue-400 text-xs font-medium">Inputs:</div>
              <div class="flex flex-wrap gap-1 mt-1">
                ${{inputs.map(f => `<span class="px-1.5 py-0.5 bg-blue-900/50 text-blue-300 rounded text-xs">${{f}}</span>`).join('')}}
              </div>
            </div>
            ` : ''}}
          </div>
        `;
      }}).join('');
    }}

    function selectNode(nodeId) {{
      selectedNodeId = nodeId;
      if (network) {{
        network.selectNodes([nodeId]);
      }}
      // 显示操作按钮
      document.getElementById('node-actions').style.display = 'flex';
      
      // 获取节点状态
      const node = graphData.knowledge_graph.nodes[nodeId];
      const deleteBtn = document.getElementById('delete-btn');
      
      // 只有已取消的节点才显示删除按钮
      if (node && node.status === 'cancelled') {{
        deleteBtn.style.display = 'inline-flex';
      }} else {{
        deleteBtn.style.display = 'none';
      }}
      
      // 更新 Add 按钮文字
      updateAddButtonText();
    }}

    function toggleAIMonitor() {{
      aiMonitorEnabled = document.getElementById('ai-monitor').checked;
      showToast(aiMonitorEnabled ? 'AI Monitor enabled' : 'AI Monitor disabled', aiMonitorEnabled ? 'success' : 'info');
    }}

    function renderGraph() {{
      const nodes = graphData.knowledge_graph.nodes || {{}};
      const edges = graphData.knowledge_graph.edges || [];

      const visNodes = new vis.DataSet(Object.values(nodes).map(n => {{
        let bg = '#334155', border = '#475569';
        if (n._is_archived) {{ bg = '#1e293b'; border = '#334155'; }}
        else if (n.status === 'resolved') {{ bg = '#065f46'; border = '#10b981'; }}
        else if (n.status === 'failed') {{ bg = '#7f1d1d'; border = '#ef4444'; }}
        else if (n.status === 'in_progress') {{ bg = '#78350f'; border = '#f59e0b'; }}
        else if (n.status === 'cancelled') {{ bg = '#374151'; border = '#6b7280'; }}

        let tip = n.description || '';
        if (n.keywords?.length) tip += '\\n\\nKeywords: ' + n.keywords.join(', ');
        if (n.layer) tip += '\\n\\nLayer: ' + n.layer;
        if (n.semantic_type) tip += '\\nType: ' + n.semantic_type;

        return {{
          id: n.id,
          label: n.title,
          title: tip,
          color: {{ background: bg, border: border }},
          font: {{ color: '#f8fafc', size: 12 }},
          shape: 'box',
          margin: 10,
          borderWidth: 2
        }};
      }}));

      const visEdges = new vis.DataSet(edges.map(e => {{
        let colors = {{ blocked_by: '#ef4444', subtask_of: '#60a5fa', consumes_output_of: '#34d399' }};
        return {{
          from: e.target,
          to: e.source,
          label: e.relation,
          font: {{ color: colors[e.relation] || '#94a3b8', size: 9, background: '#1e293b' }},
          color: {{ color: colors[e.relation] || '#94a3b8' }},
          width: 2,
          arrows: {{ to: {{ enabled: true, scaleFactor: 0.3 }} }},
          dashes: e.relation === 'blocked_by'
        }};
      }}));

      const container = document.getElementById('network-container');
      if (network) network.destroy();
      
      network = new vis.Network(container, {{nodes: visNodes, edges: visEdges}}, {{
        layout: {{ hierarchical: {{ enabled: true, direction: 'UD', levelSeparation: 70 }} }},
        physics: false,
        interaction: {{ hover: true, dragNodes: true, select: true }}
      }});

      network.on('selectNode', (params) => {{
        if (params.nodes.length > 0) {{
          selectedNodeId = params.nodes[0];
          document.getElementById('node-actions').style.display = 'flex';
          const node = graphData.knowledge_graph.nodes[selectedNodeId];
          const deleteBtn = document.getElementById('delete-btn');
          if (node && node.status === 'cancelled') {{
            deleteBtn.style.display = 'inline-flex';
          }} else {{
            deleteBtn.style.display = 'none';
          }}
          updateAddButtonText();
        }}
      }});

      network.on('deselectNode', (params) => {{
        selectedNodeId = null;
        document.getElementById('node-actions').style.display = 'none';
        updateAddButtonText();
      }});
    }}

    // Auto-refresh
    setInterval(refreshData, 3000);
    
    // Initial load from API
    refreshData();
  </script>
</body>
</html>'''

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return out_path


def create_api_server(workspace="."):
    """Create Flask API server for CRUD operations"""
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return render_template_string(open(os.path.join(workspace, 'agentic_graph_viewer.html'), 'r', encoding='utf-8').read())
    
    @app.route('/api/data')
    def api_data():
        data = load_active()
        return jsonify(data)
    
    @app.route('/api/node', methods=['POST', 'PUT'])
    def api_node():
        req = request.json
        action = req.get('action')
        data = load_active()
        
        if action == 'create' or action == 'edit':
            node = req.get('node', {})
            node_id = node.get('id')
            original_id = req.get('original_id')
            parent_id = req.get('parent_id')
            
            if action == 'edit' and original_id:
                if original_id in data['knowledge_graph']['nodes']:
                    del data['knowledge_graph']['nodes'][original_id]
            
            data['knowledge_graph']['nodes'][node_id] = {
                'id': node_id,
                'title': node.get('title', ''),
                'description': node.get('description', ''),
                'keywords': node.get('keywords', []),
                'layer': node.get('layer', 'L0'),
                'semantic_type': node.get('semantic_type', ''),
                'status': node.get('status', 'pending'),
                'artifacts': {'inputs': [], 'outputs': []},
                'resolution': None
            }
            
            # Create edge to parent if specified
            if parent_id and action == 'create':
                # Check if edge already exists
                edge_exists = any(
                    e['source'] == node_id and e['target'] == parent_id 
                    for e in data['knowledge_graph']['edges']
                )
                if not edge_exists:
                    data['knowledge_graph']['edges'].append({
                        'source': node_id,
                        'target': parent_id,
                        'relation': 'subtask_of'
                    })
            
            add_change('create' if action == 'create' else 'edit', node_id, node)
            save_active(data)
            return jsonify({'success': True, 'message': f"Node {node_id} {'created' if action == 'create' else 'updated'}"})
        
        elif action == 'cancel':
            node_id = req.get('node_id')
            if node_id in data['knowledge_graph']['nodes']:
                data['knowledge_graph']['nodes'][node_id]['status'] = 'cancelled'
                add_change('cancel', node_id, {'status': 'cancelled'})
                save_active(data)
                return jsonify({'success': True, 'message': f"Node {node_id} cancelled"})
            return jsonify({'success': False, 'error': 'Node not found'})
        
        elif action == 'delete':
            node_id = req.get('node_id')
            if node_id in data['knowledge_graph']['nodes']:
                node = data['knowledge_graph']['nodes'][node_id]
                if node.get('status') != 'cancelled':
                    return jsonify({'success': False, 'error': 'Only cancelled nodes can be deleted'})
                # 删除关联的边
                data['knowledge_graph']['edges'] = [
                    e for e in data['knowledge_graph']['edges']
                    if e['source'] != node_id and e['target'] != node_id
                ]
                # 删除节点
                del data['knowledge_graph']['nodes'][node_id]
                add_change('delete', node_id, {'deleted': True})
                save_active(data)
                return jsonify({'success': True, 'message': f"Node {node_id} deleted"})
            return jsonify({'success': False, 'error': 'Node not found'})
        
        return jsonify({'success': False, 'error': 'Invalid action'})
    
    @app.route('/api/changes')
    def api_changes():
        return jsonify(load_changes())
    
    @app.route('/api/clear-changes', methods=['POST'])
    def api_clear_changes():
        save_changes({'pending': [], 'last_check': datetime.now().isoformat()})
        return jsonify({'success': True})
    
    return app


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Enhanced Agentic Graph Viewer")
    parser.add_argument("workspace", nargs="?", default=".", help="Workspace directory")
    parser.add_argument("--server", action="store_true", help="Start API server")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    args = parser.parse_args()
    
    workspace = args.workspace
    
    if args.server:
        if not FLASK_AVAILABLE:
            print("Flask not installed. Install with: pip install flask")
            sys.exit(1)
        
        out_path = generate_html(workspace)
        print(f"Generated viewer: {out_path}")
        
        app = create_api_server(workspace)
        print(f"Starting server at http://localhost:{args.port}")
        app.run(port=args.port, debug=False)
    else:
        out_path = generate_html(workspace)
        print(f"Successfully generated interactive visualization at: {out_path}")
        print("To start API server with CRUD support, run with --server flag")


if __name__ == "__main__":
    main()
