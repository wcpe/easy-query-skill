# 缓存（sql-cache）

easy-query 的缓存是一个独立模块 `sql-cache`，通过 `EasyCacheClient` 按主键或全表读缓存，写操作时由触发器
自动失效。它不是"查询结果随手缓存"，而是面向**实体级**的 KV / 全量缓存。

## 何时用 / 不用

读多写少、按主键高频读取的实体（字典、配置、热点对象）适合。写频繁、强一致要求极高、或查询条件高度多变
的场景要谨慎（看下文一致性模式）。普通查询仍走 `EasyEntityQuery`，缓存是叠加层。

## 1. 依赖

```xml
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-cache</artifactId>
    <version>3.1.89</version>
</dependency>
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson</artifactId>
    <version>${redisson.version}</version>
</dependency>
<!-- 多级缓存（Redis + 本地）再加 caffeine -->
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
    <version>2.9.3</version>
</dependency>
```

## 2. 实体标记

实体加 `@CacheEntitySchema`（包 `com.easy.query.cache.core.annotation`，`value` 指定缓存键属性，默认
`"id"`），并按缓存模式实现标记接口（包 `com.easy.query.cache.core`）：

- `CacheKvEntity` —— KV 模式：只按主键取单个对象，必须给 key。
- `CacheAllEntity` —— 全量模式：把整表载入，支持无 key 的 `where`/分页。

```java
import com.easy.query.cache.core.CacheKvEntity;
import com.easy.query.cache.core.annotation.CacheEntitySchema;

@Data
@Table("t_blog")
@EntityProxy
@CacheEntitySchema                      // value 默认 "id"
public class Blog implements CacheKvEntity, ProxyEntityAvailable<Blog, BlogProxy> {
    @Column(primaryKey = true) private String id;
    private String content;
}
```

## 3. 读缓存

`EasyCacheClient`（包 `com.easy.query.cache.core`）。KV 模式用 `kvStorage`，全量模式用 `allStorage`：

```java
// KV：按主键取（缓存未命中会回源 DB 并回填）
Blog blog = easyCacheClient.kvStorage(Blog.class).singleOrNull("1");
// KV + 额外过滤 / 拦截器
Blog b2 = easyCacheClient.kvStorage(Blog.class).where(o -> o.content().contains("123")).singleOrNull("2");

// 全量（实体需实现 CacheAllEntity）：可无 key 查询、分页
List<Topic> all = easyCacheClient.allStorage(Topic.class).toList();
EasyPageResult<Topic> page = easyCacheClient.allStorage(Topic.class)
        .where(o -> o.title().contains("123"))
        .toPageResult(1, 2);
```

## 4. 装配与失效

`EasyCacheClient` 用 `EasyCacheBootstrapper.defaultBuilderConfiguration()...build()` 构建（注入
`EasyQueryClient`、`RedissonClient`、自定义 `EasyCacheManager`），并通过
`easyQueryClient.addTriggerListener(...)` 在增删改时自动清理对应缓存：

```java
EasyCacheClient easyCacheClient = EasyCacheBootstrapper.defaultBuilderConfiguration()
        .optionConfigure(op -> {
            op.setKeyPrefix("CACHE");
            op.setExpireMillisSeconds(1000 * 60 * 60);        // 缓存 1 小时
            op.setValueNullExpireMillisSeconds(1000 * 10);    // null 值缓存 10 秒（防穿透）
        })
        .replaceService(EasyQueryClient.class, easyQueryClient)
        .replaceService(RedissonClient.class, redissonClient)
        .replaceService(EasyCacheManager.class, MyCacheManager.class)
        .build();

easyQueryClient.addTriggerListener(triggerEvent -> {
    if (EasyCacheUtil.isCacheEntity(triggerEvent.getEntityClass())) {
        // 对该实体的写操作 → 清理缓存
    }
});
```
`EasyCacheManager` 可继承 `AbstractCacheManager` 自己实现（单 Redis），或 Redis + Caffeine 做多级缓存
（本地一层、Redis 一层），实现细节见官方文档。

## 5. 一致性模式（取舍）

- **逻辑删除 + 延迟双删**：依赖软删除与缓存延迟失效，简单通用，存在短暂不一致窗口。
- **CDC（binlog 订阅）**：通过订阅数据库变更实时失效，准实时一致，但需要部署 CDC 链路。

按业务对一致性的要求选择；强一致/资金类数据不要单纯依赖缓存。

## 常见错误

- 把缓存当强一致存储——它有过期与失效窗口。
- 频繁变更的大表用 `CacheAllEntity` 全量缓存 → 频繁整表失效，得不偿失。
- 没配 `valueNullExpireMillisSeconds` → 不存在的 key 反复回源（缓存穿透）。
- 漏接 `addTriggerListener` 失效逻辑 → 写后读到脏数据。

## Sources
- 源码验证: 模块 `sql-extension/sql-cache`；`EasyCacheClient`（`kvStorage`/`allStorage`/`deleteBy`）@
  `com.easy.query.cache.core`；`@CacheEntitySchema` @ `com.easy.query.cache.core.annotation`；
  `CacheKvEntity`/`CacheAllEntity` @ `com.easy.query.cache.core`；`sql-test/.../entity/BlogEntity.java`
  (`@CacheEntitySchema` + `CacheKvEntity`)，`sql-test/.../QueryTest25.java` (cached read)。
- 官方文档: `easy-query-doc/src/cache/{readme,api,redis-logicdelete,redis-logicdelete-multi-level}.md`。
  多级缓存的 `CacheMultiLevel` 标记在示例中由项目侧定义，使用前请按你的依赖版本确认。
