# 更新日志

本项目所有重要变更都记录在本文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-06-07

将原有的两个 skill 重构合并为单一的、基于可验证证据的渐进式披露 skill。

### Added（新增）

- 新增 `easy-query` skill：精简的入口 `SKILL.md`（触发条件、黄金规则、路由表、证据策略）+
  11 份内容稠密的参考文档，覆盖 Java、Kotlin（KSP）、Spring Boot：
  - 接入配置：`setup-kotlin.md`、`setup-java.md`、`setup-spring-boot.md`
  - 核心能力：`entity-mapping.md`、`query.md`、`relation-query.md`、`write.md`、`transaction.md`
  - 单元测试：`testing.md`（H2 内存库行为测试 + `.toSQL()` 断言 + SQL 监听捕获两种风格）
  - 进阶能力：`advanced.md`（聚合/分组、code-first DDL、分库分表、多数据源）
  - 速查：`api-index.md`（精确符号/包名，及 MyBatis/JPA/QueryDSL 等禁用项）
- 新增 `evals/evals.json` 及 `easy-query-workspace/` 下的评测产物（with-skill 与 baseline 对比、
  量化基准）作为质量佐证。
- 新增 `CHANGELOG.md`。

### Changed（变更）

- 每段示例代码均来自可验证来源（框架源码 `sql-test` 或官方文档），并在文末标注 `源码验证` / `官方文档`。
- 收紧 skill 的触发描述：补充 `com.easy-query` 坐标与“国产 ORM”线索，并加入明确的负向范围，
  避免被 MyBatis/JPA/jOOQ/react-query 等相近场景误触发。
- 重写 `README.md`，反映新的单一 skill 结构。

### Removed（移除）

- 移除旧 skill `easy-query-business-hook`（通篇治理流程、缺少可编译 API）。
- 移除旧 skill `easy-query-local-evidence-skill`（目录结构完整但内容为空壳模板）。

### Fixed（修复）

- 评测闭环暴露并修复了起草版本的两处错误：
  - 补充缺失的 `.limit(rows)` / `.limit(offset, rows)` 查询写法。
  - 修正 `RelationTypeEnum` 的包名为 `com.easy.query.core.enums`（原误写为 `...annotation`）。
