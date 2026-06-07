# Advanced features

Aggregate/groupBy, code-first DDL, sharding, and multi-datasource. These are layer-3 topics — the snippets
here are verified entry points; for deep configuration follow the doc pointers in each Sources line and
confirm against the user's version.

## Aggregate + groupBy + projection

Group with `GroupKeys.of(...)`, then project keys and aggregates in `select`. Inside the select lambda,
`g.key1()` is the first group key and `g.groupTable()` exposes the grouped columns for aggregate functions.

```java
List<TopicGroupDTO> rows = easyEntityQuery.queryable(Topic.class)
        .where(o -> o.stars().gt(100))
        .groupBy(o -> GroupKeys.of(o.title()))
        .select(g -> {
            TopicGroupDTOProxy r = new TopicGroupDTOProxy();
            r.title().set(g.key1());
            r.cnt().set(g.intCount());                 // COUNT(*)
            r.maxStars().set(g.groupTable().stars().max());
            r.sumStars().set(g.groupTable().stars().sum());
            return r;
        })
        .toList();
// SELECT title, COUNT(*), MAX(stars), SUM(stars) FROM t_topic WHERE stars > ? GROUP BY title
```

Aggregate functions on a grouped column: `.count()` / `.intCount()` / `.sum()` / `.avg()` / `.max()` /
`.min()`. There is also a `Select.DRAFT.of(...)` form to project into a lightweight `DraftN` tuple when you
don't want a dedicated DTO. Non-grouped aggregates (e.g. over a join) use `sumOrNull` / `sumOrDefault` /
`maxOrNull` / `minOrNull` terminals.

## Code-first DDL (auto table sync)

Create/migrate tables from entity classes — handy for tests (see `testing.md`) and bootstrapping.

```java
DatabaseCodeFirst codeFirst = easyEntityQuery.getDatabaseCodeFirst();
codeFirst.createDatabaseIfNotExists();                       // optional: create the schema
codeFirst.syncTableCommand(Arrays.asList(Topic.class, SysUser.class))
         .executeWithTransaction(arg -> {
             System.out.println(arg.sql);                    // inspect the DDL
             arg.commit();
         });
```
`executeWithTransaction(...)` opens easy-query's own transaction (call `arg.commit()`).
`executeWithEnvTransaction(...)` participates in an ambient (e.g. Spring) transaction instead.

## Sharding (dynamic tables)

Annotate the entity with a sharding initializer and mark the shard key; register the initializer at config
time.

```java
@Data
@Table(value = "t_order", shardingInitializer = OrderShardingInitializer.class)
@EntityProxy
public class Order implements ProxyEntityAvailable<Order, OrderProxy> {
    @Column(primaryKey = true)
    @ShardingTableKey                 // the column that decides the shard
    private String id;
    // ...
}

// modulo sharding: t_order_0 / t_order_1
public class OrderShardingInitializer extends AbstractShardingTableModInitializer<Order> {
    @Override protected int mod() { return 2; }          // number of shards
    @Override protected int tailLength() { return 1; }   // suffix length, e.g. _0 .. _1
}
```
Register the initializer on the query configuration during bootstrap:
```java
queryConfiguration.applyShardingInitializer(new OrderShardingInitializer());
```
`@ShardingTableKey` and the `Abstract*ShardingInitializer` base classes are the verified pieces; exact
routing/config (ranges, data-source sharding) is broader — see the sharding docs.

## Multi-datasource

There is no `@UseDataSource` annotation; switching is done through `EasyMultiEntityQuery` (a ThreadLocal
current-datasource model):

```java
public interface EasyMultiEntityQuery extends EasyEntityQuery {
    String getCurrentDataSource();
    void setCurrent(String dataSource);
    EasyEntityQuery getByDataSource(String dataSource);
    <TResult> TResult executeScope(String dataSource, Function<EasyEntityQuery, TResult> fn);
    void clear();
}
```
Prefer the scoped form so the current datasource is always reset:
```java
List<Order> orders = multiEntityQuery.executeScope("ds2", eq ->
        eq.queryable(Order.class).where(o -> o.status().eq(1)).toList());
```

## Custom primary key generator (UUID / snowflake)

Auto-generate the PK on insert by implementing `PrimaryKeyGenerator`
(`com.easy.query.core.basic.extension.generated`, method `getPrimaryKey()`) and binding it on the column.

```java
import com.easy.query.core.basic.extension.generated.PrimaryKeyGenerator;

// @Component   // Spring Boot auto-registers
public class UUIDPrimaryKeyGenerator implements PrimaryKeyGenerator {
    @Override public Serializable getPrimaryKey() { return UUID.randomUUID().toString().replace("-", ""); }
}

@Table("t_test")
@EntityProxy
public class Demo implements ProxyEntityAvailable<Demo, DemoProxy> {
    @Column(primaryKey = true, primaryKeyGenerator = UUIDPrimaryKeyGenerator.class)
    private String id;
}
```
For a snowflake id, return `String.valueOf(snowflake.nextId())` from `getPrimaryKey()`.

## Data tracking — diff update (only changed columns)

By default `updatable(entity)` updates all columns. With a tracking context, easy-query updates **only the
columns that actually changed** since the entity was queried. Use `TrackManager`
(`com.easy.query.core.basic.extension.track`) + `.asTracking()` on the query.

```java
TrackManager tm = easyEntityQuery.getRuntimeContext().getTrackManager();
try {
    tm.begin();
    SysUser u = easyEntityQuery.queryable(SysUser.class).asTracking().whereById("1").firstOrNull();
    u.setPhone("13900000000");                 // change one field
    easyEntityQuery.updatable(u).executeRows(); // UPDATE ... SET phone = ? WHERE id = ?  (only phone)
} finally {
    tm.release();
}
```
In Spring Boot, annotate the service method with `@EasyQueryTrack` instead of the manual begin/release.

## CTE (WITH clause)

Turn a queryable into a CTE with `.toCteAs()` and reuse it in joins:

```java
EntityQueryable<TopicProxy, Topic> cte = easyEntityQuery.queryable(Topic.class)
        .where(t -> t.id().eq("456"))
        .toCteAs();
List<Topic> list = easyEntityQuery.queryable(Topic.class)
        .leftJoin(cte, (t, c) -> t.id().eq(c.id()))
        .toList();   // WITH with_Topic AS (...) SELECT ... LEFT JOIN with_Topic ...
```
For a reusable CTE "view" with window functions, an entity can implement `EntityCteViewer<T>` and define its
query in `viewConfigure(...)` — see docs.

## JDBC listener — log slow SQL / metrics

Implement `JdbcExecutorListener` (`com.easy.query.core.basic.extension.listener`) to hook every execution
(SQL, params, elapsed, exception). Register via `replaceService(JdbcExecutorListener.class, listener)` at
bootstrap (Spring Boot: `@Component`).

```java
import com.easy.query.core.basic.extension.listener.JdbcExecutorListener;

public class SlowSqlListener implements JdbcExecutorListener {
    @Override public boolean enable() { return true; }
    @Override public void onExecuteBefore(JdbcExecuteBeforeArg arg) { }
    @Override public void onExecuteAfter(JdbcExecuteAfterArg after) {
        long ms = after.getEnd() - after.getBeforeArg().getStart();
        if (ms >= 200) log.warn("slow sql {}ms: {}", ms, after.getBeforeArg().getSql());
    }
}
```
(This is the same listener mechanism the test suite uses to capture and assert SQL — see `testing.md` §3.)

## Built-in SQL functions

The proxy DSL exposes DB functions on column accessors (string/number/date/json/math), e.g.
`o.name().length()`, `o.createTime().format("yyyy-MM-dd")`, `o.title().like(...)`, used inside `where` / `select`
/ `orderBy`. The exact catalog per category is in the docs (`easy-query-doc/src/func/*`); look it up there
rather than guessing a function name.

## Common mistakes

- Building a non-grouped aggregate with `groupBy(...).select(...)` machinery — use the `sumOrNull`/`maxOrNull`
  terminals for whole-result aggregates.
- Running code-first `syncTableCommand` without `arg.commit()` → nothing is applied.
- Setting `multiEntityQuery.setCurrent(...)` without a matching `clear()` → leaks the datasource to the next
  task on the same thread; prefer `executeScope(...)`.

## Sources
- 源码验证: `sql-test/.../dameng/DamengQueryTest.java` (groupBy/aggregate), `EntityQueryAggregateTest1.java`
  (sumOrNull/maxOrNull), `h2/domain/ALLTYPESharding.java` + `h2/sharding/AllTYPEShardingInitializer.java` +
  `h2/H2BaseTest.java` (`applyShardingInitializer`). `DatabaseCodeFirst`/`CodeFirstCommand` @
  `com.easy.query.core.basic.api.database`. `PrimaryKeyGenerator` @ `com.easy.query.core.basic.extension.generated`;
  `TrackManager` @ `com.easy.query.core.basic.extension.track`; `JdbcExecutorListener` @
  `com.easy.query.core.basic.extension.listener`.
- 官方文档: `easy-query-doc/src/ability/select/group.md`, `src/super/*` (sharding),
  `src/guide/sb-multi-datasource.md`, `src/guide/spring-boot.md` (code-first),
  `src/adv/{auto-key,data-tracking,cte,jdbc-listener}.md`, `src/func/*` (SQL functions).
