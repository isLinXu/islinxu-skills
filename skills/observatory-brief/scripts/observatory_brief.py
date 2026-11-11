#!/usr/bin/env python3
"""Generate an evidence-linked Markdown brief from Model Observatory snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request

BASE_URL = "https://islinxu.github.io/model-observatory/data/"
SOURCE_NAMES = ("runs.json", "tasks.json", "awesome.json", "entities.json", "conferences.json", "github.json")


def parse_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def clean_text(value, limit=180):
    text = " ".join(str(value or "").split())
    text = text.replace("[", "\\[").replace("]", "\\]")
    return text[:limit] + ("…" if len(text) > limit else "")


def safe_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value) or any(char in value for char in "<>'\""):
        return None
    parsed = urllib.parse.urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def link(label, url):
    target = safe_url(url)
    return f"[{clean_text(label)}]({target})" if target else clean_text(label)


def load_sources(names, *, data_dir=None, base_url=BASE_URL, timeout=30):
    payloads, errors = {}, {}
    for name in names:
        try:
            if data_dir is not None:
                with (Path(data_dir) / name).open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            else:
                request = urllib.request.Request(
                    urllib.parse.urljoin(base_url.rstrip("/") + "/", name),
                    headers={"User-Agent": "islinxu-skills-observatory-brief"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = json.load(response)
            if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                raise ValueError("unsupported schema_version")
            payloads[name] = payload
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    return payloads, errors


def upcoming_deadlines(payload, at, days, limit):
    rows = []
    end = at + timedelta(days=days)
    for conference in payload.get("conferences", []):
        for edition in conference.get("editions", []):
            for event in edition.get("events", []):
                moment = parse_time(event.get("utc"))
                if event.get("kind") != "paper" or event.get("tbd") or event.get("time_status") != "ok":
                    continue
                if moment is None or not at <= moment <= end:
                    continue
                rows.append((moment, conference, edition, event))
    rows.sort(key=lambda row: row[0])
    return rows[:limit]


def render_brief(payloads, errors, *, at, days=30, limit=5):
    lines = ["# Model Observatory 行动简报", "", f"生成时间：{at.isoformat()}；投稿窗口：未来 {days} 天。", ""]

    runs = payloads.get("runs.json")
    lines.extend(["## 1. 采集健康", ""])
    if runs and runs.get("runs"):
        run = runs["runs"][0]
        lines.append(f"- 最近记录：**{run.get('status', 'unknown')}**；记录于 {run.get('recorded_at', '未知')}。")
        lines.append(f"- 覆盖范围：{clean_text(runs.get('covers', '未声明'))}；该状态不证明后续构建或部署成功。")
        failed = run.get("steps_failed") or []
        missing = run.get("steps_missing") or []
        if failed or missing:
            lines.append(f"- 失败步骤：{clean_text(', '.join(map(str, failed)) or '无')}；缺失步骤：{clean_text(', '.join(map(str, missing)) or '无')}。")
        if safe_url(run.get("run_url")):
            lines.append(f"- 运行记录：{link('打开 Actions 运行', run['run_url'])}。")
    else:
        lines.append("- 没有可用运行记录；这不等于采集失败。")
    lines.append("")

    tasks = payloads.get("tasks.json")
    lines.extend(["## 2. 当前工作", ""])
    if tasks:
        counts = tasks.get("summary", {}).get("by_status", {})
        lines.append("- 状态计数：" + "、".join(f"{key} {value}" for key, value in sorted(counts.items())) + "。")
        order = {"blocked": 0, "doing": 1, "review": 2, "proposal": 3}
        active = [task for task in tasks.get("tasks", []) if task.get("status") in order]
        active.sort(key=lambda task: (order[task["status"]], task.get("updated", "")))
        for task in active[:limit]:
            reason = f"；原因：{clean_text(task['reason'])}" if task.get("reason") else ""
            lines.append(f"- `{task['status']}` `{task['slug']}`：{link(task.get('title'), task.get('url'))}{reason}")
        if not active:
            lines.append("- 当前没有行动状态任务。")
        lines.append(f"- 快照：{tasks.get('captured_at', '未知')}；`proposal` 仍需确认，不是已承诺工作。")
    lines.append("")

    awesome = payloads.get("awesome.json")
    lines.extend(["## 3. 论文清单变化", ""])
    if awesome:
        summary = awesome.get("summary", {})
        lines.append(
            f"- 快照状态 **{awesome.get('status', 'unknown')}**；实测新增 {summary.get('added', '未知')}、移出 {summary.get('removed', '未知')}；"
            f"可读 {summary.get('repos_ok', '未知')}，沿用 {summary.get('repos_stale', '未知')}，停更 {summary.get('stalled', '未知')}。"
        )
        new_samples = []
        for repo in awesome.get("repos", []):
            for item in repo.get("sample", []):
                if item.get("is_new"):
                    new_samples.append((repo, item))
        for repo, item in new_samples[:limit]:
            section = f"；分区：{clean_text(item.get('section'), 80)}" if item.get("section") else ""
            lines.append(f"- 样本新条目 `{item.get('id', '未知')}`：{link(item.get('title'), item.get('url'))}；来源 `{repo.get('id')}`{section}")
        lines.append(f"- 快照：{awesome.get('captured_at', '未知')}；样本最多展示 {limit} 条，**不等于遍历全部新增**。")
    lines.append("")

    entities = payloads.get("entities.json")
    github = payloads.get("github.json")
    lines.extend(["## 4. 项目与实体", ""])
    if entities:
        validation = entities.get("validation", {})
        lines.append(
            f"- 注册实体 {entities.get('summary', {}).get('total', '未知')}；未解析 {validation.get('unresolved', '未知')}，"
            f"未核对 {validation.get('unchecked', '未知')}，范围外 {validation.get('out_of_scope', '未知')}。"
        )
        gaps = []
        for domain, item in entities.get("coverage", {}).items():
            if item.get("available") and item.get("unregistered_count", 0):
                gaps.append((item["unregistered_count"], domain, item))
        for count, domain, item in sorted(gaps, reverse=True)[:limit]:
            lines.append(f"- `{domain}` 未登记 {count} / {item.get('total', '未知')}；这是工作队列，不是质量评分。")
        lines.append(f"- 快照：{entities.get('captured_at', '未知')}；未核对不等于断链，范围外不等于待办。")
    if github:
        repositories = github.get("repositories", [])
        owned = [repo for repo in repositories if not repo.get("is_fork") and not repo.get("archived")]
        recent = [repo for repo in owned if (parse_time(repo.get("pushed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= at - timedelta(days=7)]
        lines.append(f"- 公开非 fork 且未归档仓库 {len(owned)}；近 7 天有推送 {len(recent)}，只表示活动，不代表优先级。快照：{github.get('captured_at', '未知')}。")
    lines.append("")

    conferences = payloads.get("conferences.json")
    lines.extend(["## 5. 投稿窗口", ""])
    if conferences:
        deadlines = upcoming_deadlines(conferences, at, days, limit)
        for moment, conference, edition, event in deadlines:
            lines.append(f"- {moment.isoformat()}：`{conference.get('key')}` / `{edition.get('id')}`；{link('会议页面', edition.get('url'))}；事件 `{event.get('id')}`。")
        if not deadlines:
            lines.append("- 当前窗口内没有可确定时刻的 paper 事件。")
        lines.append(f"- 快照：{conferences.get('captured_at', '未知')}；社区目录可能与官网不同步，投稿前必须回官网复核。")
    lines.append("")

    lines.extend(["## 来源异常与边界", ""])
    if errors:
        for name, error in sorted(errors.items()):
            lines.append(f"- `{name}` 读取失败：{clean_text(error)}；对应板块未生成，不按 0 处理。")
    else:
        lines.append("- 本次所需来源均已读取；仍需遵守各来源自身的状态与样本口径。")
    lines.append("- 本简报是只读视图，不回写任务、实体或指标。")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="read snapshots from this directory instead of the network")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--at", help="UTC ISO timestamp used for windows; defaults to now")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.days < 0 or args.limit < 1:
        parser.error("--days must be non-negative and --limit must be positive")
    at = parse_time(args.at) if args.at else datetime.now(timezone.utc)
    if at is None:
        parser.error("invalid --at timestamp")
    payloads, errors = load_sources(SOURCE_NAMES, data_dir=args.data_dir, base_url=args.base_url)
    if not payloads:
        for name, error in errors.items():
            print(f"ERROR {name}: {error}")
        return 1
    output = render_brief(payloads, errors, at=at, days=args.days, limit=args.limit)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    for name, error in errors.items():
        print(f"WARNING {name}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
