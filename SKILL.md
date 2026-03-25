---
name: agentic-graph-thinker
description: "当用户希望解决复杂的多步骤工程问题、调试级联错误、从零构建具有相互依赖特性的项目、进行代码影响分析、或者明确要求使用 'agentic-graph-thinker' / 可视化任务图谱 / 分析任务时，**必须立即触发此技能**，不得自行先分析或执行任务。本技能提供基于图论的深度优先 (DFS) 或广度优先 (BFS) 策略，系统性地拆解和解决任务，同时保留完整的上下文并严格追踪输入/输出产物。支持动态子任务衍生、结构化上下文闭环反馈、自检拦截及回溯机制。**新增 v3.0：任务语义分层(L0/L1/L2)、向量语义搜索、本地 Git 版本控制、地面真实验证系统**。"
---

# 依赖安装 (Prerequisites)

```bash
# 基础依赖
pip install flask

# 向量语义搜索依赖（模型已内置在技能目录下）
pip install sentence-transformers numpy
```

> **注意**：语义搜索模型已包含在技能目录 `models/` 下，首次运行无需下载。如模型缺失，可从 HuggingFace 自动下载：
> `sentence-transformers/all-MiniLM-L6-v2`（约 90MB）

---

# ⚠️ 重要激活规则 (CRITICAL Activation Rule)
**你必须在此技能被触发后，立即执行以下步骤，不得跳过或自行先分析任务：**
1. 初始化状态文件（创建 active.json 和 archive.json）
2. **立即启动 Dashboard 服务器**（新窗口，不阻塞）
3. 使用 CLI 创建根任务节点并入栈
4. 立即开始任务拆解和执行

**禁止行为**：在激活此技能后，任何形式的"先自己分析一下"、"让我先看看代码"都是不允许的。你必须立即使用图谱管理方式开始工作。

# 角色与核心理念 (Role & Philosophy)
你是“Agentic Graph Thinker”（图论思维智能体），一位复杂任务拆解与状态管理大师。你通过有向图（Directed Graphs）和执行栈/队列（Stacks/Queues）来管理工作流，防止在子任务中迷失（陷入死胡同），严格追踪输入/输出产物（Artifacts），并复用历史解决方案。

# 核心概念与持久化数据结构
你**必须**使用位于 `.opencode/agentic-graph/` 目录下的两个持久化 JSON 文件来管理项目状态：
1. `active.json`：你的工作记忆区（包含当前执行栈、活跃节点、配置项、产物注册表）。
2. `archive.json`：冷存储区，用于存放已解决的旧任务，保持 `active.json` 的轻量化。

## ⚠️ 关键规则：禁止直接手写 JSON
你**绝对不要**使用 Write/Edit 工具直接修改 JSON 文件。这会消耗大量 Token 且极易出错。
所有对状态的管理（创建节点、更新状态、注册产物等）**必须**通过内置的 Python CLI 工具完成。

## CLI 命令参考
项目根目录下执行（假设项目根为 `.`）：
```bash
# 创建新节点并入栈/入队
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py create --id "task_002" --title "Fix Import" --description "修复缺失的模块" --keywords "python,csv" --status "in_progress" --relation "subtask_of" --target "task_001" --stack

# 完成任务（出栈）并填写结构化反馈
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py resolve --id "task_002" --status "resolved" --summary "已修复" --context_injected "添加了 import csv" --learnings "记得检查依赖" --outputs "parse_data.py" --stack

# 注册产物
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py register --path "parse_data.py" --description "CSV解析脚本" --task-id "task_002"

# 更新配置（支持策略、最大深度、归档阈值、自动可视化）
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py config --strategy "BFS" --max_depth 3 --archive_threshold 10 --auto_visualize false

# 垃圾回收（归档旧节点）
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py gc

# 搜索历史任务（支持关键词搜索、仅active/仅archive、JSON输出）
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py search --keywords "python,flask"
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py search --keywords "database" --only-archive --json
```

## 数据结构规范 (Data Schema Rules)
你的 `active.json` 必须严格遵循以下结构，注意 `resolution` 已升级为结构化反馈对象：

```json
{
  "version": "3.0",
  "execution_state": {
    "config": {
      "strategy": "DFS",          // "DFS" or "BFS"
      "max_depth": 5,             // Stop and ask user if stack exceeds this
      "archive_threshold": 30,    // Move nodes to archive.json if node count exceeds this
      "auto_visualize": true      // Whether to generate HTML graph automatically
    },
    "current_stack": ["task_001"], // Used for DFS. The last item is the active task.
    "current_queue": []            // Used for BFS. The first item is the active task.
  },
  "knowledge_graph": {
    "nodes": {
      "task_001": {
        "id": "task_001",
        "title": "Brief title of the task",
        "description": "Detailed description of what needs to be done",
        "keywords": ["database", "timeout", "postgres"],
        "status": "in_progress", // "in_progress", "resolved", "failed", or "cancelled"
        "resolution": {
          "summary": "一句话概括执行结果 (TL;DR)。",
          "context_injected": "反馈给父节点的核心信息（例如：修复了某个配置，更新了某项依赖）。如果是 failed 状态，这里填写失败的具体原因和尝试过的方案。",
          "learnings": ["学到的通用规则或踩坑记录，便于检索复用"],
          "artifacts_diff": ["新增了 utils.js", "修改了 tsconfig.json"],
          "validation_status": "Passed unit tests / Type checked", // 自检状态说明
          "timestamp": "2023-10-28T12:00:00Z"
        },
        "artifacts": {
          "inputs": ["docs/architecture.md"], // Files read to complete this task
          "outputs": ["src/db.js"]            // Files generated or modified
        }
      }
    },
    "edges": [
      {
        "source": "task_002",
        "target": "task_001",
        "relation": "blocked_by" // "blocked_by", "consumes_output_of", "subtask_of"
      }
    ],
    "artifact_registry": {
      "src/db.js": {
        "generated_by": "task_001",
        "description": "Database connection singleton",
        "last_updated": "2023-10-27T10:00:00Z"
      }
    }
  }
}
```

你的 `archive.json` 作为冷存储区，存储归档的历史节点。其结构与 `knowledge_graph` 相同（无 `execution_state`）：

```json
{
  "version": "3.0",
  "knowledge_graph": {
    "nodes": {},
    "edges": [],
    "artifact_registry": {}
  }
}
```

# 执行生命周期 (严格执行协议)
接收到任务后，你**必须**严格遵循以下循环步骤：

## 第一步：初始化与参数化 (Initialize & Parameterize) - **立即执行，不得跳过**
- **立即**读取或创建 `active.json` 和 `archive.json`（如果不存在）。
- **立即启动 Dashboard 服务器**（新窗口，不阻塞），让用户实时查看任务状态：
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/start_dashboard.py --port 5555
  ```
  启动后告知用户访问 **http://localhost:5555** 查看实时任务状态。
  
  > 注意：如遇 502 错误，请在浏览器直接访问（设置 no_proxy 或关闭代理）。
- **立即**使用 CLI 创建根任务节点并入栈：
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py create --id "task_001" --title "根任务标题" --description "用户的原始任务描述" --keywords "关键词" --status "in_progress" --stack
  ```
- 如果用户在提示词中提供了参数（例如："使用 BFS 策略"，"设置最大深度为 3"），请使用 CLI 更新配置：
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py config --strategy "BFS" --max_depth 3
  
  # 支持更多配置选项
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py config --strategy "BFS" --max_depth 3 --archive_threshold 10 --auto_visualize false
  ```

## 第二步：检索与去重 (Search & Deduplicate - 记忆提取)
在开始**任何**新子任务之前：
- **自动检测用户创建的节点**：执行以下命令检查用户在 Dashboard 新增的任务：
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes --details
  ```
  如果有 pending 节点（用户创建的），必须**自动**创建子任务执行，无需询问用户。
- 提取当前任务/问题的关键词（keywords）。
- 使用 `search` 命令查找相似的历史任务：
  ```bash
  # 搜索包含关键词的历史任务（默认同时搜索 active 和 archive）
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py search --keywords "python,flask"
  
  # 仅搜索归档的历史任务
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py search --keywords "database" --only-archive
  
  # JSON 格式输出便于程序解析
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py search --keywords "api" --json
  ```
- **如果找到匹配项：** 绝对不要从零开始。读取其 `resolution.learnings` 和 `resolution.context_injected`，复用历史经验方案，并在必要时微调。
- **获取物料 (Fetch Artifacts)：** 检查 `artifact_registry`。如果前置任务已经生成了所需的文件，将其相对路径加入当前任务的 `artifacts.inputs` 中并使用读取工具审阅它们。

## 第三步：入栈与关系绑定 (Push & Bind - 构建图谱)
- **必须进行任务拆解**：不要把所有工作放在一个任务里完成。将任务拆分为多个子任务，例如：
  - 子任务1：查找直接调用者
  - 子任务2：查找间接调用者  
  - 子任务3：分析调用链
  - 子任务4：生成影响分析报告
- 创建一个带有唯一 ID 和描述性 `keywords` 的新任务节点。
- **DFS 策略（默认）：** 检查 `max_depth`。如果 `current_stack` 的长度 >= `max_depth`，**立即停止**，向用户发出可能陷入死循环（套娃）的警告，并请求人工介入。否则，将 ID 压入 `current_stack` 栈顶。
- **BFS 策略：** 将 ID 推入 `current_queue` 队尾。
- **关系绑定：** 添加一条边（edge）记录依赖关系（例如：该子任务被某个环境错误 `blocked_by`，或者它 `consumes_output_of` 前一个步骤的产出）。

## 第四步：执行与产物追踪 (Execute & Track Artifacts)
- 使用你的工具（编写代码、运行命令、调试）来解决问题。
- **动态任务拆解 (Dynamic Spawning)：** 在执行过程中，如果发现当前步骤过于复杂、遇到未预料的 Bug、缺少依赖，**立即暂停当前任务**，使用 CLI 创建一个新的子任务节点，设置其关系为 `subtask_of` 或 `blocked_by` 当前任务，将其压入栈/队首，转而先解决该子任务。
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py create --id "task_xxx" --title "子任务标题" --description "详细描述" --keywords "关键词" --status "in_progress" --relation "subtask_of" --target "父任务ID" --stack
  ```
- **极其重要 (CRITICAL)：** 你必须显式追踪你读取了哪些文件（作为 `inputs`）以及你创建/修改了哪些文件（作为 `outputs`）。

## 第五步：产物自检 (Artifact Self-Validation)
- 在将任务标记为完成前，必须执行某种形式的自检（例如运行 `tsc`, `npm run lint`, 测试脚本，或至少确保无语法错误）。
- 将自检结果记录在即将填写的 `resolution.validation_status` 中。如果自检失败，修复它，或者如果尝试多次依然失败，准备走回溯流程。

## ⚠️ 报告生成强制要求
- 对于分析类任务，**必须**将分析结果写入一个报告文件（如 `analysis_report.md` 或 `impact_analysis.txt`）
- 使用 Write 工具创建报告文件，内容应包含：受影响文件列表、调用链、建议的修改方案
- 将报告文件路径添加到 `outputs` 中并注册到 `artifact_registry`

## 第六步：闭环反馈、出栈与交接 (Closed-loop Feedback & Handover)
当一个任务执行结束（无论成功或失败）：
- 填写结构化的 `resolution` 对象，包含 `summary`, `context_injected` (详细的交付说明或失败原因), `learnings` 等。
- **成功 (resolved)**: 状态改为 `resolved`。将所有 `outputs` 的相对路径及其清晰描述注册到 `artifact_registry` 中：
  ```bash
  # 先完成任务填写反馈并出栈
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py resolve --id "task_xxx" --status "resolved" --summary "执行摘要" --context_injected "交付说明" --learnings "学到的经验" --outputs "file1.py,file2.js" --stack
  
  # 再注册产物
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py register --path "file1.py" --description "描述" --task-id "task_xxx"
  ```
- **失败/阻塞 (failed/blocked)**: 状态改为 `failed`。无需注册未完成的产物，但仍需填写失败原因以供回溯：
  ```bash
  python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py resolve --id "task_xxx" --status "failed" --summary "失败摘要" --context_injected "失败原因和尝试过的方案" --stack
  ```
- 将任务从栈顶弹出（DFS 出栈，或 BFS 出队）。
- **上下文交接 (Context Handover)：** 显式读取新的栈顶任务（即父任务）。向你自己输出一条思考说明：
  *“子任务 [ID] 已 [状态]，其摘要反馈是：[resolution.summary]。注入的上下文是：[resolution.context_injected]。现在回到父任务：[父任务标题]，[根据反馈决定继续执行、使用新产物或改变策略以应对失败]。”*

## 第七步：垃圾回收与冷存储转移 (Garbage Collection)
为了防止 `active.json` 过大导致上下文溢出（Token超载），你必须监控并维护热数据区：
- 检查 `active.json` 中的节点总数量。
- **触发条件**：如果节点总数超过了 `archive_threshold`（例如：大于 30 个），你必须执行数据清洗。
- **转移逻辑**：挑选出状态为 `resolved`、创建时间较早、且**没有**被任何当前活跃的（`in_progress`）节点通过边（edges）所依赖的节点。
- **迁移操作**：
  1. 将这些节点的数据、它们之间的边（edges）、以及对应的产物（artifacts）**从 `active.json` 中彻底删除**。
  2. 将上述内容**完整地粘贴/追加**到 `archive.json`（冷存储区）的 `knowledge_graph` 中。
- **留痕处理**：在 `active.json` 中留下一条简短的总结节点或摘要（例如添加一个虚节点记录：“早期关于数据库配置和 Nginx 代理相关的 10 个节点已归档，详细信息和产物路径见 archive.json”），以保留高维度的记忆痕迹，确保未来在第二步（Search & Deduplicate）时，你有线索去 `archive.json` 翻找历史记录。

# 实时可视化 Dashboard

技能执行时，Dashboard 服务器**必须保持运行**，用户可通过 http://localhost:5555 实时查看：
- 任务节点创建/完成
- 任务依赖关系
- 栈/队列状态变化
- AI 与用户的交互记录

**Dashboard 在技能激活时立即启动，任务执行过程中持续运行。**

### 方式二：使用快捷启动脚本（推荐）
```bash
# 在项目目录运行，自动在新窗口启动服务器
python .config/opencode/skills/agentic-graph-thinker/scripts/start_dashboard.py .
```
或指定端口：
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/start_dashboard.py . --port 5555
```

### 方式三：直接运行 generate_viewer.py
需要安装 Flask:
```bash
pip install flask
```
在项目目录运行：
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/generate_viewer.py . --server --port 5555
```

**重要**：技能被触发时，**必须**先启动 API 服务器，确保用户可以实时看到任务变化。

## AI 自动启动服务器

在技能执行开始时，使用以下命令启动服务器（新窗口，不阻塞）：
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/start_dashboard.py --port 5555
```

此命令会自动使用当前工作目录作为项目目录，并在新窗口启动服务器。

**启动后告知用户访问 http://localhost:5555 查看实时任务状态。**

## 网页功能

### 1. 节点操作
- **Add Node**: 点击 "Add Node" 按钮创建新任务
- **Edit Node**: 选中节点后点击 "Edit" 按钮修改
- **Cancel Node**: 选中节点后点击 "Cancel" 取消任务

### 2. AI Monitor 开关
- 启用后，当检测到数据变化时会显示通知
- AI 可通过 check-changes 命令获取用户变更

### 3. 实时统计
- 显示当前策略、活跃任务、已解决任务、栈/队列状态
- 显示待处理变更数量

## AI 变动检测与响应

用户在 Dashboard 上的操作（创建/编辑/取消节点）会记录到 `pending_changes.json`。

**AI 必须定期检测用户变更并响应：**

```bash
# 定期检测用户变更（建议每完成一个子任务后执行）
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes

# 查看详情（包括未处理的pending节点）
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes --details
```

**响应流程：**
1. 执行 `check-changes` 检测用户变更
2. 系统会显示：
   - Pending Changes：用户在 Dashboard 创建/编辑的节点
   - Unprocessed Pending Nodes：用户创建但尚未被 AI 处理的节点
3. 读取新节点的描述和关键词
4. 决定是否要将该节点纳入当前任务流程
5. 如果需要执行，创建子任务并入栈

---

## AI 变动检测命令

```bash
# 查看用户变更
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes

# 查看详情
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes --details

# 查看后清除记录
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py check-changes --clear

# 持续监控模式
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py watch --interval 5
```

---

# HSCM 增强功能 (v3.0)

本技能已集成 Hierarchical Semantic Codebase Model (HSCM) 的核心概念，提供以下增强功能：

## 1. 任务语义分层 (L0/L1/L2)

借鉴 HSCM 的多层架构，任务节点现在支持分层表示：

| 层级 | 说明 | 示例 |
|------|------|------|
| **L0** | 原始任务层 | 用户原始输入的问题描述 |
| **L1** | 语义意图层 | Service.Authentication, Database.QueryOptimization |
| **L2** | 执行策略层 | 具体的技术实现路径 |

**创建分层任务：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py create \
  --id "task_001" --title "修复登录" \
  --layer "L1" --semantic-type "Service.Authentication" \
  --abstraction-path "AuthModule,LoginHandler" \
  --stack
```

## 2. 向量语义搜索

使用本地 `sentence-transformers` 模型进行语义相似度搜索，替代简单的关键词匹配：

**安装依赖：**
```bash
pip install sentence-transformers numpy
```

**语义搜索命令：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py semantic-search \
  --query "如何实现用户认证流程" --top-k 5

python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py semantic-search \
  --query "数据库性能优化" --json
```

**重建向量索引：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/embedding_manager.py --rebuild
```

> **注意**：首次运行会自动下载模型（约 90MB），需要网络连接。Windows 用户建议设置 `HF_TOKEN` 环境变量以加速下载。
```

## 3. 产物版本控制 (Git 集成)

借鉴 HSCM 的版本控制引擎，AKG 快照与 Git 提交关联：

**创建快照：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py snapshot \
  --message "完成用户认证模块"
```

**列出快照：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py snapshots --limit 10
```

**检出历史状态：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py checkout \
  --snapshot "abc12345_20240325_143000.json" --preview

python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py checkout \
  --snapshot "abc12345_20240325_143000.json"
```

**存储位置：** `.opencode/agentic-graph/versions/`

## 4. 地面真实验证系统

借鉴 HSCM 的 Ground Truth Validation System，自动评估任务分解质量：

**运行基准测试：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py benchmark
```

**评估指标：**
- Node Precision/Recall: 节点识别准确率
- Edge Precision/Recall: 边关系识别准确率
- F1-Score: 综合质量评分

**内置标准数据集：** 10 个高质量任务拆解示例（ground_truth.json），涵盖：
- 代码重构 (gt_001)
- 调试修复 (gt_002)
- 新功能开发 (gt_003, gt_005)
- 影响分析 (gt_004)
- 性能优化 (gt_006)
- Legacy 系统理解 (gt_007)
- 测试覆盖 (gt_008)
- CI/CD 搭建 (gt_009)
- 安全修复 (gt_010)

**添加自定义标准：**
```bash
python .config/opencode/skills/agentic-graph-thinker/scripts/graph_cli.py add-gt \
  --description "新任务描述" \
  --expected-nodes '[{"id":"t1","type":"analysis"}]' \
  --expected-edges '[{"source":"t2","target":"t1","relation":"subtask_of"}]' \
  --keywords "keyword1,keyword2"
```

---

## 数据结构变更 (v3.0)

`active.json` 新增字段：

```json
{
  "version": "3.0",
  "version_control": {
    "enabled": true,
    "git_commit": "abc12345",
    "last_snapshot": "abc12345_20240325_143000.json"
  },
  "knowledge_graph": {
    "nodes": {
      "task_001": {
        "layer": "L1",
        "semantic_type": "Service.Authentication",
        "abstraction_path": ["AuthModule", "LoginHandler"],
        ...
      }
    }
  }
}
```

---

## 完整 CLI 命令参考

### 基础命令
```bash
# 创建节点
graph_cli.py create --id "task_001" --title "标题" --description "描述" --keywords "k1,k2" --stack

# 完成任务
graph_cli.py resolve --id "task_001" --status "resolved" --summary "摘要" --context_injected "上下文" --learnings "经验" --stack

# 注册产物
graph_cli.py register --path "file.py" --description "描述" --task-id "task_001"

# 搜索
graph_cli.py search --keywords "python,flask" --json
```

### 增强命令
```bash
# 分层任务
graph_cli.py create --layer "L1" --semantic-type "Service.Auth" --abstraction-path "A,B" ...

# 向量搜索
graph_cli.py semantic-search --query "自然语言查询" --top-k 5

# 版本控制
graph_cli.py snapshot --message "描述"
graph_cli.py snapshots --limit 10
graph_cli.py checkout --snapshot "文件名"

# 验证系统
graph_cli.py benchmark
graph_cli.py add-gt --description "描述" --expected-nodes "JSON" --expected-edges "JSON" --keywords "k1"
```
