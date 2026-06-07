---
name: easy-query
description: >-
  Write, modify, review, debug, or test Java/Kotlin code that uses the easy-query
  ORM — the library published under the `com.easy-query` group id and used via
  `EasyEntityQuery` / `EasyQueryClient` / `easyEntityQuery` (a.k.a. EasyQuery, a
  strong-typed 国产 ORM). Use this skill whenever the task involves easy-query
  entities/proxy generation, proxy-DSL queries, inserts/updates/deletes,
  pagination, transactions, relation/@Navigate/include queries, sharding,
  multi-datasource, code-first DDL, or writing unit tests for easy-query code —
  in plain Java, Kotlin (KSP), or Spring Boot. Trigger even when the user does
  not name easy-query but the code clearly uses its proxy DSL (e.g.
  `easyEntityQuery.queryable(X.class).where(o -> o.field().eq(v))` or Kotlin
  `where { it.field().eq(v) }`), asks how to query/insert/page/test "this ORM" in
  a project that depends on easy-query, or asks to migrate MyBatis/JPA code TO
  easy-query. Do NOT use it for other persistence tools that merely share
  keywords — MyBatis / MyBatis-Plus (QueryWrapper), JPA / Hibernate
  (CriteriaBuilder), Spring Data JPA, jOOQ, QueryDSL, SQLAlchemy, raw-SQL tuning,
  Elasticsearch query DSL, or @tanstack/react-query — unless the task is
  explicitly about converting that code to easy-query.
---

# EasyQuery skill

Help an agent write **compilable, idiomatic easy-query code** in Java, Kotlin (KSP), and Spring Boot,
plus the unit tests for it. This skill is built from verified examples — real source in the easy-query
repo and the official docs — so the rule is simple: **use the patterns here, do not invent API.**

This file is the index. Read the one `references/*.md` file your task points to; each contains complete,
copy-ready code. Do not load all references at once.

## Golden rules (read these every time)

1. **Two entry points; default to `EasyEntityQuery`.** `EasyEntityQuery` is the strong-typed *proxy DSL*
   (`easyEntityQuery.queryable(User.class).where(o -> o.name().eq(x))`). `EasyQueryClient` is the weak-typed
   core client. Use `EasyEntityQuery` unless the user is clearly on the weak-typed path.

2. **Every entity needs a generated proxy.** The entity is annotated `@Table` + `@EntityProxy` and
   implements `ProxyEntityAvailable<Entity, EntityProxy>`. The `EntityProxy` class is **generated at compile
   time** — APT for Java, **KSP for Kotlin** (not KAPT). So "cannot find `XxxProxy`" or "proxy not generated"
   is a **build-config problem**, not a code problem → see `references/setup-java.md` / `references/setup-kotlin.md`.

3. **The DSL is the same across languages; only the lambda surface differs.**
   Java: `where(o -> o.id().eq("1"))`. Kotlin: `where { it.id().eq("1") }` (optional infix: `it.id eq "1"`).
   Method names (`eq`/`like`/`gt`/`in`/`orderBy`/`toList`/`executeRows`…) are identical.

4. **Dynamic conditions use the gated overloads — never build strings.** Use `.eq(condition, value)` or
   `where(condition, o -> ...)` so an empty filter is simply skipped. See `references/query.md`.

5. **Pagination must carry a stable sort.** `toPageResult(pageIndex, pageSize)` returns a page with
   `getData()` / `getTotal()`; always pair it with `orderBy(...)`, and add a tiebreaker (e.g. id) when the
   sort key is not unique.

6. **Writes have safety semantics — respect them.** Logic-delete is applied automatically; a physical delete
   needs `.disableLogicDelete().allowDeleteStatement(true)`. Optimistic lock uses `@Version` +
   `withVersion(...)` / `ignoreVersion()`. A row count of `0` is a signal (not found / stale version / state
   changed), not a silent success. See `references/write.md`.

## Routing table — task → reference

| Task | Read |
|------|------|
| Set up a **Kotlin** project (Gradle KSP, entity, init, infix DSL) | `references/setup-kotlin.md` ★ |
| Set up a plain **Java** project (Maven APT, bootstrap init, entity) | `references/setup-java.md` |
| **Spring Boot** integration (starter, `application.yml`, inject `EasyEntityQuery`) | `references/setup-spring-boot.md` |
| Define/annotate an **entity** (`@Table/@Column/@Version/@LogicDelete/@Navigate`, proxy model) | `references/entity-mapping.md` |
| **Query**: where, dynamic filters, order, select-to-DTO, terminals, pagination | `references/query.md` |
| **Relation** queries: joins, `@Navigate`, `.include(...)`, subquery | `references/relation-query.md` |
| **Write**: insert/batch, update (`setColumns`/increment), delete, `whereById`, version, logic-delete | `references/write.md` |
| **Transaction**: `beginTransaction` try-with-resources, Spring `@Transactional` | `references/transaction.md` |
| **Write unit tests** (H2 in-memory + behavior, or MySQL + SQL-string assertion) | `references/testing.md` ★ |
| **Interceptors**: auto-fill audit fields, multi-tenant filter, update-set hooks | `references/interceptors.md` |
| **Field↔column mapping**: enum/JSON value converter, TypeHandler, column encryption, `@ValueObject` | `references/type-mapping.md` (`@ValueObject` in `entity-mapping.md`) |
| **Computed / derived columns**: `@Column(sqlExpression/sqlConversion)`, cross-table stat columns | `references/computed-properties.md` |
| **Request-object query**: `whereObject` (`@EasyWhereCondition`), dynamic sort (`ObjectSort`), `@NavigateFlat` | `references/dto-query.md` |
| **Caching** (sql-cache): `EasyCacheClient` kv/all storage, `@CacheEntitySchema`, invalidation | `references/caching.md` |
| **Advanced**: sharding, multi-datasource, code-first DDL, aggregate/groupBy, custom PK, data tracking, CTE, JDBC listener, behavior flags (smart-predicate), SQL functions | `references/advanced.md` |
| Look up an exact **symbol / method / package** | `references/api-index.md` |

## Evidence policy

Order of truth: **the user's current project (their pom/build.gradle, entities, version, errors) → the
verified examples in this skill → say "I don't know / this isn't covered".** Never fill a gap by guessing a
class or method name. If the skill doesn't cover a scenario, say so plainly and point to the source/docs.

Each reference file ends with a **Sources** footer marking whether a snippet is `源码验证` (verified against
repo source/tests) or `官方文档` (from the official docs). Repo source and tests outrank doc prose when they
disagree. Analysis baseline: easy-query **3.1.89-dev**. Treat it as a reference version, not a hard lock — if
the user's version differs, prefer their project and flag APIs that may have moved.

## Anti-patterns to catch in review

- Inventing class/method names, or mixing in **MyBatis-Plus `QueryWrapper` / JPA `CriteriaBuilder` /
  QueryDSL / jOOQ** syntax — these are *not* easy-query and must never appear.
- `firstOrNull()` where the business key is unique → use `singleOrNull()`.
- `toList()` then filtering/sorting/paging in memory → push it into the DSL.
- Pagination with no `orderBy`, or an unstable sort key.
- Dynamic filters concatenated as strings instead of the gated `.eq(condition, value)` overloads.
- Physical delete via `allowDeleteStatement(true)` without verifying the `where` is complete.
- Treating a `0` row count from update/delete as success.
- Returning the ORM entity straight to a controller/API (leaks version/logic-delete/audit fields).

## What to output

Lead with the working code, then a one-line note on which reference it came from and any version caveat.
For reviews, point at the concrete bug/risk first. When the user's project context is unknown, don't assume
Spring vs plain Java vs Kotlin — ask or show the relevant variant.
