# AI‑Tech‑Radar
个人AI技术情报简报系统。
每日自动扫描：
1. Agent多智能体、MCP生态项目，过滤玩具Demo
2. vLLM / SGLang 推理引擎重大更新，过滤普通bugfix
3. ModelScope新开源基座模型，识别是否支持vLLM部署

输出 Markdown周报 + GitHub Pages静态网页，零服务器，GitHub Actions免费运行。
周报按“项目动态 / GitHub潜在新项目 / ModelScope新模型”分栏，时间统一显示为 `YYYY-MM-DD HH:MM`。
页面支持按内容类型和学习价值（高 / 中 / 低）组合筛选。
模型条目的用途、标签、下载量和创建时间来自 ModelScope，摘要由 `[llm]` 配置的模型根据这些来源信息生成。

## 整体文件说明
| 文件 | 作用 |
|---|---|
| `config.toml` | 配置：监控仓库、搜索条件、过滤黑名单、LLM参数 |
| `scan.py` | 主脚本：拉取GitHub/ModelScope数据、LLM研判、生成报告 |
| `.github/workflows/daily-scan.yml` | 定时Action，每天自动执行，支持手动触发 |
| `index.html` | 静态网页，GitHub Pages浏览周报 |
| `reports/` | 自动输出的周报md文件 |

## 前置准备
1. 新建**私有GitHub仓库**，仓库名：`ai‑tech‑radar`，初始化README。
> 私有仓库防止密钥泄露。

2. 生成密钥，存入仓库 Secrets（Settings → Secrets and variables → Actions）
- `GITHUB_TOKEN`：Personal access token(classic)，勾选`repo`权限，提升GitHub API配额。
- `LLM_API_KEY`：大模型key，默认使用DeepSeek‑Chat，兼容OpenAI接口。
- `MODELSCOPE_TOKEN`：ModelScope API 访问令牌。

### Secrets列表
| Secret名称 | 说明 |
|---|---|
| GITHUB_TOKEN | GitHub个人访问令牌 |
| LLM_API_KEY | LLM服务API Key |
| MODELSCOPE_TOKEN | ModelScope API访问令牌 |

## 全部文件内容

### 1. config.toml
```toml
[github]
watch_repos = [
    "vllm-project/vllm",
    "vllm-project/vllm-omni",
    "vllm-project/production-stack",
    "sglang-project/sglang",
    "modelscope/AgentScope",
    "langchain-ai/langchain",
    "mem0ai/mem0",
    "LMCache/LMCache",
    "alibaba/OpenSandbox",
    "alibaba/spring-ai-alibaba",
    "QwenLM/Qwen-Agent"
]

search_queries = [
    "topic:ai-agent stars:200..10000",
    "topic:mcp-server stars:200..10000",
    "topic:multi-agent stars:500..20000",
    "ai-agent framework stars:500..20000",
    "org:alibaba ai stars:200..20000",
    "org:QwenLM stars:200..20000"
]

[filter]
ban_keywords = ["template", "tutorial", "example", "demo-only", "lorafile"]
min_stars = 200
release_days_back = 7
# ModelScope 过滤（最近30天，下载量不少于500）
ms_days_back = 30
ms_min_downloads = 500
max_projects = 20

[llm]
api_base = "http://192.168.102.19:8082/v1"
model = "qwen3"
temperature = 0.1

[schedule]
run_interval = "daily"# AI‑Tech‑Radar
个人AI技术情报简报系统。
每日自动扫描：
1. Agent多智能体、MCP生态项目，过滤玩具Demo
2. vLLM / SGLang 推理引擎重大更新，过滤普通bugfix
3. ModelScope新开源基座模型，识别是否支持vLLM部署

输出 Markdown周报 + GitHub Pages静态网页，零服务器，GitHub Actions免费运行。
周报按“项目动态 / GitHub潜在新项目 / ModelScope新模型”分栏，时间统一显示为 `YYYY-MM-DD HH:MM`。
页面支持按内容类型和学习价值（高 / 中 / 低）组合筛选。
模型条目的用途、标签、下载量和创建时间来自 ModelScope，摘要由 `[llm]` 配置的模型根据这些来源信息生成。

## 整体文件说明
| 文件 | 作用 |
|---|---|
| `config.toml` | 配置：监控仓库、搜索条件、过滤黑名单、LLM参数 |
| `scan.py` | 主脚本：拉取GitHub/ModelScope数据、LLM研判、生成报告 |
| `.github/workflows/daily-scan.yml` | 定时Action，每天自动执行，支持手动触发 |
| `index.html` | 静态网页，GitHub Pages浏览周报 |
| `reports/` | 自动输出的周报md文件 |

## 前置准备
1. 新建**私有GitHub仓库**，仓库名：`ai‑tech‑radar`，初始化README。
> 私有仓库防止密钥泄露。

2. 生成密钥，存入仓库 Secrets（Settings → Secrets and variables → Actions）
- `GITHUB_TOKEN`：Personal access token(classic)，勾选`repo`权限，提升GitHub API配额。
- `LLM_API_KEY`：大模型key，默认使用DeepSeek‑Chat，兼容OpenAI接口。
- `MODELSCOPE_TOKEN`：ModelScope API 访问令牌。

### Secrets列表
| Secret名称 | 说明 |
|---|---|
| GITHUB_TOKEN | GitHub个人访问令牌 |
| LLM_API_KEY | LLM服务API Key |
| MODELSCOPE_TOKEN | ModelScope API访问令牌 |

## 全部文件内容

### 1. config.toml
```toml
[github]
watch_repos = [
    "vllm-project/vllm",
    "vllm-project/vllm-omni",
    "vllm-project/production-stack",
    "sglang-project/sglang",
    "modelscope/AgentScope",
    "langchain-ai/langchain",
    "mem0ai/mem0",
    "LMCache/LMCache",
    "alibaba/OpenSandbox",
    "alibaba/spring-ai-alibaba",
    "QwenLM/Qwen-Agent"
]

search_queries = [
    "topic:ai-agent stars:200..10000",
    "topic:mcp-server stars:200..10000",
    "topic:multi-agent stars:500..20000",
    "ai-agent framework stars:500..20000",
    "org:alibaba ai stars:200..20000",
    "org:QwenLM stars:200..20000"
]

[filter]
ban_keywords = ["template", "tutorial", "example", "demo-only", "lorafile"]
min_stars = 200
release_days_back = 7
# ModelScope 过滤（最近30天，下载量不少于500）
ms_days_back = 30
ms_min_downloads = 500
max_projects = 20

[llm]
api_base = "http://192.168.102.19:8082/v1"
model = "qwen3"
temperature = 0.1

[schedule]
run_interval = "daily"
