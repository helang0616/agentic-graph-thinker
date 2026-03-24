import json
import os
import sys

def main():
    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
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

    # Merge active and archive data
    merged_data = {
        "execution_state": active_data.get("execution_state", {}),
        "knowledge_graph": {
            "nodes": {},
            "edges": [],
            "artifact_registry": {}
        }
    }

    # Helper to merge dicts/lists
    def merge_kg(source_data, is_archived=False):
        kg = source_data.get("knowledge_graph", {})
        for node_id, node in kg.get("nodes", {}).items():
            if is_archived:
                node["_is_archived"] = True
            merged_data["knowledge_graph"]["nodes"][node_id] = node
        merged_data["knowledge_graph"]["edges"].extend(kg.get("edges", []))
        merged_data["knowledge_graph"]["artifact_registry"].update(kg.get("artifact_registry", {}))

    # Merge archive first, then active (so active overrides if any duplicates)
    merge_kg(archive_data, is_archived=True)
    merge_kg(active_data, is_archived=False)

    json_str = json.dumps(merged_data)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
  <meta charset="UTF-8">
  <title>Agentic Graph Dashboard</title>
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
    #network-container {{ min-height: 600px; height: 75vh; border-radius: 0.75rem; overflow: hidden; background: #1e293b; border: 1px solid #334155; }}
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #1e293b; }}
    ::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #64748b; }}
    .fa-chevron-down {{ transition: transform 0.2s ease; }}
  </style>
</head>
<body class="p-4 md:p-8 flex flex-col h-screen overflow-hidden">

  <header class="flex flex-col md:flex-row justify-between items-center mb-6 bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700 shrink-0">
    <div>
      <h1 class="text-3xl font-extrabold text-white flex items-center gap-3">
        <i class="fa-solid fa-diagram-project text-blue-500"></i> Agentic Graph Dashboard
      </h1>
      <p class="text-gray-400 mt-2 text-sm">Real-time Task Dependency & Artifact Tracking</p>
    </div>
    <div class="flex gap-4 mt-4 md:mt-0">
      <div class="bg-gray-700 px-4 py-2 rounded-lg text-center border border-gray-600">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Strategy</div>
        <div class="font-bold text-blue-400" id="stat-strategy">DFS</div>
      </div>
      <div class="bg-gray-700 px-4 py-2 rounded-lg text-center border border-gray-600">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Tasks</div>
        <div class="font-bold text-green-400" id="stat-tasks">0</div>
      </div>
      <div class="bg-gray-700 px-4 py-2 rounded-lg text-center border border-gray-600">
        <div class="text-xs text-gray-400 uppercase tracking-wide">Artifacts</div>
        <div class="font-bold text-purple-400" id="stat-artifacts">0</div>
      </div>
    </div>
  </header>

  <main class="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0 overflow-hidden">
    <!-- Left Column: Graph -->
    <div class="lg:col-span-2 flex flex-col h-full min-h-0 overflow-hidden">
      <div class="bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-700 flex flex-col h-full">
        <h2 class="text-lg font-bold text-white mb-3 flex items-center gap-2 shrink-0">
          <i class="fa-solid fa-network-wired text-blue-400"></i> Topology Graph
        </h2>
        <div id="network-container" class="flex-1 w-full relative"></div>
      </div>
    </div>

    <!-- Right Column: Details & Artifacts -->
    <div class="bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-700 flex flex-col h-full overflow-hidden">
      <div class="flex items-center justify-between cursor-pointer hover:bg-gray-700 rounded p-2 -m-2 mb-0" onclick="document.getElementById('artifacts-panel').classList.toggle('hidden')">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-folder-open text-purple-400"></i> Artifact Registry
        </h2>
        <i class="fa-solid fa-chevron-down text-gray-400" id="artifacts-chevron"></i>
      </div>
      <div id="artifacts-panel" class="overflow-y-auto pr-2 space-y-3 flex-1 min-h-0 transition-all duration-200">
        <!-- Artifacts injected here -->
      </div>
      
      <div class="mt-4 pt-4 border-t border-gray-700 shrink-0 h-2/5 flex flex-col min-h-0">
        <div class="flex items-center justify-between cursor-pointer hover:bg-gray-700 rounded p-2 -m-2 mb-0" onclick="document.getElementById('tree-panel').classList.toggle('hidden')">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-list-check text-green-400"></i> Execution Tree
          </h2>
          <i class="fa-solid fa-chevron-down text-gray-400" id="tree-chevron"></i>
        </div>
        <div id="tree-panel" class="overflow-y-auto pr-2 space-y-2 text-sm flex-1 min-h-0 transition-all duration-200">
          <!-- Tree injected here -->
        </div>
      </div>
    </div>
  </main>

  <script>
    const graphData = {json_str};

    // Toggle collapse with chevron rotation
    function setupToggle(panelId, chevronId) {{
      const panel = document.getElementById(panelId);
      const chevron = document.getElementById(chevronId);
      if (panel && chevron) {{
        panel.dataset.chevron = chevronId;
      }}
    }}
    
    // Add click handlers for panel headers
    document.querySelectorAll('.cursor-pointer').forEach(header => {{
      header.addEventListener('click', function() {{
        const panel = this.parentElement.querySelector('[id$="-panel"]');
        const chevron = this.querySelector('.fa-chevron-down');
        if (panel && chevron) {{
          chevron.style.transform = panel.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(-90deg)';
        }}
      }});
    }});

    function init() {{
      const state = graphData.execution_state || {{}};
      const kg = graphData.knowledge_graph || {{}};
      const nodes = kg.nodes || {{}};
      const edges = kg.edges || [];
      const registry = kg.artifact_registry || {{}};

      // Update Stats
      document.getElementById('stat-strategy').innerText = state.config?.strategy || 'DFS';
      document.getElementById('stat-tasks').innerText = Object.keys(nodes).length;
      document.getElementById('stat-artifacts').innerText = Object.keys(registry).length;

      // Draw Network
      const visNodes = new vis.DataSet(Object.values(nodes).map(n => {{
        let bg = '#334155', border = '#475569';
        
        if (n._is_archived) {{
            bg = '#1e293b'; border = '#334155'; // Darker for archived
        }} else if (n.status === 'resolved') {{ 
            bg = '#065f46'; border = '#10b981'; 
        }} else if (n.status === 'failed') {{ 
            bg = '#7f1d1d'; border = '#ef4444'; // Red for failed
        }} else if (n.status === 'in_progress') {{ 
            bg = '#78350f'; border = '#f59e0b'; 
        }}
        
        const archivedTag = n._is_archived ? " (Archived)" : "";
        
        // Rich tooltip
        let tip = n.description || '';
        if (n.resolution && typeof n.resolution === "object") {{
          tip += "\\n\\n=== Result ===\\n" + (n.resolution.summary || "");
          if (n.resolution.context_injected) {{
            tip += "\\n\\n=== Context ===\\n" + n.resolution.context_injected;
          }}
          if (n.resolution.learnings && n.resolution.learnings.length > 0) {{
            tip += "\\n\\n=== Learnings ===\\n" + n.resolution.learnings.join("\\n");
          }}
        }}
        if (n.keywords && n.keywords.length > 0) {{
          tip += "\\n\\nKeywords: " + n.keywords.join(", ");
        }}
        
        return {{
          id: n.id,
          label: n.title + archivedTag,
          title: tip,
          color: {{ background: bg, border: border }},
          font: {{ color: n._is_archived ? '#94a3b8' : '#f8fafc', size: 12 }},
          shape: 'box',
          margin: 12,
          borderWidth: 2,
          shadow: {{ enabled: true, color: 'rgba(0,0,0,0.3)', size: 8, x: 2, y: 2 }}
        }};
      }}));

      const visEdges = new vis.DataSet(edges.map(e => {{
        let edgeColor = '#94a3b8';
        let edgeWidth = 2;
        let labelColor = '#fbbf24';
        if (e.relation === 'blocked_by') {{ edgeColor = '#ef4444'; labelColor = '#f87171'; edgeWidth = 2; }}
        else if (e.relation === 'subtask_of') {{ edgeColor = '#60a5fa'; labelColor = '#93c5fd'; edgeWidth = 2; }}
        else if (e.relation === 'consumes_output_of') {{ edgeColor = '#34d399'; labelColor = '#6ee7b7'; edgeWidth = 2; }}
        
        return {{
          from: e.target,
          to: e.source,
          label: e.relation,
          font: {{ 
            color: labelColor, 
            size: 10, 
            face: 'monospace', 
            background: '#1e293b',
            strokeWidth: 2,
            strokeColor: '#0f172a'
          }},
          color: {{ color: edgeColor, highlight: '#ffffff' }},
          width: edgeWidth,
          arrows: {{ to: {{ enabled: true, scaleFactor: 0.3 }} }},
          smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.3 }},
          dashes: e.relation === 'blocked_by'
        }};
      }}));

      const network = new vis.Network(document.getElementById('network-container'), {{nodes: visNodes, edges: visEdges}}, {{
        layout: {{
          hierarchical: {{ 
            enabled: true, 
            direction: 'UD', 
            sortMethod: 'directed',
            levelSeparation: 80,
            nodeSpacing: 150
          }}
        }},
        physics: false,
        interaction: {{ dragNodes: true, dragEdges: true, hover: true }}
      }});

      // Draw Artifacts
      const artContainer = document.getElementById('artifacts-panel');
      if (Object.keys(registry).length === 0) {{
        artContainer.innerHTML = '<div class="text-gray-500 text-sm italic p-4 text-center">No artifacts registered yet.</div>';
      }} else {{
        Object.entries(registry).forEach(([path, info]) => {{
          artContainer.innerHTML += `
            <div class="bg-gray-700 p-3 rounded-lg border border-gray-600 hover:border-purple-500 transition">
              <div class="flex justify-between items-start">
                <a href="${{path}}" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono text-sm break-all flex items-center gap-2">
                  <i class="fa-regular fa-file-code"></i> ${{path}}
                </a>
              </div>
              <p class="text-gray-300 text-xs mt-2">${{info.description}}</p>
              <div class="text-gray-500 text-[10px] mt-2 uppercase tracking-wide">
                <i class="fa-solid fa-hammer"></i> Created by: <span class="text-gray-400">${{info.generated_by}}</span>
              </div>
            </div>
          `;
        }});
      }}

      // Draw Tree
      const treeContainer = document.getElementById('tree-panel');
      Object.values(nodes).forEach(n => {{
        let icon = n.status === 'resolved' ? '<i class="fa-solid fa-check text-green-400"></i>' : 
                   n.status === 'failed' ? '<i class="fa-solid fa-xmark text-red-400"></i>' : 
                   '<i class="fa-solid fa-spinner fa-spin text-yellow-400"></i>';
        if (n._is_archived) icon = '<i class="fa-solid fa-box-archive text-gray-500"></i>';
        
        treeContainer.innerHTML += `
          <details class="bg-gray-700 rounded-lg overflow-hidden border border-gray-600">
            <summary class="p-3 font-medium cursor-pointer hover:bg-gray-600 flex justify-between items-center outline-none list-none">
              <div class="flex items-center gap-2">${{icon}} <span class="${{n._is_archived ? 'text-gray-400' : 'text-gray-200'}}">${{n.title}}</span></div>
              <div class="text-xs text-gray-500 font-mono">${{n.id}}</div>
            </summary>
            <div class="p-3 bg-gray-800 border-t border-gray-600 text-gray-300 text-xs leading-relaxed space-y-2">
              <div><span class="text-gray-500 font-bold">Desc:</span> ${{n.description}}</div>
              ${{n.resolution && typeof n.resolution === 'object' ? `
              <div class="border-t border-gray-700 pt-2"><span class="text-blue-400 font-bold">Summary:</span> ${{n.resolution.summary || ''}}</div>
              <div><span class="text-purple-400 font-bold">Context Injected:</span> ${{n.resolution.context_injected || ''}}</div>
              ${{n.resolution.validation_status ? `<div><span class="text-green-400 font-bold">Validation:</span> ${{n.resolution.validation_status}}</div>` : ''}}
              ${{n.resolution.learnings && n.resolution.learnings.length > 0 ? `<div><span class="text-yellow-400 font-bold">Learnings:</span> <ul class="list-disc pl-4 mt-1">${{n.resolution.learnings.map(l => `<li>${{l}}</li>`).join('')}}</ul></div>` : ''}}
              ` : (n.resolution ? `<div><span class="text-green-500 font-bold">Result:</span> ${{n.resolution}}</div>` : '')}}
            </div>
          </details>
        `;
      }});
    }}

    init();
  </script>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Successfully generated modern visualization at: {out_path}")

if __name__ == "__main__":
    main()