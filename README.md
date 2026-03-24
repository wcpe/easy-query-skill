# easy-query-skill

`easy-query-skill` 是一个面向 easy-query ORM 的通用 AI agent skill 仓库，目标是在编写、修改和审查业务代码时，为 Agent 提供稳定的 easy-query 证据优先工作流与可降级的本地实现模板。

当前仓库主要包含一个核心 skill：

- `easy-query-business-hook`：用于 Repository、Service、查询构造、分页、更新删除、事务与并发相关业务代码的实现与审查，遵循 `MCP -> 本地 references -> Web` 的检索与降级顺序。

## Repository Layout

- `easy-query-business-hook/SKILL.md`：skill 主定义与执行规则
- `easy-query-business-hook/agents/openai.yaml`：UI 元信息与默认调用提示
- `easy-query-business-hook/references/`：MCP 不足时使用的本地查询、写入、事务、审查模板
- `easy-query-business-hook/scripts/validate_skill.py`：仓库自定义校验脚本

## What This Repo Is For

- 让 Agent 优先按 easy-query 源码和测试风格生成业务代码
- 在 MCP 缺失时，提供保守、可落地的本地降级模板
- 为 easy-query 相关 skill 的持续迭代提供统一仓库与版本管理

## Validation

可使用以下脚本校验 skill 结构：

```powershell
$env:PYTHONUTF8='1'
python path/to/quick_validate.py ./easy-query-business-hook
python ./easy-query-business-hook/scripts/validate_skill.py ./easy-query-business-hook/SKILL.md
```
