---
name: easy-query-business-hook
description: 在编写、修改或审查使用 easy-query 的业务代码时使用。适用于 Repository、Service、查询构造、分页、动态条件、更新删除、事务与并发相关实现。要求先查询 MCP 中的 easy-query 源码、测试和示例；若 MCP 无足够证据，再降级到本 skill 的本地 references 文档和例子；若仍不足，再搜索 Web 官方资料。输出必须优先遵循源码中已证实的写法，禁止仅凭 ORM 通用经验臆造 easy-query API。
---

# EasyQuery Business Hook Skill

## Overview
本 Skill 用于在真实业务代码里自动 hook easy-query 的实现需求。目标不是复述概念，而是帮助 Agent 在 Repository、Service 与调用层中按 easy-query 已有源码风格落地查询、写入、分页、事务与并发相关代码。

本 Skill 的核心立场是：`MCP 优先、源码优先、本地 references 降级、Web 兜底`。Agent 必须先确认事实，再输出代码或结论；没有证据时可以给出工程建议，但必须明确标注为“通用 ORM 工程规则”，不能伪装成 EasyQuery 源码事实。

本 Skill 适用范围：
- 业务需求驱动的 easy-query 代码生成、改写、补全与审查
- EasyQuery 查询与写入 DSL 使用
- `EasyQueryClient` / `easyEntityQuery` 入口分析
- `Queryable` / `Insertable` / `Updateable` / `Deletable` / `Transaction` 相关实现
- Repository / Service 边界设计
- 分页、排序、动态条件、批量写、乐观锁、事务、一致性、异常语义审查

本 Skill 的非目标：
- 不替代源码阅读
- 不要求 Agent 记忆整套 EasyQuery API
- 不把外部实践文档当成框架强制规范
- 不大段复制源码、测试或官方文档到最终输出

证据分级：
- `A`：EasyQuery MCP 中的源码、API、测试、示例、官方文档镜像
- `B`：本地源码中的公共 API、实现、测试
- `C`：本地文档、FAQ、实践页、迁移说明
- `D`：Web 官方资料、官方仓库、可信技术文档
- `X`：通用 ORM 工程规则，不是 EasyQuery 源码专属事实

## Activation / Trigger
在以下场景激活本 Skill：
- 用户明确提到 EasyQuery、`easyEntityQuery`、`EasyQueryClient`
- 用户希望“按 easy-query 源码里的写法”生成或修改业务代码
- 用户要生成或重构 Repository、查询逻辑、分页逻辑、事务逻辑、批量写逻辑
- 用户要审查并发、一致性、N+1、全表扫描、无条件更新/删除、动态排序风险
- 用户要排查“查询不对、更新 0 行、事务没生效、版本号冲突、分页重复/丢失、排序字段不安全、先查后改失效”
- 用户要判断文档写法、示例写法、项目写法与源码行为是否一致

如果任务不是 EasyQuery 相关，或者项目根本没有 EasyQuery 上下文，不要强行套用本 Skill。

## Knowledge Source Priority
知识获取顺序必须固定，不能颠倒：

1. 先查 EasyQuery MCP。
2. 再查本 skill 的 `references/` 目录中的本地例子与模式文档。
3. 必要时再查当前工作区本地源码目录或用户项目源码目录。
4. 最后才允许 Web 搜索。

落地时采用如下检索顺序：

1. 先找公共入口与公开 API。
2. 再找测试用例与示例，确认行为边界。
3. MCP 不足时，优先读取本 skill 的 `references/query-patterns.md`、`references/write-patterns.md`、`references/transaction-patterns.md`、`references/crud-module.md`、`references/code-first.md`、`references/review-checks.md`。
4. 仍有歧义时，再读实现类或当前项目中的适配代码，确认异常、默认值、保护机制、事务语义。
5. 本地 references 与源码都不足时，才去 Web 搜索。

裁决规则：
- `A/B` 级证据高于 `C/D` 级证据。
- 源码、API、测试行为高于文档描述。
- 文档示例与源码冲突时，以源码/API/测试为准。
- Web 结果永远不能覆盖 MCP 或本地源码事实。

## MCP Usage Rules
如果运行环境可访问 EasyQuery MCP，先做这些事：

1. 查询 EasyQuery 相关源码、API 摘要、测试、示例、文档镜像。
2. 优先读取公共入口、核心接口、异常定义、测试文件。
3. 对关键结论至少找到一个源码/API 落点，最好再找一个测试或示例佐证。
4. 如果 MCP 中只有知识卡片，没有源码索引，要明确写出“只有参考知识，没有源码级证据”，不能把知识卡片当成最终事实。
5. 如果 MCP 与本地源码都可用，但两者不一致，以可验证的源码/API/测试行为为准。

MCP 结论的使用方式：
- 可以提炼规则、边界、推荐路径、危险写法。
- 不要大段复制 MCP 返回的源码、文档原文或测试内容。
- 最终输出应保留“证据结论”，不要把 Skill 写成源码摘抄本。

MCP 无法充分回答时，按以下顺序降级：
1. 先读本 skill 的 `references/` 文件，优先找与当前任务最接近的写法模板。
2. 如果 `references/` 只有经验规则、没有源码级证据，要明确标注“这是本地参考模式，不是源码实锤”。
3. 只有 references 与当前项目代码都不足时，才进入 Web 搜索。

## Source First Rules
分析本地源码时，优先顺序如下：

1. 入口类：先找 `EasyQueryClient`、项目中的 `easyEntityQuery` 包装入口。
2. 查询接口：重点看 `Query`、`Filterable*`、`Orderable*`、`PageAble`。
3. 写入接口：重点看 `Insertable`、`Updateable`、`Deletable`、`SQLExecuteExpectRows`。
4. 并发/版本：重点看 `@Version`、`ignoreVersion`、`withVersion`、相关测试。
5. 事务：重点看 `Transaction`、`beginTransaction`、连接管理器与事务接入层。
6. 测试：优先找版本、删除、分页、批量、冲突写入、事务相关测试。

已知的源码优先规则：
- `EasyQueryClient` 是核心公共入口，常见入口包括 `queryable`、`insertable`、`updatable`、`deletable`、`beginTransaction`。
- `whereById`、`whereByIds` 是主键查询优先入口。
- `whereObject` 存在明确边界：源码注释已说明“仅支持主表的动态对象查询”。
- 动态查询默认严格模式：`DynamicQueryStrategy.dynamicMode()` 默认返回 `STRICT`。
- 更新与删除存在无 `WHERE` 保护；不能把“源码会拦截”当成可以偷懒的理由。
- 物理删除默认受保护，通常需要显式 `allowDeleteStatement(true)` 才允许执行。
- 版本控制的当前公开写法应优先认 `ignoreVersion` / `withVersion`，不要优先相信旧文档写法。
- `executeRows(expectRows, msg, code)` 在不在事务内时会自动开一个事务来保证单次断言操作的原子性，但这不等于业务级事务设计已经完成。

源码提炼时必须输出以下四类信息：
- 事实：明确存在的入口、默认行为、异常、保护机制
- 边界：哪些写法只适合主表、只适合单表、只适合某类方言或测试场景
- 推荐：源码中更稳定、更常见、测试覆盖更多的路径
- 风险：会抛错、会退化、会产生歧义、会隐藏并发问题的用法

## Documentation Reference Rules
本地 references 文档与例子只能作为参考层，文档仅作参考，主要用途如下：
- 补术语、背景、设计意图
- 补本 skill 维护者沉淀的推荐写法、常见 FAQ、降级模板
- 补迁移说明、实践经验、场景解释
- 辅助定位可能的入口名、概念名、章节名

文档使用规则：
- `references/` 文档不能凌驾于源码之上。
- 没有源码或测试支撑的 references 内容，只能写成“参考建议”，不能写成硬规则。
- 本地 references 与源码冲突时，必须明确写出冲突点，并写明“以源码/MCP 为准”。

本 skill 自带的本地降级文件如下：
- `references/query-patterns.md`：查询、分页、动态条件、排序相关写法
- `references/write-patterns.md`：插入、更新、删除、受影响行数、版本控制相关写法
- `references/transaction-patterns.md`：事务边界、回滚、跨 Repository 协调相关写法
- `references/crud-module.md`：基础 CRUD 模块、Repository / Service 骨架与调用方式
- `references/code-first.md`：Code First 实体建模、字段注解、初始化与迁移注意事项
- `references/review-checks.md`：代码评审与风险扫描时的重点检查项

当前已知冲突与降级处理：
- 文档中的 `noVersionIgnore` / `noVersionError` 说法存在历史痕迹；当前源码与测试公开写法应优先使用 `ignoreVersion` / `withVersion`。
- 文档中的“编译期 Repository”实践页属于实践方案，不应被误判为 EasyQuery 核心内建 Repository 抽象。
- 文档里的分页、排序、DTO 查询示例可作为入口参考，但最终行为仍要回到源码与测试确认。

## Web Fallback Rules
只有在以下条件同时满足时，才允许 Web 搜索：
- MCP 没有 EasyQuery 相关源码/测试/文档镜像，或者无法访问
- 本地源码和本地文档都不足以回答用户问题
- 用户问题必须依赖额外的官方资料、迁移说明、版本说明或特定方言行为

Web 使用规则：
- 优先官方仓库、官方文档、官方示例、可信发布说明。
- 先解释“MCP 和本地 references 为什么不足”，再引用 Web 结果。
- Web 结果只作为补充，不能覆盖本地源码事实。
- 如果 Web 与源码冲突，必须回退到源码/MCP 结论。

## Repository Rules
以下大部分属于 `X 级` 通用 ORM 工程规则，不是 EasyQuery 核心源码强制机制；只有与 EasyQuery 公共入口直接相关的部分才算 `A/B` 级事实。

Repository 规则：
- Repository 层负责持有 EasyQuery DSL、表实体映射、查询组装、写入执行。
- Repository 可以返回领域需要的聚合结果、分页结果、DTO 投影结果，但不要把底层 ORM DSL 直接泄漏到 Service 以上。
- 主键查询优先使用 `whereById` / `whereByIds`，唯一键查询优先使用明确条件加 `singleOrNull`。
- 只需要判断存在性时优先 `any()` / `count()`，不要先 `toList()` 再在内存里判断。
- `whereObject` 只适合主表 DTO 条件拼接；复杂跨表业务条件、分支条件、权限条件应显式写 DSL。
- 方言相关的 `onConflictThen`、批量写、软删除、版本更新应封装在 Repository 内，不要把方言细节扩散到 Service。

Service 规则：
- Service 层负责业务语义、事务边界、并发语义、跨 Repository 协调、异常翻译。
- Service 层不得随意泄漏 ORM DSL 或 EasyQuery DSL 到上层调用方。
- Service 如果必须使用 EasyQuery 细节，应说明这是临时工程折中，并优先收敛回 Repository。

Command / Listener / Scheduler 规则：
- `X 级` 通用工程规则：Command、Listener、Scheduler 应优先调用 Service，而不是直接拼接 ORM DSL。
- 若项目上下文是 Bukkit / Spigot / Paper / 游戏服务端，禁止主线程执行数据库 I/O；这不是 EasyQuery 专属事实，而是项目线程模型硬约束。

API 边界规则：
- 不要把 ORM Entity 直接泄漏到开放 API、Controller 返回体、消息体。
- Entity 变更字段、逻辑删除字段、版本字段、内部审计字段不应被上层随意感知。

## Transaction Rules
事务设计遵循“业务边界优先，框架能力配合”的原则。

硬规则：
- 事务边界默认放在 Service 层，不放在 Controller、Command、Listener、Repository 调用点四处分散开启。
- 如果项目已接入 Spring / Solon 等事务体系，优先参与宿主事务，不要无理由叠加手工事务。
- 没有宿主事务时，可以使用 `beginTransaction()` 明确包裹单服务或跨 Repository 的一致性操作。
- 跨多个 Repository 的写操作要么明确在同一事务内，要么明确说明为何允许最终一致。
- 远程调用、长时间等待、重计算不要放在长事务里。
- 只读查询默认不要无理由开事务，除非需要锁、隔离级别、强一致观察窗口。
- `executeRows(expectRows, msg, code)` 的自动事务只保证“单次断言写入”的原子性，不能替代完整业务事务编排。

回滚规则：
- 领域校验失败、并发断言失败、唯一键冲突、跨仓储任何一步失败时，默认应让事务整体回滚。
- 如果业务要求部分成功，必须显式说明补偿策略，不能把“部分成功”当默认行为。

不应开事务的场景：
- 纯查询、缓存预热、报表导出、分页列表、无需原子性的读操作
- 用户交互链路中包含远程 RPC、文件上传、长时间阻塞等待
- 大批量离线处理但没有分批提交策略

## Concurrency Rules
并发审查时，先判断当前操作属于哪一类：

1. 单语句条件更新/删除
2. 先查后改
3. 唯一键幂等写入
4. 批量写或批量补偿
5. 版本号控制或断言行数控制

并发规则：
- 能用单条 SQL 表达业务约束时，优先单条 SQL，不要先查再改。
- 先查后改必须分析丢失更新、重复创建、脏覆盖、ABA 风险。
- 需要版本控制时优先使用 `@Version` 与 `withVersion`；`ignoreVersion` 只能在有明确理由时使用。
- 更新/删除返回 `0` 行时，必须判断语义：未命中、已被他人修改、版本过期、状态已变化、条件不完整，不能直接吞掉。
- 需要“恰好更新 1 行”语义时，优先使用受影响行数断言，并把失败视为并发或状态异常。
- 唯一键天然适合做幂等防线；如果依赖 `onConflictThen`，要确认方言支持、冲突列是否完整、回写语义是否符合业务。
- 批量写要区分“全成功”“部分成功”“驱动不返回精确行数”三种语义，不要假设所有 JDBC 驱动都能给出精确批量行数。
- 如果上下文是游戏服务端或其他单线程主循环场景，数据库 I/O 必须异步化；这是 `X 级` 项目规则。

## Pagination / Sorting Rules
分页与排序审查要同时看“结果正确性”和“性能可控性”。

硬规则：
- 所有分页查询都必须有确定性排序；如果业务排序字段不唯一，应追加稳定的二级排序键，例如主键。这条是 `X 级` 通用工程规则，不是 EasyQuery 自动保证。
- 用户可控的动态排序必须做字段白名单，不要把前端传来的字段名直接喂给 `orderByObject` 或自定义排序 DSL。
- EasyQuery 默认动态模式是严格模式，但严格模式不等于业务白名单已经完善；仍然要在应用层约束允许排序的字段集合。
- 深分页优化是性能策略，不是结果正确性的替代品；没有稳定排序的深分页仍然可能重复或漏数。
- 如果已经知道总数，可以使用 `toPageResult(pageIndex, pageSize, total)` 避免重复 `count`。
- 不要先全量查出再在内存做排序、过滤、分页。
- 多表联查分页时，要审查排序列是否可索引、是否会导致不稳定翻页或高代价排序。

## Anti-patterns
- 把文档示例当成最终事实，不核对源码和测试
- 看到 `whereObject` 就把所有动态查询都塞进去，不区分主表与复杂跨表场景
- 把 `firstOrNull` 用在“唯一键必须唯一”的业务语义上
- 没有稳定排序就直接分页
- 动态排序不做白名单，只按前端字段名透传
- 更新或删除条件不完整，或者依赖隐式条件侥幸通过
- 物理删除时随手打开 `allowDeleteStatement(true)`，却没有额外审查条件完整性
- 默认忽略版本号，把 `ignoreVersion()` 当成常规写法
- 先查后改但没有事务、版本号、唯一键或受影响行数断言
- 批量写默认假设“全部成功且受影响行数精确”
- Service 层直接向 Controller / Command 暴露 ORM DSL
- Command / Listener / Scheduler 直接访问 Repository 并拼接复杂查询
- 在 Bukkit / 游戏服主线程执行数据库 I/O
- 先查全量列表再在内存里过滤、去重、排序、分页
- 把 ORM Entity 直接返回给 API 层或消息层
- 本地证据不足时直接拍脑袋给结论，不标注不确定性

## Review Checklist
执行代码审查、方案审查、故障分析时，至少逐项检查：

1. 当前结论属于 `A/B/C/D/X` 哪个证据等级。
2. 是否先查了 EasyQuery MCP；如果没有，是否说明了原因。
3. 是否先查了公共入口、测试、实现，再看文档。
4. 查询场景是否正确选择了 `whereById`、`singleOrNull`、`firstOrNull`、`count`、`any`。
5. `whereObject` 是否被误用于复杂跨表业务逻辑。
6. 动态排序是否做了字段白名单与方向校验。
7. 分页是否有稳定排序，是否可能重复/漏数。
8. 更新/删除条件是否完整，是否存在无 `WHERE` 或弱条件风险。
9. 物理删除是否显式评审了 `allowDeleteStatement(true)` 的必要性。
10. 写操作是否需要 `@Version`、`withVersion`、受影响行数断言或唯一键保护。
11. 先查后改是否分析了并发窗口。
12. 事务边界是否放在 Service，而不是随处散落。
13. 是否错误依赖了 `executeRows(expectRows...)` 的自动事务来代替完整业务事务。
14. 是否存在 N+1、全表扫描、内存过滤分页、无索引排序等性能风险。
15. 是否把 Entity、ORM DSL、方言细节泄漏到了不该泄漏的层。
16. 最终输出是否给出可落地代码、风险说明、必要测试点，而不是只有空泛建议。

## Built-in Cases
以下内置用例是 Skill 自带的抽象模板，不依赖外部源码文件，可直接用于代码生成、代码审查和故障分析。

### BQ-01 按 ID 查询单条
- 正例模板：`easyEntityQuery.queryable(User.class).whereById(id).singleOrNull();`
- 反例模板：`queryable(User.class).toList().stream().filter(x -> x.getId().equals(id)).findFirst()`
- 检查点：主键查询优先走 `whereById`；若业务语义是“最多一条”，优先 `singleOrNull`。

### BQ-02 按唯一键查询
- 正例模板：`queryable(User.class).where(u -> u.email().eq(email)).singleOrNull();`
- 反例模板：`firstOrNull()` 被用于邮箱、手机号、业务单号等本应唯一的字段。
- 检查点：唯一语义要显式断言“至多一条”。

### BQ-03 条件列表查询
- 正例模板：`queryable(Order.class).where(o -> { o.status().eq(status); o.shopId().eq(shopId); }).toList();`
- 反例模板：先查全量订单，再用 Java Stream 过滤状态。
- 检查点：过滤条件尽量下推到 SQL。

### BQ-04 exists / count 查询
- 正例模板：`queryable(User.class).where(u -> u.username().eq(name)).any();`
- 正例模板：`queryable(Task.class).where(t -> t.state().eq(state)).count();`
- 反例模板：`toList().size() > 0`
- 检查点：只判断存在性或数量时，不要拉全量数据。

### PG-01 正常分页查询
- 正例模板：`queryable(User.class).where(...).orderBy(u -> u.id().asc()).toPageResult(pageIndex, pageSize);`
- 反例模板：没有任何排序直接分页。
- 检查点：分页必须伴随明确排序。

### PG-02 稳定排序分页
- 正例模板：`orderBy(u -> { u.createTime().desc(); u.id().desc(); })`
- 反例模板：只按 `createTime` 排序，而 `createTime` 不是唯一列。
- 检查点：业务排序字段不唯一时，追加主键或唯一键做稳定次序。

### PG-03 动态排序白名单
- 正例模板：只允许 `id/createTime/status` 进入排序映射，再转成 `orderByObject` 或显式 DSL。
- 反例模板：前端传 `sort=deleted desc,1=1` 或任意字段名后直接透传。
- 检查点：严格模式只能减少非法字段，不能替代业务白名单。

### PG-04 防止无序分页重复/丢失
- 正例模板：在翻页接口里固定排序键集合，并把排序规则写进 Repository。
- 反例模板：第一页按默认顺序，第二页按前端临时字段，导致重复或漏数。
- 检查点：分页结果的一致性依赖排序稳定性。

### DC-01 可选参数条件拼接
- 正例模板：`where(q -> { q.name().like(!isBlank(name), name); q.state().eq(state != null, state); })`
- 反例模板：参数为空时仍拼上宽泛条件或错误条件。
- 检查点：可选参数条件要显式 gated。

### DC-02 空条件处理
- 正例模板：先校验请求至少命中一个业务过滤维度，必要时拒绝执行宽表扫描。
- 反例模板：所有条件都为空时直接返回全表数据。
- 检查点：空条件是否符合业务与性能边界。

### DC-03 多条件组合
- 正例模板：明确 `AND/OR` 组合边界，复杂逻辑回退到显式 DSL。
- 反例模板：把复杂业务分支全部丢进动态 DTO 条件对象，希望框架自动猜对。
- 检查点：复杂业务谓词宁可显式，不要过度抽象。

### DC-04 时间范围过滤
- 正例模板：显式定义开始/结束边界、时区语义、闭区间/半开区间。
- 反例模板：前端传时间范围后直接拼字符串或遗漏一侧边界。
- 检查点：范围查询要同时审查索引与时区语义。

### WR-01 插入
- 正例模板：`easyEntityQuery.insertable(entity).executeRows();`
- 反例模板：插入前先全表查重，再不设唯一约束直接插入。
- 检查点：插入语义是否依赖唯一键、默认值、回填或事务。

### WR-02 条件更新
- 正例模板：`updatable(User.class).setColumns(...).where(u -> u.id().eq(id)).executeRows();`
- 反例模板：更新条件过弱，或者假设框架会自动补全业务条件。
- 检查点：更新必须有完整命中条件；若需并发保护，再叠加版本或状态条件。

### WR-03 批量写
- 正例模板：`insertable(list).batch().executeRows();`
- 反例模板：大批量逐条写且不考虑分批与事务边界。
- 检查点：批量写要审查行数返回语义、分批策略、失败恢复。

### WR-04 删除
- 正例模板：`deletable(User.class).where(u -> u.id().eq(id)).executeRows();`
- 反例模板：`allowDeleteStatement(true)` 后只靠模糊条件或没有额外审查。
- 检查点：删除条件必须完整；物理删除必须额外评审。

### WR-05 软删除
- 正例模板：项目实体启用逻辑删除时，优先走默认删除语义，并明确上层对“已删除”的处理。
- 反例模板：不知道实体有逻辑删除字段，却误以为删除是物理删。
- 检查点：软删/物理删语义必须在 Repository 或 Service 说清楚。

### CC-01 先查后改风险识别
- 正例模板：先判断能否改写成单 SQL；不能时再加事务、版本号、唯一键或断言行数。
- 反例模板：`select -> if status ok then update`，中间没有任何并发保护。
- 检查点：读写窗口里可能出现状态漂移。

### CC-02 乐观锁更新
- 正例模板：实体使用 `@Version`，表达式更新显式 `withVersion`，失败时把 `0` 行更新视为并发冲突。
- 反例模板：实体有版本字段，但业务层默认 `ignoreVersion()`。
- 检查点：不要把忽略版本当常规写法。

### CC-03 唯一键幂等
- 正例模板：唯一业务键 + 插入冲突处理，或唯一键 + 查询断言 + 明确事务。
- 反例模板：只在应用层 `if not exists then insert`，数据库层没有唯一约束。
- 检查点：幂等最终要落到数据库约束或可验证的单语句语义。

### CC-04 更新 0 行的语义判断
- 正例模板：区分“记录不存在”“版本过期”“状态不匹配”“重复请求”。
- 反例模板：`executeRows()==0` 直接返回成功。
- 检查点：0 行更新通常是重要业务信号。

### TX-01 单服务事务
- 正例模板：Service 方法内统一开启事务，完成查询校验、写入、日志后再提交。
- 反例模板：Repository A 自己开事务，Repository B 也自己开事务，业务层以为整体原子。
- 检查点：事务边界要和业务边界对齐。

### TX-02 跨仓储事务协调
- 正例模板：一个 Service 协调多个 Repository，统一由宿主事务或 `beginTransaction()` 包裹。
- 反例模板：两个仓储各自成功，第三步失败后没有回滚路径。
- 检查点：跨仓储写入要么同事务，要么给出补偿方案。

### TX-03 回滚语义
- 正例模板：领域异常、并发异常、唯一键冲突默认触发回滚。
- 反例模板：捕获异常后吞掉，导致上层以为成功。
- 检查点：异常翻译后仍要保留失败语义。

### TX-04 不应开事务的场景
- 正例模板：普通分页列表、导出查询、缓存预读不包长事务。
- 反例模板：把用户点击一次列表页也放进长事务。
- 检查点：没有原子性需求就不要滥开事务。

### LA-01 Repository 正确用法
- 正例模板：Repository 封装 EasyQuery 查询与写入细节，对外暴露业务友好的方法签名。
- 反例模板：Repository 只返回裸 `Queryable` 让 Service 随意继续拼接。
- 检查点：持久化细节应尽量收口。

### LA-02 Service 正确用法
- 正例模板：Service 负责业务判断、事务、并发语义、异常翻译。
- 反例模板：Service 同时承载大量 SQL 细节、方言分支、动态排序拼装。
- 检查点：Service 不是第二个 Repository。

### LA-03 错误的 Service 直接拼 ORM DSL
- 正例模板：Service 调用 `userRepository.lockingUpdatePhone(...)`
- 反例模板：Service 里直接堆叠 `queryable/updatable/deletable/orderByObject/whereObject`
- 检查点：若不得不临时这样做，必须说明原因并计划回收。

### LA-04 Command / Listener 直接访问仓储的反例
- 正例模板：`listener -> service.handleEvent(...)`
- 反例模板：`listener -> repository.queryable(...).where(...).executeRows()`
- 检查点：入口层应保持薄，避免业务与持久化耦合。

### RV-01 N+1 查询风险
- 正例模板：审查列表场景是否把关联读取下推到合适查询策略或批量查询策略。
- 反例模板：查出 100 条主记录后，每条再查一次子记录。
- 检查点：不是所有问题都靠 ORM 自动解决。

### RV-02 全表扫描风险
- 正例模板：空条件、大范围模糊查询、无索引排序前先评估边界。
- 反例模板：后台搜索接口无条件放开全表 `like`。
- 检查点：业务“能查”不等于工程“该这样查”。

### RV-03 无 where 更新/删除风险
- 正例模板：即使源码有保护，也把“条件完整性”当成审查硬项。
- 反例模板：认为框架会兜底，所以调用层不再检查条件。
- 检查点：上层应主动保证命中范围正确。

### RV-04 主线程查库风险
- 正例模板：若上下文是 Bukkit / 游戏服，数据库读写全部移到异步线程或专用执行器。
- 反例模板：玩家事件主线程直接访问 Repository。
- 检查点：这是线程模型风险，不是 ORM 语法问题。

### RV-05 列表全量查出后内存过滤风险
- 正例模板：过滤、排序、分页尽量在 SQL 侧完成。
- 反例模板：`toList()` 后再 `.stream().filter().sorted().skip().limit()`
- 检查点：这通常同时损失正确性与性能。

### RV-06 ORM 实体泄漏到 API 层风险
- 正例模板：Repository 返回 DTO/VO/聚合结果或由 Service 做映射。
- 反例模板：Controller 直接返回 Entity，包括版本号、删除标记、审计字段。
- 检查点：边界对象与持久化对象不要混用。

### EQ-01 Queryable / Updateable / Transaction 典型入口
- 正例模板：查询从 `queryable` 开始，写入从 `insertable/updatable/deletable` 开始，事务从 `beginTransaction` 或宿主事务开始。
- 反例模板：没有确认公共入口就凭记忆造 API。
- 检查点：先确认入口，再扩展实现。

### EQ-02 常见 DSL 组合方式
- 正例模板：`queryable -> where/whereObject -> orderBy/orderByObject -> select -> toList/toPageResult`
- 正例模板：`updatable -> setColumns -> withVersion/ignoreVersion -> where -> executeRows`
- 检查点：组合顺序要符合公共 API 习惯与测试习惯。

### EQ-03 示例与源码冲突时如何裁决
- 正例模板：文档示例若使用旧 API 名称，回到源码和测试确认当前公共方法名。
- 反例模板：看见文档里有 `noVersionIgnore()` 就直接生成同名调用。
- 检查点：输出里要写明“文档存在历史痕迹，以源码/测试为准”。

### EQ-04 文档行为与源码不一致时如何处理
- 正例模板：先记录冲突点，再采用当前 API/测试行为，并提示用户该差异可能与版本有关。
- 反例模板：忽略冲突，混用新旧写法。
- 检查点：冲突必须显式裁决，不能含糊带过。

## Output Constraints
最终输出必须满足以下约束：

- 先给结论，再给依据与落地代码，不要只讲概念。
- 明确区分哪部分是 `A/B` 级 EasyQuery 事实，哪部分是 `X` 级通用 ORM 工程规则。
- 若本地证据不足，必须明确写出“不足点、当前假设、下一步检索路径”。
- 生成代码时，优先给可直接落地的 Repository / Service / 调用层代码骨架，不要只给抽象口号。
- 代码审查时，优先指出 bug、风险、回归点、缺失测试，再给总结。
- 问题分析时，必须给出调用链、根因、修复建议、回归测试建议。
- 不要大段照抄源码、测试或文档；只提炼规则、模式、入口、限制、反模式。
- 如果用了 Web，必须说明触发原因、使用来源、为何没有采用本地证据。
- 如果项目上下文未知，不要擅自假设 Spring、Bukkit、分库分表、消息队列等框架前提。
