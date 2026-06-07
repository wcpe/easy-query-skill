# API index — symbol quick-reference

Exact names, packages, and the reference file that shows each in context. Use this to look up a symbol; never
invent one that isn't here or in the user's project.

## Entry points

| Symbol | Package | Notes |
|--------|---------|-------|
| `EasyEntityQuery` | `com.easy.query.api.proxy.client` | Strong-typed proxy DSL (default). |
| `DefaultEasyEntityQuery` | `com.easy.query.api.proxy.client` | Impl; `new DefaultEasyEntityQuery(client)`. |
| `EasyQueryClient` | `com.easy.query.core.api.client` | Weak-typed core client. |
| `EasyQueryBootstrapper` | `com.easy.query.core.bootstrapper` | `.defaultBuilderConfiguration()....build()`. |

## Entity annotations (`com.easy.query.core.annotation`)

`@Table` · `@Column` · `@EntityProxy` · `@Version` · `@LogicDelete` · `@Navigate` · `@ShardingTableKey`

- `@Column` keys: `primaryKey`, `generatedKey`, `value`, `exist`, `autoSelect`.
- Entity must `implements ProxyEntityAvailable<Entity, EntityProxy>` (`com.easy.query.core.proxy`).
- `RelationTypeEnum` (`com.easy.query.core.enums`): `OneToMany` / `ManyToOne` / `ManyToMany`.
- Strategy classes: `VersionLongStrategy` (`...extension.version`), `LogicDeleteStrategyEnum`
  (`...extension.logicdel`).

## Query DSL → see `query.md`

- Start: `queryable(Entity.class)` (Java) / `queryable(Entity::class.java)` (Kotlin).
- Filter: `where(o -> ...)`, gated `where(condition, o -> ...)`.
- Predicates: `eq` `ne` `gt` `ge` `lt` `le` `like` `notLike` `isNull` `isNotNull` `isNotBlank` `in` `notIn`
  `rangeClosed` — each has a gated overload `eq(condition, value)`.
- Order: `orderBy(o -> o.col().asc()/.desc())`.
- Limit / top-N: `limit(rows)` / `limit(offset, rows)` / gated `limit(condition, offset, rows)`.
- Project: `select(Dto.class, s -> Select.of(s.col().as(Dto::setX)))`.
- Terminals: `toList()` `firstOrNull()` `singleOrNull()` `count()` `any()`.
- Page: `toPageResult(pageIndex, pageSize)` → `EasyPageResult<T>` (`getData()`, `getTotal()`).

## Write DSL → see `write.md`

- `insertable(entity|list)` → `.batch()` → `.executeRows()` / `.executeRows(true)` (backfill key).
- `updatable(Entity.class)` → `.setColumns(o -> o.col().set(v) / .increment(n) / .decrement(n))` → `where`
  → `.executeRows()` / `.executeRows(expectRows, msg[, code])`.
- `updatable(entity)` → `.executeRows()` (by primary key).
- `deletable(Entity.class)` → `.whereById(id)` / `.where(...)` → `.executeRows()`.
- Version: `.withVersion(v)` / `.ignoreVersion()`.
- Physical delete: `.disableLogicDelete().allowDeleteStatement(true)`.

## Transactions → see `transaction.md`

- `easyEntityQuery.beginTransaction()` → `Transaction` (`com.easy.query.core.basic.jdbc.tx`):
  `commit()` / `rollback()` / `close()` (auto-rollback). Spring: `@Transactional`.

## Relations → see `relation-query.md`

- `.include(e -> e.relation())` (eager load), `.subQueryToGroupJoin(s -> s.relation())`,
  `.leftJoin/.rightJoin(Other.class, (a,b) -> ...)`, `.leftJoinMerge/.rightJoinMerge(...)`.

## Advanced → see `advanced.md`

- Aggregate in group: `groupBy(o -> GroupKeys.of(o.col()))`, `g.key1()`, `g.intCount()`,
  `g.groupTable().col().sum()/.max()/.min()/.avg()`; `Select.DRAFT.of(...)`. Whole-result: `sumOrNull`,
  `sumOrDefault`, `maxOrNull`, `minOrNull`.
- Code-first: `easyEntityQuery.getDatabaseCodeFirst().syncTableCommand(List<Class<?>>).executeWithTransaction(arg -> arg.commit())`.
- Sharding: `@Table(shardingInitializer=...)`, `@ShardingTableKey`,
  `AbstractShardingTableModInitializer`, `queryConfiguration.applyShardingInitializer(...)`.
- Multi-datasource: `EasyMultiEntityQuery.executeScope(name, eq -> ...)` / `setCurrent(name)` / `clear()`.

## Extensions → see `interceptors.md`, `type-mapping.md`, `dto-query.md`

- Interceptors (`com.easy.query.core.basic.extension.interceptor`): `EntityInterceptor`
  (`configureInsert`/`configureUpdate`), `PredicateFilterInterceptor`, `UpdateSetInterceptor`,
  `UpdateEntityColumnInterceptor`; base `Interceptor` (`name`/`apply`/`order`/`enable`). Register:
  Spring `@Component`, or `configuration.applyInterceptor(...)`. `ProtectedInterceptor` survives `noInterceptor()`.
- Value converter: `ValueConverter<P,V>` / `ValueAutoConverter`
  (`com.easy.query.core.basic.extension.conversion`), bind `@Column(conversion = X.class)` or
  `configuration.applyValueConverter(...)`.
- Type handler: `JdbcTypeHandler` (`com.easy.query.core.basic.jdbc.types.handler`), bind
  `@Column(typeHandler = X.class)`.
- Encryption: `@Encryption(strategy=, supportQueryLike=)` (`com.easy.query.core.annotation`) +
  `EncryptionStrategy` (`com.easy.query.core.basic.extension.encryption`) + `applyEncryptionStrategy(...)`.
- Audit ignore: `@UpdateIgnore` / `@InsertIgnore`; nested value type `@ValueObject`
  (all `com.easy.query.core.annotation`).
- Request-object query: `whereObject(dto)` + `@EasyWhereCondition(type=Condition.*, propName=, propNames=,
  tableIndex=, allowEmptyStrings=)` (`com.easy.query.core.annotation`); dynamic sort `ObjectSort`
  (`com.easy.query.core.api.dynamic.sort`); flatten relation field `@NavigateFlat(pathAlias=)`.
- Primary key generator: `@Column(primaryKeyGenerator = X.class)` + `PrimaryKeyGenerator`
  (`com.easy.query.core.basic.extension.generated`).
- Data tracking (diff update): `TrackManager` (`com.easy.query.core.basic.extension.track`) +
  `.asTracking()` + `updatable(entity)`; Spring `@EasyQueryTrack`.
- CTE: `.toCteAs()`, `EntityCteViewer<T>`. JDBC listener: `JdbcExecutorListener`
  (`com.easy.query.core.basic.extension.listener`).
- Computed columns (`computed-properties.md`): `@Column(sqlExpression = @ColumnSQLExpression(sql=, args={
  @ExpressionArg(prop=)}))` (`com.easy.query.core.annotation`); `@Column(sqlConversion = X.class)` +
  `ColumnValueSQLConverter` (`com.easy.query.core.basic.extension.conversion`); `@Column(autoSelect=false)`
  for expensive cross-table stats.
- DB-function generated key: `@Column(generatedSQLColumnGenerator = X.class)` + `GeneratedKeySQLColumnGenerator`
  (`com.easy.query.core.basic.extension.generated`).
- Behavior flags: `.configure(s -> s.getBehavior().add(EasyBehaviorEnum.SMART_PREDICATE))` —
  `EasyBehaviorEnum` (`com.easy.query.core.enums`).
- Caching (`caching.md`, module `sql-cache`): `EasyCacheClient.kvStorage(...)` / `.allStorage(...)`
  (`com.easy.query.cache.core`); `@CacheEntitySchema` (`com.easy.query.cache.core.annotation`) +
  `CacheKvEntity` / `CacheAllEntity`.

## Dialects (`useDatabaseConfigure(...)`)

`MySQLDatabaseConfiguration` (`com.easy.query.mysql.config`, artifact `sql-mysql`),
`H2DatabaseConfiguration` (`com.easy.query.h2.config`, `sql-h2`), plus `sql-pgsql` / `sql-mssql` /
`sql-oracle` / etc.

## Forbidden — never emit these (they are NOT easy-query)

- MyBatis-Plus: `QueryWrapper`, `LambdaQueryWrapper`, `IService`, `BaseMapper`.
- JPA/Hibernate: `CriteriaBuilder`, `EntityManager`, `@Entity`/`@Id` (from `javax`/`jakarta.persistence`).
- QueryDSL / jOOQ DSL.

If a needed capability isn't listed here or in the other references, say it's not covered rather than guessing.

## Sources
- 源码验证: package/symbol names from `sql-core`, `sql-api-proxy`, `sql-mysql`, `sql-h2`, and `sql-test`
  usages cited in the per-topic reference files. Skill baseline 3.1.89-dev.
