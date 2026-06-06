# easy-query-skill

面向 [easy-query](https://github.com/dromara/easy-query) ORM 的 Claude AI agent skill，帮助智能体在
**Java、Kotlin（KSP）、Spring Boot** 中编写、修改、审查并测试使用 easy-query 的代码。

本 skill 采用**渐进式披露**：一个很薄的入口文件（`SKILL.md`）通过路由表把任务导向若干份内容稠密、
可直接复制的参考文档；每段示例代码都来自可验证来源——easy-query 框架源码（`sql-test`）或官方文档。

## 目录结构

```
easy-query/
├── SKILL.md                     # 入口：触发条件、黄金规则、路由表、证据策略
├── references/
│   ├── setup-kotlin.md          # Gradle KSP（不用 KAPT）、实体、初始化、infix DSL
│   ├── setup-java.md            # Maven APT、EasyQueryBootstrapper 初始化、实体
│   ├── setup-spring-boot.md     # starter、application.yml、注入 EasyEntityQuery
│   ├── entity-mapping.md        # @Table/@Column/@Version/@LogicDelete/@Navigate、代理模型
│   ├── query.md                 # where、动态条件、排序、select-DTO、limit、分页
│   ├── relation-query.md        # @Navigate、.include(...)、子查询、显式 join
│   ├── write.md                 # 增删改、乐观锁、逻辑删除
│   ├── transaction.md           # beginTransaction try-with-resources 与 Spring @Transactional
│   ├── testing.md               # H2 内存库行为测试、.toSQL() 断言、SQL 监听捕获
│   ├── advanced.md              # 聚合/分组、code-first DDL、分库分表、多数据源
│   └── api-index.md             # 精确符号/包名速查 + 禁用项（MyBatis/JPA/QueryDSL）
└── evals/
    └── evals.json               # 供 skill-creator 评测闭环使用的测试用例
```

## 设计原则

- **只用可验证的写法，不臆造 API。** 每段代码都标注来源：`源码验证`（框架源码/测试）或 `官方文档`，
  写在各参考文档末尾的 Sources 区块。skill 明确禁止输出 MyBatis-Plus / JPA / QueryDSL 等其他框架的语法。
- **渐进式披露。** `SKILL.md` 保持精简，深度内容下沉到 `references/`，智能体只按需加载所需的那一份。
- **Kotlin 一等公民**（基于 KSP），与 Java、Spring Boot 并列。

## 证据来源

- 框架源码：https://github.com/dromara/easy-query
- 官方文档：https://github.com/xuejmnet/easy-query-doc

## 评测

`easy-query-workspace/` 保留了 skill-creator 评测闭环的产物（7 个用例的 with-skill / baseline 对比、
量化基准 `benchmark.md`）作为质量佐证。
