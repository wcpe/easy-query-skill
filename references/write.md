# Write DSL — insert / update / delete

Inserts (single + batch), updates (`setColumns`, increment, by-entity), deletes (by id / condition),
optimistic locking, and logic-delete. All write chains end in `executeRows(...)`, which returns the affected
row count.

## When to use / not

Use for mutating data. For the transaction wrapper around multiple writes see `transaction.md`.

## Insert

```java
Topic t = new Topic();
t.setStars(999);
t.setTitle("title999");
t.setCreateTime(LocalDateTime.now());

long rows = easyEntityQuery.insertable(t).executeRows();        // returns affected rows
// For a DB-generated key, pass true to backfill the id onto the object:
long rows2 = easyEntityQuery.insertable(t).executeRows(true);   // t.getId() is now populated
```

Batch insert:
```java
List<Topic> list = buildMany();
long rows = easyEntityQuery.insertable(list).batch().executeRows();
```
`.batch()` issues a batched statement. Note: some JDBC drivers don't return precise per-row counts for
batches — don't assert an exact count unless you've confirmed the driver does.

## Update

By condition with `setColumns` (the proxy lambda picks columns type-safely):
```java
long rows = easyEntityQuery.updatable(Topic.class)
        .setColumns(o -> o.stars().set(12))
        .where(o -> o.id().eq("2"))
        .executeRows();

// multiple columns
easyEntityQuery.updatable(Topic.class)
        .setColumns(o -> {
            o.stars().set(12);
            o.title().set("new title");
        })
        .where(o -> o.id().eq("5"))
        .executeRows();
```

Increment / decrement (atomic, in-SQL):
```java
easyEntityQuery.updatable(Topic.class)
        .setColumns(o -> o.stars().increment())     // stars = stars + 1
        .whereById("5").executeRows();

easyEntityQuery.updatable(Topic.class)
        .setColumns(o -> o.stars().decrement(2))    // stars = stars - 2
        .where(o -> o.id().eq("5")).executeRows();
```

Update a whole entity by its primary key:
```java
Topic t = new Topic();
t.setId("5");
t.setTitle("updated");
long rows = easyEntityQuery.updatable(t).executeRows();   // UPDATE ... WHERE id = ?
```

Assert an expected row count (throws if mismatch — good for "must update exactly one"):
```java
easyEntityQuery.updatable(Topic.class)
        .setColumns(o -> o.title().set("x"))
        .where(o -> o.id().eq("5"))
        .executeRows(1, "更新失败");          // expectRows, message
// also: .executeRows(expectRows, msg, code)
```

## Delete

```java
// by id
long r1 = easyEntityQuery.deletable(Topic.class).whereById("999").executeRows();
// by condition
long r2 = easyEntityQuery.deletable(Topic.class).where(o -> o.title().eq("title998")).executeRows();
// by entity (uses its primary key)
long r3 = easyEntityQuery.deletable(topic).executeRows();
// batch
easyEntityQuery.deletable(topics).batch().executeRows();
```

## Logic-delete vs physical delete

If the entity has `@LogicDelete`, `deletable(...)` performs a **soft delete** — it issues
`UPDATE ... SET deleted = ?` and queries auto-filter deleted rows. To physically remove the row, opt out
explicitly:
```java
easyEntityQuery.deletable(BlogEntity.class)
        .where(o -> o.id().eq("id123"))
        .disableLogicDelete()            // bypass soft-delete -> real DELETE
        .allowDeleteStatement(true)      // allow the DELETE to run
        .executeRows();
```
Only set `allowDeleteStatement(true)` after confirming the `where` is complete — it removes a guard, not the
need for a correct condition.

## Optimistic locking — `@Version`

With a `@Version` column, updates/deletes append `WHERE version = ?` and bump it. A `0` row count means the
row was changed by someone else (stale version). Treat that as a concurrency conflict, not success.

```java
easyEntityQuery.updatable(SysUserVersionLong.class)
        .setColumns(s -> s.phone().set("123"))
        .where(o -> o.id().eq(id))
        .withVersion(1L)        // expected current version
        .executeRows();

// deliberately bypass version checking (only with a clear reason):
easyEntityQuery.deletable(SysUserVersionLong.class)
        .whereById(id)
        .ignoreVersion()
        .executeRows();
```

## Common mistakes

- Treating `executeRows() == 0` as success — it usually means not-found / stale-version / state-changed.
- Update/delete with a weak or missing `where` (relying on the framework to "protect" you).
- `allowDeleteStatement(true)` without auditing the condition.
- `ignoreVersion()` as a default — it silently disables optimistic locking.
- Assuming batch writes return an exact per-row count across all drivers.

## Sources
- 源码验证: `sql-test/.../InsertTest.java`, `UpdateTest.java`, `DeleteTest.java`, `VersionTest.java`;
  `SQLExecuteExpectRows` (`executeRows(long,String[,String])`) @ `com.easy.query.core.basic.api.internal`.
- 官方文档: `easy-query-doc/src/ability/{insert,update,delete}.md`. Skill baseline 3.1.89-dev.
