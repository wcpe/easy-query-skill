# Relation queries — @Navigate, include, joins, subquery

Two ways to relate tables: **navigation properties** (`@Navigate` + `.include(...)`, the idiomatic
easy-query way) and **explicit joins**. Plus relation-based subqueries.

## When to use / not

Use `@Navigate` + `.include(...)` to load related objects (one-to-many, many-to-one, many-to-many). Use
explicit joins when you need ad-hoc join shapes or to filter/aggregate across tables without a declared
relation. For aggregate/groupBy see `advanced.md`.

## 1. Declare relations with `@Navigate`

`@Navigate` goes on a field that holds the related entity/collection. `selfProperty` / `targetProperty` name
the join columns; `RelationTypeEnum` is the cardinality. (`Entity.Fields.x` constants come from the proxy /
field-name generation; plain strings also work.)

One-to-many (a company has many users):
```java
@Navigate(value = RelationTypeEnum.OneToMany,
          selfProperty = {Company.Fields.id},
          targetProperty = {SysUser.Fields.companyId})
private List<SysUser> users;
```

Many-to-one (a user belongs to one company):
```java
@Navigate(value = RelationTypeEnum.ManyToOne,
          selfProperty = {SysUser.Fields.companyId},
          targetProperty = {Company.Fields.id})
private Company company;
```

Many-to-many:
```java
@Navigate(value = RelationTypeEnum.ManyToMany,
          selfProperty = "uid",
          targetProperty = "uid")
private List<TbAccount> accounts;
```

Imports: `com.easy.query.core.annotation.Navigate` (the annotation) and
`com.easy.query.core.enums.RelationTypeEnum` (the cardinality enum — note it lives under `.enums`, not
`.annotation`).

## 2. Eager-load with `.include(...)`

`.include(...)` populates a navigation property. You can also filter on the relation inside `where`:

```java
List<SysUser> list = easyEntityQuery.queryable(SysUser.class)
        .include(user -> user.bankCards())                       // load each user's bankCards
        .where(user -> {
            user.bankCards().where(bc -> bc.type().eq("储蓄卡"))   // filter on the relation
                            .all(bc -> bc.code().startsWith("33123"));
        })
        .toList();
```

The framework runs the relation as a separate batched query (no N+1) — `print-nav-sql: true` in Spring shows
the generated navigation SQL.

## 3. Relation subquery — `subQueryToGroupJoin`

Turn a navigation relation into a group-join subquery (efficient existence/aggregate over the relation):

```java
List<MyTopic> list = easyEntityQuery.queryable(MyTopic.class)
        .subQueryToGroupJoin(s -> s.myTopics())
        .where(d -> {
            d.myTopics().any();          // EXISTS-style over the relation
        })
        .toList();
```

You can also set `subQueryToGroupJoin = true` on the `@Navigate` annotation to make a relation use the
group-join strategy by default.

## 4. Explicit joins

When there's no declared relation, join by class. The join lambda receives one proxy per joined table:

```java
List<Topic> list = easyEntityQuery.queryable(Topic.class)
        .leftJoin(BlogEntity.class, (t, b) -> t.id().eq(b.id()))
        .where((t, b) -> b.title().like("hello"))
        .toList();
```

Chaining more joins uses `leftJoinMerge` / `rightJoinMerge`, where the merge lambda exposes the table handles
(`o.t1`, `o.t2`, …):
```java
easyEntityQuery.queryable(Topic.class)
        .leftJoin(Topic.class, (t1, t2) -> t1.id().eq(t2.id()))
        .leftJoinMerge(Topic.class, o -> o.t1.id().eq(o.t3.id()))
        .toList();
```
`rightJoin` / `rightJoinMerge` work the same way.

## Common mistakes

- Manually looping queries to load children (`for (user : users) query bankCards`) → N+1; use `.include(...)`.
- Wrong `selfProperty`/`targetProperty` direction on `@Navigate` (self = this entity's column, target = the
  other entity's column).
- Reaching for explicit joins when a declared `@Navigate` + `.include(...)` is clearer and avoids N+1.

## Sources
- 源码验证: `sql-test/.../dameng/DamengQueryTest.java` (`.include(...)`, `.subQueryToGroupJoin(...)`),
  `.../h2/domain/{TbOrder,TbAccount}.java`, `.../entity/BlogEntity.java` (`@Navigate`),
  `BaseEntityQueryAggregateTest1.java` (explicit join shapes). `@Navigate` @
  `com.easy.query.core.annotation`; `RelationTypeEnum` @ `com.easy.query.core.enums` (verified in source).
- 官方文档: `easy-query-doc/src/navigate/*`, `src/include/*`, `src/guide/spring-boot.md`. Skill baseline 3.1.89-dev.
