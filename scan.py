import os
import json
import time
import datetime
import hashlib
from pathlib import Path
import tomllib
import requests

# ========== 加载配置 ==========
with open("config.toml", "rb") as f:
    cfg = tomllib.load(f)

GITHUB_TOKEN = cfg["github"].get("token") or os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    raise SystemExit("缺少 GITHUB_TOKEN：请在 config.toml [github].token 或环境变量中配置")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-")
GITHUB_HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept":"application/vnd.github+json"}

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)
SNAPSHOT_PATH = REPORT_DIR / ".snapshot.json"

def load_snapshot():
    try:
        value = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def mark_change(snapshot, kind, key, fingerprint):
    """Return a stable daily status and update the persisted source snapshot."""
    bucket = snapshot.setdefault(kind, {})
    previous = bucket.get(key)
    if previous is None:
        status = "新增"
    elif previous.get("fingerprint") != fingerprint:
        status = "有变化"
    else:
        status = "未变化"
    bucket[key] = {
        "fingerprint": fingerprint,
        "last_seen": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return status

def fingerprint(*values):
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

def parse_timestamp(value):
    """Parse an ISO timestamp and normalize it to an aware UTC datetime."""
    if isinstance(value, datetime.datetime):
        parsed = value
    else:
        try:
            parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)

def format_timestamp(value):
    """Format an ISO timestamp for compact report display."""
    parsed = parse_timestamp(value)
    if parsed is None:
        return str(value)
    parsed = parsed.replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M")

def format_report_datetime(value):
    """Format timestamps as clear Chinese month/day/hour/minute text."""
    compact = format_timestamp(value)
    try:
        parsed = datetime.datetime.strptime(compact, "%Y-%m-%d %H:%M")
    except ValueError:
        return compact
    return f"{parsed.year}年{parsed.month}月{parsed.day}日 {parsed.hour}点{parsed.minute:02d}分"

def github_api(url):
    resp = requests.get(url, headers=GITHUB_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def llm_judge(prompt:str):
    headers = {"Authorization":f"Bearer {LLM_API_KEY}", "Content-Type":"application/json"}
    payload={
        "model":cfg["llm"]["model"],
        "temperature":cfg["llm"]["temperature"],
        "messages":[{"role":"user","content":prompt}]
    }
    r = requests.post(f"{cfg['llm']['api_base']}/chat/completions", json=payload, headers=headers, timeout=60)
    return r.json()["choices"][0]["message"]["content"]

def fetch_watch_repo_releases(repo):
    items=[]
    try:
        data = github_api(f"https://api.github.com/repos/{repo}/releases?per_page=3")
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=cfg["filter"].get("release_days_back", 7)
        )
        for rel in data:
            published = rel.get("published_at")
            published_at = parse_timestamp(published)
            if published_at is None or published_at < cutoff:
                continue
            items.append({
                "repo":repo,
                "tag":rel["tag_name"],
                "name":rel["name"],
                "body":rel["body"][:2000],
                "published":published,
                "url":rel["html_url"]
            })
    except Exception as e:
        print(f"fetch {repo} release error {e}")
    return items

def search_new_projects(query):
    try:
        res = github_api(f"https://api.github.com/search/repositories?q={query}&sort=updated&per_page=15")
    except Exception as e:
        print(f"search {query} error {e}")
        return []
    ban = cfg["filter"]["ban_keywords"]
    out=[]
    for item in res["items"]:
        name = item["full_name"].lower()
        readme_snippet = (item.get("description") or "").lower()
        if any(b in name or b in readme_snippet for b in ban):
            continue
        if item["stargazers_count"] < cfg["filter"]["min_stars"]:
            continue
        out.append({
            "full_name":item["full_name"],
            "stars":item["stargazers_count"],
            "desc":item["description"],
            "url":item["html_url"],
            "updated":item["updated_at"]
        })
    return out

def fetch_ms_new_models():
    """扫描 ModelScope 最近指定天数新建的文本生成模型，过滤适配器和数据集。"""
    days = cfg["filter"].get("ms_days_back", cfg["filter"].get("hf_days_back", 7))
    min_dl = cfg["filter"].get("ms_min_downloads", cfg["filter"].get("hf_min_downloads", 0))
    ms_token = (
        os.environ.get("MODELSCOPE_TOKEN")
        or os.environ.get("MODELSCOPE_API_TOKEN")
        or os.environ.get("MODELSCOPE_API_KEY")
    )
    if not ms_token:
        print("fetch modelscope models skipped: missing MODELSCOPE_TOKEN")
        return []

    endpoint = os.environ.get("MODELSCOPE_ENDPOINT", "https://modelscope.cn").rstrip("/")
    # The former /api/v1/models route now returns 404.  ModelScope's current
    # public API is under /openapi/v1 and expects a Bearer token header.
    url = f"{endpoint}/openapi/v1/models"
    params = {
        # OpenAPI supports ``last_modified`` sorting; creation time is used
        # for the actual seven-day filter below. ``filter.task`` is the
        # documented filter form (plain ``task`` is silently ignored).
        "filter.task": "text-generation",
        "sort": "last_modified",
        "page_number": 1,
        "page_size": 50,
    }
    headers = {"Authorization": f"Bearer {ms_token}", "Accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"fetch modelscope models error {e}")
        return []

    # API responses have appeared as a list, Data/data, or a paged object
    # containing items/models/results. Unwrap all of these forms.
    def unwrap_models(value):
        if isinstance(value, list):
            return value
        if not isinstance(value, dict):
            return []
        for key in ("items", "list", "data", "results", "models", "Models", "Data"):
            if key in value:
                found = unwrap_models(value[key])
                if found:
                    return found
        return []

    models = unwrap_models(payload)
    if not isinstance(models, list):
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    ban_keywords = {"lora", "adapter", "lorafile", "dataset", "tutorial", "template"}
    results = []
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = (
            model.get("ModelId") or model.get("model_id") or model.get("modelId")
            or model.get("id") or model.get("name") or model.get("Path")
        )
        created_str = (
            model.get("CreatedAt") or model.get("created_at") or model.get("createdAt")
            or model.get("created")
        )
        if not model_id or not created_str:
            continue
        created = parse_timestamp(created_str)
        if created is None:
            continue
        if created < cutoff:
            continue

        raw_description = model.get("Description") or model.get("description") or ""
        description = str(raw_description).lower()
        raw_tags = model.get("Tags") or model.get("tags") or []
        tags = {
            str(tag.get("Name", tag.get("name", "")) if isinstance(tag, dict) else tag).lower()
            for tag in raw_tags
        }
        raw_task = model.get("Task") or model.get("task") or model.get("Tasks") or model.get("tasks")
        task_text = str(raw_task).lower()
        if task_text and not any(term in task_text for term in ("text-generation", "text_generation", "text generation", "llm")):
            continue
        if any(keyword in str(model_id).lower() or keyword in description or keyword in tags
               for keyword in ban_keywords):
            continue

        try:
            downloads = int(model.get("Downloads", model.get("downloads", 0)) or 0)
        except (TypeError, ValueError):
            downloads = 0
        if downloads < min_dl:
            continue

        results.append({
            "modelId": str(model_id),
            "downloads": downloads,
            "tags": sorted(tags),
            "description": str(raw_description).strip(),
            "createdAt": format_report_datetime(created),
            "_created": created,
            "url": f"https://modelscope.cn/models/{str(model_id).lstrip('/')}",
        })
    results.sort(key=lambda item: item["_created"], reverse=True)
    for item in results:
        item.pop("_created", None)
    return results[:8]

def build_report():
    week_str = datetime.datetime.now().strftime("%Y‑W%U")
    report_path = REPORT_DIR / f"{week_str}.md"
    snapshot = load_snapshot()
    change_counts = {"新增": 0, "有变化": 0, "未变化": 0}
    md_lines = []
    md_lines.append(f"# AI‑Tech‑Radar 周报 {week_str}")
    md_lines.append(f"> 生成时间：{format_report_datetime(datetime.datetime.now())}")
    md_lines.append("")

    # 1.项目动态：watch_repos 中的 Release
    md_lines.append("## 📦 项目动态")
    release_list = []
    for repo in cfg["github"]["watch_repos"]:
        rs = fetch_watch_repo_releases(repo)
        release_list.extend(rs)
    release_list.sort(key=lambda item: parse_timestamp(item["published"]) or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc))
    if not release_list:
        md_lines.append("> 最近 7 天没有符合条件的项目 Release。")
    for r in release_list:
        status = mark_change(
            snapshot,
            "releases",
            f"{r['repo']}:{r['tag']}",
            fingerprint(r["published"], r["body"]),
        )
        change_counts[status] += 1
        prompt = f"""请严格输出以下三行，不要增加其它内容：
1. **更新类型**：用具体名词说明这次 Release 属于什么变化（如新增模型支持、推理性能、调度架构、兼容性或 bug 修复）。
2. **学习价值**：只能填写高、中或低。
3. **一句话**：用 80-160 字具体说明改了什么、解决什么问题、影响哪些使用场景，以及为什么值得关注或可以忽略。

项目：{r['repo']}
版本：{r['tag']}
更新说明：{r['body'][:1200]}"""
        judge = llm_judge(prompt)
        md_lines.append(f"### [{r['repo']} {r['tag']}]({r['url']}) | {status}")
        md_lines.append(f"> 发布时间：{format_report_datetime(r['published'])}")
        md_lines.append(judge)
        md_lines.append("")

    # 2.GitHub潜在新项目
    md_lines.append("## 🔍 GitHub本周扫描潜在新项目")
    all_candidates = []
    for q in cfg["github"]["search_queries"]:
        all_candidates.extend(search_new_projects(q))
    uniq = {}
    for p in all_candidates:
        uniq[p["full_name"]]=p
    candidates = list(uniq.values())[:cfg["filter"].get("max_projects", 20)]
    for proj in candidates:
        status = mark_change(
            snapshot,
            "projects",
            proj["full_name"],
            fingerprint(proj["updated"], proj["desc"]),
        )
        change_counts[status] += 1
        prompt = f"""请严格输出以下三行，不要增加其它内容：
1. **更新类型**：用具体名词概括项目定位和技术方向。
2. **学习价值**：只能填写高、中或低。
3. **一句话**：用 100-180 字具体说明项目解决的问题、核心机制、适用对象或场景，以及是否值得关注。避免空泛形容词。

仓库信息：
repo:{proj['full_name']}
stars:{proj['stars']}
desc:{proj['desc']}"""
        j = llm_judge(prompt)
        md_lines.append(f"### [{proj['full_name']}]({proj['url']}) ⭐{proj['stars']} | {status}")
        md_lines.append(f"> 发布时间：{format_report_datetime(proj['updated'])}")
        md_lines.append(j)
        md_lines.append("")

    # 3.ModelScope新开源模型
    md_lines.append("## 🤗 ModelScope 本周新基座模型")
    ms_models = fetch_ms_new_models()
    if not ms_models:
        md_lines.append("> 本期没有获取到符合筛选条件的新模型，请检查 MODELSCOPE_TOKEN 或调整时间/下载量阈值。")
    for m in ms_models:
        status = mark_change(
            snapshot,
            "models",
            m["modelId"],
            fingerprint(m["createdAt"], m["tags"], m["description"]),
        )
        change_counts[status] += 1
        prompt = f"""请严格输出以下三行，不要增加其它内容：
1. **更新类型**：说明模型类型和主要能力（如基座、Instruct、代码或多模态）。
2. **学习价值**：只能填写高、中或低。
3. **一句话**：用 100-180 字具体说明模型解决的任务、能力特点、适用场景、规模/限制，以及是否值得关注和部署注意事项。避免空泛描述。

模型信息：
model_id:{m['modelId']}
downloads:{m['downloads']}
created_at:{m['createdAt']}
tags:{m['tags']}
description:{m['description']}
source:ModelScope"""
        j = llm_judge(prompt)
        md_lines.append(
            f"### [{m['modelId']}]({m['url']}) | 下载量:{m['downloads']} | 创建于:{m['createdAt']} | {status}"
        )
        md_lines.append(f"> 发布时间：{m['createdAt']}")
        md_lines.append(j)
        md_lines.append("")

    md_lines.insert(3, f"> 本次扫描：新增 {change_counts['新增']} 条，有变化 {change_counts['有变化']} 条，未变化 {change_counts['未变化']} 条。")
    md_text = "\n".join(md_lines)
    report_path.write_text(md_text, encoding="utf-8")
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report saved: {report_path}")
    return week_str

if __name__ == "__main__":
    build_report()
