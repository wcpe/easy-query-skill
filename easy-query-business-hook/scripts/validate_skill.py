#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


REQUIRED_SECTIONS = [
    "Overview",
    "Activation / Trigger",
    "Knowledge Source Priority",
    "MCP Usage Rules",
    "Source First Rules",
    "Documentation Reference Rules",
    "Web Fallback Rules",
    "Repository Rules",
    "Transaction Rules",
    "Concurrency Rules",
    "Pagination / Sorting Rules",
    "Anti-patterns",
    "Review Checklist",
    "Built-in Cases",
    "Output Constraints",
]

REQUIRED_REFERENCE_FILES = [
    "references/query-patterns.md",
    "references/write-patterns.md",
    "references/transaction-patterns.md",
    "references/crud-module.md",
    "references/code-first.md",
    "references/review-checks.md",
]


RULE_COVERAGE = {
    "优先使用 EasyQuery MCP": [
        r"先查 EasyQuery MCP",
        r"MCP优先",
    ],
    "源码优先于文档": [
        r"源码优先",
        r"源码、API、测试行为高于文档",
        r"源码.*高于.*文档",
    ],
    "文档仅作参考": [
        r"文档只能作为参考",
        r"文档仅.*参考",
    ],
    "Web 仅兜底": [
        r"最后才允许 Web 搜索",
        r"Web 结果只作为补充",
    ],
    "Bukkit/游戏服务端主线程禁查库": [
        r"Bukkit",
        r"主线程.*数据库 I/O|主线程.*查库",
    ],
    "Repository 层使用 ORM": [
        r"Repository 层负责.*EasyQuery DSL|Repository 层负责.*ORM",
    ],
    "Service 层不得泄漏 ORM DSL": [
        r"Service 层不得随意泄漏.*ORM DSL",
        r"Service.*不要.*DSL",
    ],
    "分页查询必须关注稳定排序": [
        r"稳定排序",
        r"确定性排序",
    ],
    "动态排序要白名单": [
        r"动态排序.*白名单",
        r"白名单.*排序",
    ],
    "更新/删除必须检查条件完整性": [
        r"更新/删除条件.*完整",
        r"条件完整性",
        r"无 `WHERE` 保护",
    ],
    "先查后改需要并发保护分析": [
        r"先查后改",
        r"并发保护",
    ],
    "事务边界要明确": [
        r"事务边界",
        r"Service 层",
    ],
    "必须输出可落地代码": [
        r"可直接落地",
        r"可落地代码",
    ],
}


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Skill file not found: {path}")
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict | None:
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def find_headings(text: str) -> list[str]:
    return [m.group(2).strip() for m in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.M)]


def has_section(headings: list[str], title: str) -> bool:
    return any(h == title for h in headings)


def get_section_body(text: str, title: str) -> str:
    pattern = rf"^##\s+{re.escape(title)}\s*$"
    match = re.search(pattern, text, re.M)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", text[start:], re.M)
    if not next_match:
        return text[start:]
    return text[start:start + next_match.start()]


def require_patterns(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.I | re.M) for pattern in patterns)


def parse_code_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:[^\n`]*)\n(.*?)```", text, re.S)


def count_bullets(section_body: str) -> int:
    return len(re.findall(r"^\s*-\s+", section_body, re.M)) + len(re.findall(r"^\s*\d+\.\s+", section_body, re.M))


def count_case_headers(text: str) -> int:
    return len(re.findall(r"^###\s+[A-Z]{2}-\d{2}\s+", text, re.M))


def main() -> int:
    default_skill = Path(__file__).resolve().parents[1] / "SKILL.md"
    skill_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_skill
    skill_dir = skill_path.parent
    text = read_text(skill_path)
    headings = find_headings(text)
    frontmatter = parse_frontmatter(text)

    errors: list[str] = []
    warnings: list[str] = []

    if frontmatter is None:
        errors.append("缺少标准 YAML frontmatter，或 frontmatter 格式无效。")
    else:
        frontmatter_name = frontmatter.get("name")
        frontmatter_description = frontmatter.get("description")
        if not isinstance(frontmatter_name, str) or not re.fullmatch(r"[a-z0-9-]{1,64}", frontmatter_name):
            errors.append("frontmatter 的 name 必须是 1-64 位小写字母、数字或连字符。")
        if not isinstance(frontmatter_description, str) or not frontmatter_description.strip():
            errors.append("frontmatter 的 description 不能为空。")

    openai_yaml_path = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml_path.exists():
        errors.append("缺少 agents/openai.yaml。")
    else:
        openai_text = read_text(openai_yaml_path)
        if "display_name:" not in openai_text or "short_description:" not in openai_text:
            errors.append("agents/openai.yaml 缺少 display_name 或 short_description。")
        if "default_prompt:" not in openai_text:
            warnings.append("agents/openai.yaml 尚未设置 default_prompt。")

    for rel_path in REQUIRED_REFERENCE_FILES:
        if not (skill_dir / rel_path).exists():
            errors.append(f"缺少 references 文件: {rel_path}")

    for section in REQUIRED_SECTIONS:
        if not has_section(headings, section):
            errors.append(f"缺少必要章节: {section}")

    for label, patterns in RULE_COVERAGE.items():
        if not require_patterns(text, patterns):
            errors.append(f"缺少重点规则覆盖: {label}")

    built_in_body = get_section_body(text, "Built-in Cases")
    anti_body = get_section_body(text, "Anti-patterns")
    review_body = get_section_body(text, "Review Checklist")
    output_body = get_section_body(text, "Output Constraints")
    docs_body = get_section_body(text, "Documentation Reference Rules")
    priority_body = get_section_body(text, "Knowledge Source Priority")

    if count_case_headers(text) < 20:
        errors.append("内置用例数量不足，建议至少 20 个案例标题。")

    if built_in_body.count("正例模板") < 15:
        errors.append("内置用例中的正例模板不足。")

    if built_in_body.count("反例模板") < 10:
        errors.append("内置用例中的反例模板不足。")

    if count_bullets(anti_body) < 10:
        errors.append("Anti-patterns 反模式条目不足。")

    if count_bullets(review_body) < 12:
        errors.append("Review Checklist 检查项不足。")

    if "冲突" not in docs_body or "源码" not in docs_body:
        errors.append("Documentation Reference Rules 未明确说明源码/文档冲突裁决。")

    if "1." not in priority_body or "2." not in priority_body or "3." not in priority_body or "4." not in priority_body:
        errors.append("Knowledge Source Priority 未给出明确检索顺序。")

    if "通用 ORM 工程规则" not in text and "不是 EasyQuery" not in text:
        errors.append("未区分 EasyQuery 源码事实与通用 ORM 工程规则。")

    if "不要大段照抄源码" not in output_body and "不要大段复制" not in output_body:
        errors.append("Output Constraints 未限制源码抄写。")

    if "可落地代码" not in output_body and "可直接落地" not in output_body:
        errors.append("Output Constraints 未要求输出可落地代码。")

    code_blocks = parse_code_blocks(text)
    total_code_lines = sum(len(block.splitlines()) for block in code_blocks)
    longest_block = max((len(block.splitlines()) for block in code_blocks), default=0)

    if len(code_blocks) > 12:
        warnings.append("代码块较多，检查是否过度使用长示例。")

    if total_code_lines > 260:
        warnings.append("代码块总行数较高，检查是否过度复制源码或示例。")

    if longest_block > 45:
        warnings.append("存在过长代码块，检查是否需要改为抽象模板。")

    if built_in_body.count("检查点") < 15:
        warnings.append("Built-in Cases 的检查点偏少，建议继续补齐。")

    if "MCP" not in text or "Web" not in text:
        errors.append("缺少 MCP 或 Web 兜底说明。")

    if errors:
        print("VALIDATION FAILED")
        for item in errors:
            print(f"- ERROR: {item}")
        for item in warnings:
            print(f"- WARN: {item}")
        return 1

    print("VALIDATION PASSED")
    print(f"- Skill file: {skill_path}")
    if frontmatter is not None:
        print(f"- Skill name: {frontmatter.get('name')}")
    print(f"- OpenAI UI config: {'present' if openai_yaml_path.exists() else 'missing'}")
    print(f"- Reference files: {len(REQUIRED_REFERENCE_FILES)} required")
    print(f"- Case headers: {count_case_headers(text)}")
    print(f"- Code blocks: {len(code_blocks)}")
    print(f"- Total code lines: {total_code_lines}")
    print(f"- Longest code block lines: {longest_block}")
    for item in warnings:
        print(f"- WARN: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
