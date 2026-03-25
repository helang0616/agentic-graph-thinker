#!/usr/bin/env python
"""
快速启动 Agentic Graph Dashboard
用法: python start_dashboard.py [--port 5555]

注意: 需要先有 active.json (通过 graph_cli.py create 创建任务)
"""
import sys
import os
import json
import subprocess
import argparse

GRAPH_DIR = ".opencode/agentic-graph"
ACTIVE_FILE = os.path.join(GRAPH_DIR, "active.json")

def ensure_active_json(project_dir):
    """确保 active.json 存在"""
    active_path = os.path.join(project_dir, ACTIVE_FILE)
    if not os.path.exists(active_path):
        os.makedirs(os.path.dirname(active_path), exist_ok=True)
        default_data = {
            "version": "3.0",
            "execution_state": {
                "config": {"strategy": "DFS", "max_depth": 5, "archive_threshold": 30, "auto_visualize": True, "embedding_enabled": False},
                "current_stack": [],
                "current_queue": []
            },
            "knowledge_graph": {"nodes": {}, "edges": [], "artifact_registry": {}},
            "version_control": {"enabled": True}
        }
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
        print(f"Created default {ACTIVE_FILE}")

def main():
    parser = argparse.ArgumentParser(description='Start Agentic Graph Dashboard')
    parser.add_argument('--port', type=int, default=5555, help='Port number')
    args = parser.parse_args()
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 当前工作目录作为项目目录
    project_dir = os.getcwd()
    
    # 确保 active.json 存在
    ensure_active_json(project_dir)
    
    # 首先生成 HTML 文件
    print("Generating HTML...")
    gen_cmd = [sys.executable, os.path.join(script_dir, 'generate_viewer.py'), project_dir]
    subprocess.run(gen_cmd, cwd=project_dir)
    
    # 检查 HTML 文件是否存在
    html_path = os.path.join(project_dir, 'agentic_graph_viewer.html')
    if not os.path.exists(html_path):
        print(f"Error: Failed to generate {html_path}")
        sys.exit(1)
    
    # 启动服务器在新窗口
    print("Starting server...")
    server_cmd = [
        sys.executable,
        os.path.join(script_dir, 'generate_viewer.py'),
        project_dir,
        '--server',
        '--port', str(args.port)
    ]
    
    CREATE_NEW_CONSOLE = 0x00000010
    subprocess.Popen(server_cmd, creationflags=CREATE_NEW_CONSOLE, cwd=project_dir)
    
    print(f"Dashboard starting at http://localhost:{args.port}")
    print("请在浏览器中打开上述地址查看")

if __name__ == '__main__':
    main()
