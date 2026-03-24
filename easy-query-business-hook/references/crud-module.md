# CRUD Module

在 MCP 无法提供足够源码或示例时，使用本文件作为基础 CRUD 模块的本地降级参考。

## 使用方式

- 优先把 CRUD 收敛在 Repository + Service 边界内，不要让调用层直接拼 easy-query DSL。
- 先定义实体、查询请求、返回 DTO，再补 Repository 方法和 Service 语义。
- 若项目已经有统一基类、通用分页对象或审计字段约定，优先跟随项目现有风格。

## CRUD Query Module Coverage

本模块当前覆盖以下查询知识点，优先配合 `query-patterns.md` 一起使用：

- 查询
- 查询对象
- 表达式编写
- 筛选对象
- 对象排序
- 多表 join
- 分组查询
- 常用 API 介绍
- 单表查询
- 分页查询
- `PARTITION BY`
- 联合查询 `UNION / UNION ALL`
- 递归树查询
- `CaseWhen`
- 大数据流式查询返回
- `map` 结果返回
- 结构化属性填充

## 常用 API 速览

- `queryable(...)`：查询入口
- `where(...)`：显式条件过滤
- `whereById(...)` / `whereByIds(...)`：主键查询
- `whereObject(...)`：主表动态筛选对象
- `orderBy(...)`：显式排序
- `groupBy(...)` / `having(...)`：分组与聚合后过滤
- `select(...)`：DTO、标量、聚合结果投影
- `toList()` / `singleOrNull()` / `firstOrNull()`：结果获取
- `toPageResult(...)`：分页查询
- `count()` / `any()` / `sumBigDecimal(...)` / `maxOrNull(...)` / `minOrNull(...)`：常见聚合 API

## API Preview

- 查询：`queryable`、`where`、`whereById`、`whereObject`、`orderBy`、`groupBy`、`having`、`select`
- 写入：`insertable`、`updatable`、`deletable`
- 结果：`toList`、`singleOrNull`、`firstOrNull`、`toPageResult`
- 聚合：`count`、`any`、`sumBigDecimal`、`maxOrNull`、`minOrNull`
- 事务：`beginTransaction`
- 高级能力：`join`、`caseWhen`、`union`、窗口函数、原生 SQL 等要优先以 MCP / 源码确认为准

## Query Object Template

查询对象优先只承载可枚举、可校验的过滤与排序参数，不要把复杂业务谓词全部塞进一个对象。

```java
public class UserQueryRequest {
    private Long shopId;
    private String keyword;
    private Integer status;
    private String sortField;
    private boolean asc;
    private int pageIndex;
    private int pageSize;

    // getters / setters
}
```

```kotlin
data class UserQueryRequest(
    val shopId: Long?,
    val keyword: String?,
    val status: Int?,
    val sortField: String?,
    val asc: Boolean,
    val pageIndex: Int,
    val pageSize: Int
)
```

## Filter Object Template

筛选对象适合主表动态条件，不适合跨表复杂谓词。

```java
public class UserFilter {
    private Long shopId;
    private String username;
    private Integer status;

    // getters / setters
}
```

```java
public List<UserEntity> listUsers(UserFilter filter) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .whereObject(filter)
        .orderBy(user -> user.id().desc())
        .toList();
}
```

## Expression Writing

表达式编写优先保持“条件可读、空参数 gated、业务语义清晰”。

```java
public List<OrderEntity> listOrders(OrderQueryRequest request) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> {
            order.shopId().eq(request.getShopId() != null, request.getShopId());
            order.status().eq(request.getStatus() != null, request.getStatus());
            order.orderNo().like(request.getKeyword() != null && !request.getKeyword().isBlank(), request.getKeyword());
        })
        .toList();
}
```

## Single Table Query

单表查询优先作为默认路径，只有确实需要关联数据时再上 join。

```java
public List<UserSummaryDTO> listUserSummaries(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.shopId().eq(shopId))
        .select(UserSummaryDTO.class, user -> new UserSummaryDTO(
            user.id(),
            user.username(),
            user.status()
        ))
        .toList();
}
```

## Return VO / DTO

返回 VO、DTO 时优先显式 `select`，不要把完整 Entity 直接泄漏给上层。

```java
public List<UserVO> listUserVOs(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.shopId().eq(shopId))
        .select(UserVO.class, user -> new UserVO(
            user.id(),
            user.username(),
            user.status()
        ))
        .toList();
}
```

## Anonymous Type 1

匿名类型在 README 示例和部分投影场景里可以看到思路，但当前本地源码依据不足以把它写成首选稳定模板。

```java
public Object listUserAnonymous1Placeholder() {
    return "Prefer DTO/VO projection first. If you need anonymous projection, verify current select inference against README examples and local source before use.";
}
```

## Anonymous Type 2 Placeholder

不同 easy-query 版本对匿名投影、临时对象、lambda 结果推断的支持细节可能不同。

```java
public Object listUserAnonymous2Placeholder() {
    return "Prefer MCP verification before relying on advanced anonymous projection inference.";
}
```

## Custom Flat Object

自定义平铺对象适合把 join 结果或聚合结果收成一个单层 DTO。

```java
public List<UserOrderFlatDTO> listUserOrderFlats(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .leftJoin(OrderEntity.class, (user, order) -> user.id().eq(order.userId()))
        .where((user, order) -> user.shopId().eq(shopId))
        .select(UserOrderFlatDTO.class, (user, order) -> new UserOrderFlatDTO(
            user.id(),
            user.username(),
            order.orderNo(),
            order.status()
        ))
        .toList();
}
```

## Select Advanced

`select` 进阶时，优先关注投影边界、聚合表达式和返回类型是否稳定。

```java
public List<UserOrderStatsDTO> listUserOrderStats(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .leftJoin(OrderEntity.class, (user, order) -> user.id().eq(order.userId()))
        .where((user, order) -> user.shopId().eq(shopId))
        .groupBy((user, order) -> {
            user.id();
            user.username();
        })
        .select(UserOrderStatsDTO.class, (user, order) -> new UserOrderStatsDTO(
            user.id(),
            user.username(),
            order.count(),
            order.sumBigDecimal(o -> o.payAmount())
        ))
        .toList();
}
```

## Where Advanced

`where` 进阶时，优先把业务分支写清楚，不要把复杂条件揉成不可读表达式。

```java
public List<OrderEntity> listOrdersAdvanced(OrderQueryRequest request) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> {
            order.shopId().eq(request.getShopId() != null, request.getShopId());
            order.status().in(request.getStatuses() != null && !request.getStatuses().isEmpty(), request.getStatuses());
            order.orderNo().like(request.getKeyword() != null && !request.getKeyword().isBlank(), request.getKeyword());
            order.createTime().ge(request.getStartTime() != null, request.getStartTime());
            order.createTime().le(request.getEndTime() != null, request.getEndTime());
        })
        .toList();
}
```

## Pagination Query

分页查询必须带稳定排序；排序字段不唯一时，追加主键作为稳定次序。

```java
public PageResult<UserEntity> pageUsers(UserQueryRequest request) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> {
            user.shopId().eq(request.getShopId() != null, request.getShopId());
            user.status().eq(request.getStatus() != null, request.getStatus());
        })
        .orderBy(user -> {
            user.createTime().desc();
            user.id().desc();
        })
        .toPageResult(request.getPageIndex(), request.getPageSize());
}
```

## Object Sorting

对象排序必须经过白名单映射，不要直接信任外部字段名。

```java
public <T> T applyUserSort(T query, UserQueryRequest request) {
    return query;
}
```

说明：
- 这里保留占位函数，是因为具体查询对象类型在不同 easy-query DSL 阶段可能不同。
- 真正实现时，优先回项目现有 Repository 写法或 MCP 确认当前排序 DSL。

## Multi-table Join

多表 join 优先明确关联条件、投影目标和排序。

```java
public List<OrderDetailDTO> listOrderDetails(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .leftJoin(UserEntity.class, (order, user) -> order.userId().eq(user.id()))
        .where((order, user) -> order.shopId().eq(shopId))
        .select(OrderDetailDTO.class, (order, user) -> new OrderDetailDTO(
            order.id(),
            order.orderNo(),
            user.username(),
            order.status()
        ))
        .toList();
}
```

## Group Query

分组查询适合统计型报表，优先直接投影到 DTO。

```java
public List<OrderStatusCountDTO> countOrdersByStatus(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .groupBy(order -> order.status())
        .select(OrderStatusCountDTO.class, order -> new OrderStatusCountDTO(
            order.status(),
            order.count()
        ))
        .toList();
}
```

## PARTITION BY Placeholder

`PARTITION BY` 常见于窗口函数、排名、分组内排序等高级查询。该能力的具体 DSL 很依赖 easy-query 当前版本与方言支持。

```java
public Object partitionByPlaceholder() {
    return "Prefer MCP verification before implementing PARTITION BY / window function DSL.";
}
```

## UNION Placeholder

`UNION / UNION ALL` 建议先用 MCP 确认当前版本公开 DSL，再落地生产代码。

```java
public Object unionPlaceholder() {
    return "Prefer MCP verification before implementing union/unionAll DSL.";
}
```

## Recursive Tree Query Placeholder

递归树查询通常依赖数据库递归 CTE、层级路径或应用层递归组装，具体策略强依赖方言与版本。

```java
public Object recursiveTreePlaceholder() {
    return "Prefer MCP verification before implementing recursive tree query DSL or CTE support.";
}
```

## CaseWhen Placeholder

`caseWhen` 在 README 示例语境中是存在的主题，但当前本地源码检索没有给到足够直接的公共 DSL 落点，降级时先保留占位说明。

```java
public Object caseWhenPlaceholder() {
    return "Prefer MCP or local README/source verification before implementing caseWhen projection DSL.";
}
```

## Streaming Query Placeholder

大数据流式返回通常依赖 easy-query 的流式 API、游标能力或宿主数据源配置。由于版本差异较大，MCP 不足时优先保守占位。

```java
public Object streamQueryPlaceholder() {
    return "Prefer MCP verification before implementing large-result streaming query / cursor API.";
}
```

## Map Result Placeholder

本地源码里能命中 `select(Map.class, ...)` 的内部使用痕迹，但当前更像框架内部工具与关系填充路径，不建议把它直接当成公开首选模板。

```java
public Object mapResultPlaceholder() {
    return "Prefer DTO/VO projection first. If Map projection is required, verify current select(Map.class, ...) behavior against local source before use.";
}
```

## Structured Property Fill Placeholder

结构化属性填充通常涉及值对象、导航属性、聚合 DTO 或结果映射规则，建议先确认源码、注解与代理生成链路。

```java
public Object structuredPropertyFillPlaceholder() {
    return "Prefer MCP verification before implementing structured property fill / value object / navigate mapping.";
}
```

## Create

新增优先落在 Repository，Service 负责业务校验和异常语义。

```java
public long createUser(UserEntity entity) {
    return easyEntityQuery
        .insertable(entity)
        .executeRows();
}
```

## Update

更新优先明确命中条件、版本控制和受影响行数语义。

```java
public long updateUserStatus(Long userId, String status) {
    return easyEntityQuery
        .updatable(UserEntity.class)
        .setColumns(user -> user.status().set(status))
        .where(user -> user.id().eq(userId))
        .executeRows();
}
```

## Delete

删除优先明确逻辑删还是物理删，不要把删除语义隐藏在调用层。

```java
public long removeUser(Long userId) {
    return easyEntityQuery
        .deletable(UserEntity.class)
        .where(user -> user.id().eq(userId))
        .executeRows();
}
```

## Transaction

事务边界默认放在 Service 或业务协调层。

```java
public void createUserWithAudit(CreateUserCommand command) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        userRepository.insert(command.toEntity());
        auditRepository.insert(AuditLogEntity.created("user", command.getUsername()));
        transaction.commit();
    }
}
```

## Insert Or Update Placeholder

插入或者更新往往依赖方言与具体 API，真正落地前优先回 MCP / 源码确认。

```java
public Object insertOrUpdatePlaceholder(UserEntity entity) {
    return "Prefer MCP verification before implementing insert-or-update / upsert DSL.";
}
```

## Batch

Batch 批处理优先明确是批量插入、批量更新还是批量 upsert。

```java
public long batchCreateUsers(List<UserEntity> entities) {
    return easyEntityQuery
        .insertable(entities)
        .batch()
        .executeRows();
}
```

## Dynamic Table Name Placeholder

动态表名通常和分表、租户、时间路由有关，真实实现高度依赖当前版本与项目接入方式。

```java
public Object dynamicTableNamePlaceholder() {
    return "Prefer MCP verification before implementing dynamic table name / sharding route logic.";
}
```

## Native SQL Placeholder

原生 SQL 应作为最后手段；真实入口、结果映射和参数绑定方式请优先回 MCP / 源码确认。

```java
public Object nativeSqlPlaceholder() {
    return "Prefer MCP verification before implementing native SQL execution and mapping.";
}
```

## Java Skeleton

```java
public class UserRepository {

    public UserEntity findById(Long userId) {
        return easyEntityQuery
            .queryable(UserEntity.class)
            .whereById(userId)
            .singleOrNull();
    }

    public PageResult<UserEntity> pageUsers(UserPageRequest request) {
        return easyEntityQuery
            .queryable(UserEntity.class)
            .where(user -> {
                user.status().eq(request.getStatus() != null, request.getStatus());
                user.name().like(request.getKeyword() != null && !request.getKeyword().isBlank(), request.getKeyword());
            })
            .orderBy(user -> {
                user.createTime().desc();
                user.id().desc();
            })
            .toPageResult(request.getPageIndex(), request.getPageSize());
    }

    public long insert(UserEntity entity) {
        return easyEntityQuery
            .insertable(entity)
            .executeRows();
    }

    public long updateName(Long userId, String name) {
        return easyEntityQuery
            .updatable(UserEntity.class)
            .setColumns(user -> user.name().set(name))
            .where(user -> user.id().eq(userId))
            .executeRows();
    }

    public long deleteById(Long userId) {
        return easyEntityQuery
            .deletable(UserEntity.class)
            .where(user -> user.id().eq(userId))
            .executeRows();
    }
}
```

```java
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public UserEntity getUser(Long userId) {
        return userRepository.findById(userId);
    }

    public PageResult<UserEntity> pageUsers(UserPageRequest request) {
        return userRepository.pageUsers(request);
    }

    public void createUser(CreateUserCommand command) {
        userRepository.insert(command.toEntity());
    }

    public void renameUser(Long userId, String name) {
        long rows = userRepository.updateName(userId, name);
        if (rows != 1) {
            throw new IllegalStateException("rename user failed");
        }
    }

    public void removeUser(Long userId) {
        long rows = userRepository.deleteById(userId);
        if (rows != 1) {
            throw new IllegalStateException("remove user failed");
        }
    }
}
```

## Kotlin Skeleton

```kotlin
class UserRepository {

    fun findById(userId: Long): UserEntity? {
        return easyEntityQuery
            .queryable(UserEntity::class.java)
            .whereById(userId)
            .singleOrNull()
    }

    fun pageUsers(request: UserPageRequest): PageResult<UserEntity> {
        return easyEntityQuery
            .queryable(UserEntity::class.java)
            .where { user ->
                user.status().eq(request.status != null, request.status)
                user.name().like(!request.keyword.isNullOrBlank(), request.keyword)
            }
            .orderBy { user ->
                user.createTime().desc()
                user.id().desc()
            }
            .toPageResult(request.pageIndex, request.pageSize)
    }

    fun insert(entity: UserEntity): Long {
        return easyEntityQuery
            .insertable(entity)
            .executeRows()
    }

    fun updateName(userId: Long, name: String): Long {
        return easyEntityQuery
            .updatable(UserEntity::class.java)
            .setColumns { user -> user.name().set(name) }
            .where { user -> user.id().eq(userId) }
            .executeRows()
    }

    fun deleteById(userId: Long): Long {
        return easyEntityQuery
            .deletable(UserEntity::class.java)
            .where { user -> user.id().eq(userId) }
            .executeRows()
    }
}
```

```kotlin
class UserService(
    private val userRepository: UserRepository
) {
    fun getUser(userId: Long): UserEntity? = userRepository.findById(userId)

    fun pageUsers(request: UserPageRequest): PageResult<UserEntity> =
        userRepository.pageUsers(request)

    fun createUser(command: CreateUserCommand) {
        userRepository.insert(command.toEntity())
    }

    fun renameUser(userId: Long, name: String) {
        check(userRepository.updateName(userId, name) == 1L) { "rename user failed" }
    }

    fun removeUser(userId: Long) {
        check(userRepository.deleteById(userId) == 1L) { "remove user failed" }
    }
}
```

## CRUD Checklist

- `Create` 是否依赖唯一键、默认值、审计字段或事务
- `Read` 是否优先走主键、唯一键或明确分页排序
- `Update` 是否校验命中条件、版本字段和受影响行数
- `Delete` 是逻辑删除还是物理删除，是否需要额外确认
- Service 是否负责业务语义，Repository 是否负责 DSL 收口
