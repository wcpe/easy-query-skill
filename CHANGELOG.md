# 更新日志

本项目所有重要变更都记录在本文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.2.0] - 2026-06-07

继续按"官方文档梳理 + 源码查证"补齐剩余高级功能。

### Added（新增）

- 新增 `references/computed-properties.md`：数据库计算/派生列——`@Column(sqlExpression =
  @ColumnSQLExpression(...))` 简单表达式、`@Column(sqlConversion = ColumnValueSQLConverter.class)`
  复杂表达式（CASE/函数/SQL 层加密）、跨表统计子查询列（`autoSelect=false`）。
- 新增 `references/caching.md`：`sql-cache` 模块——`EasyCacheClient` 的 `kvStorage`/`allStorage`、
  `@CacheEntitySchema` + `CacheKvEntity`/`CacheAllEntity`、装配与失效（`EasyCacheBootstrapper` +
  `addTriggerListener`）、一致性模式（逻辑删除延迟双删 / CDC）。

### Changed（变更）

- `references/dto-query.md` 的动态排序补全为已验证的 `ObjectSort` + `ObjectSortBuilder` 完整示例。
- `references/entity-mapping.md` 新增 `@ValueObject` 值对象（扁平嵌套列）小节。
- `references/advanced.md` 新增：数据库函数生成主键 `GeneratedKeySQLColumnGenerator`、行为开关
  `EasyBehaviorEnum`（`.configure(...)`，含 smart-predicate 条件下推）。
- `references/interceptors.md` 新增操作审计日志小节（字段级用 `EntityInterceptor`；完整操作日志的
  `DatabaseInterceptor` 方案标注"未在当前源码定位到，按版本确认"）。
- 同步更新 `SKILL.md` 路由表与 `api-index.md` 速查。

## [1.1.0] - 2026-06-07

补齐高级功能内容，全部对照官方文档（easy-query-doc）梳理、再用框架源码查证。

### Added（新增）

- 新增 `references/interceptors.md`：拦截器体系（`EntityInterceptor` / `PredicateFilterInterceptor` /
  `UpdateSetInterceptor` / `UpdateEntityColumnInterceptor`），含**审计字段自动填充**与**多租户过滤**示例、
  注册方式（Spring `@Component` 或 `applyInterceptor`）、`@UpdateIgnore` / `@InsertIgnore`、临时关闭与
  `ProtectedInterceptor`。
- 新增 `references/type-mapping.md`：字段↔列映射扩展——值转换器 `ValueConverter`/`ValueAutoConverter`
  （枚举、JSON）、`JdbcTypeHandler`、列加密 `@Encryption` + `EncryptionStrategy`。
- 新增 `references/dto-query.md`：基于请求对象的查询——`whereObject` + `@EasyWhereCondition`（含
  `Condition` 取值与区间 `propName`）、动态排序 `ObjectSort`、关联字段扁平映射 `@NavigateFlat`。
- `references/advanced.md` 扩充：自定义主键生成器 `PrimaryKeyGenerator`、数据追踪差异更新
  `TrackManager` / `.asTracking()` / `@EasyQueryTrack`、CTE（`.toCteAs()` / `EntityCteViewer`）、
  JDBC 监听器 `JdbcExecutorListener`（慢 SQL）、内置 SQL 函数指引。

### Changed（变更）

- `SKILL.md` 路由表新增 interceptors / type-mapping / dto-query 三条，并更新 advanced 覆盖范围。
- `references/api-index.md` 新增「Extensions」速查段；`references/entity-mapping.md` 补充
  `@Encryption` / `@UpdateIgnore` / `@InsertIgnore` / `@ValueObject` 注解与 `@Column` 的
  `conversion` / `typeHandler` / `primaryKeyGenerator` 属性。

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
