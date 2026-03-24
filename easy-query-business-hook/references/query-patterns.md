# Query Patterns

在 MCP 无法提供足够源码或测试证据时，使用本文件作为 easy-query 查询与分页写法的本地降级参考。

## 使用方式

- 先把本文件当成“写法模板索引”，不要直接当成源码事实。
- 如果本文件与 MCP 或当前项目源码冲突，以 MCP / 源码 / 测试为准。
- 输出代码时，优先保留 easy-query 常见链路顺序：`queryable -> where -> orderBy -> select -> toList/toPageResult`。

## Local Source Pointers

继续核对本文件里的查询能力时，优先回看这些本地来源：

- `README.md`
  - `groupBy` / `having` 示例
  - `leftJoin` 示例
  - `union` 示例
  - `exists` 示例
  - `toPageResult` 示例
- `README-zh.md`
  - 与英文 README 对应的中文示例页
- `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest1.java`
  - 聚合与 join 基础用例
- `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest2.java`
  - 多 join、分组、聚合扩展用例
- `sql-test/src/main/java/com/easy/query/test/dameng/DamengQueryTest.java`
  - `toPageResult`、`groupBy` 等查询场景
- `sql-test/src/main/java/com/easy/query/test/mysql8/ManyJoinTest.java`
  - 多表 join、group by、分页投影
- `sql-test/src/main/java/com/easy/query/test/mysql8/MySQL8Test5.java`
  - `distinct`、`leftJoin` 等多样化查询
- `sql-test/src/main/java/com/easy/query/test/EncryptionTest.java`
  - `whereById`、基础 select 路径

## Kotlin Snippets

- Kotlin 项目优先参考这一组模板，再按具体场景回到下方 Java 模板扩展。
- 若项目使用 data class、空安全或扩展函数封装，优先保持项目现有风格，不要强行套 Java 写法。

```kotlin
fun findById(userId: Long): UserEntity? {
    return easyEntityQuery
        .queryable(UserEntity::class.java)
        .whereById(userId)
        .singleOrNull()
}
```

```kotlin
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
```

```kotlin
fun listOrderDetails(shopId: Long): List<OrderDetailDTO> {
    return easyEntityQuery
        .queryable(OrderEntity::class.java)
        .leftJoin(UserEntity::class.java) { order, user -> order.userId().eq(user.id()) }
        .where { order, _ -> order.shopId().eq(shopId) }
        .select(OrderDetailDTO::class.java) { order, user ->
            OrderDetailDTO(
                order.id(),
                order.orderNo(),
                user.name(),
                order.status()
            )
        }
        .toList()
}
```

## 典型模式

### 主键查询

- 优先 `whereById` / `whereByIds`
- 若业务语义要求至多一条，优先 `singleOrNull`
- 本地可回看：
  - `sql-test/src/main/java/com/easy/query/test/EncryptionTest.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/M8SaveTest.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/M8Save2Test.java`

```java
public UserEntity findById(Long userId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .whereById(userId)
        .singleOrNull();
}
```

```java
public List<UserEntity> listByIds(Collection<Long> userIds) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .whereByIds(userIds)
        .toList();
}
```

### 唯一键查询

- 用显式条件表达唯一业务键
- 需要唯一语义时优先 `singleOrNull`，不要默认 `firstOrNull`

```java
public UserEntity findByEmail(String email) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.email().eq(email))
        .singleOrNull();
}
```

### 条件列表

- 可选参数条件要 gated，避免把空条件直接变成宽表扫描
- 过滤、排序、分页尽量下推到 SQL，不要先 `toList()` 再用内存流处理

```java
public List<OrderEntity> listOrders(OrderQueryRequest request) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> {
            order.shopId().eq(request.getShopId() != null, request.getShopId());
            order.status().eq(request.getStatus() != null, request.getStatus());
            order.keyword().like(request.getKeyword() != null && !request.getKeyword().isBlank(), request.getKeyword());
        })
        .orderBy(order -> order.id().desc())
        .toList();
}
```

### exists / count

- 只判断是否存在时优先 `any()`
- 只统计数量时优先 `count()`，不要先拉列表再算

```java
public boolean existsByUsername(String username) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.username().eq(username))
        .any();
}
```

```java
public long countActiveUsers(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> {
            user.shopId().eq(shopId);
            user.status().eq(UserStatus.ACTIVE);
        })
        .count();
}
```

### 主表动态条件

- `whereObject` 只作为主表动态过滤模板使用
- 跨表复杂业务条件优先回到显式 DSL
- 本地可回看：
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable/Filterable1.java`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable3/override/ClientOverrideQueryable3.java`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable4/override/ClientOverrideQueryable4.java`

```java
public List<UserEntity> listUsers(UserQueryRequest request) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .whereObject(request)
        .orderBy(user -> user.id().desc())
        .toList();
}
```

### `IN` 条件查询

- 批量状态、批量主键之外的集合过滤，优先显式 DSL
- 先校验集合非空，避免生成无意义条件

```java
public List<OrderEntity> listByStatuses(Collection<Integer> statuses) {
    if (statuses == null || statuses.isEmpty()) {
        return List.of();
    }
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.status().in(statuses))
        .orderBy(order -> order.id().desc())
        .toList();
}
```

### 分页

- 分页必须有确定性排序
- 业务排序字段不唯一时，追加主键或唯一键作为稳定次序
- 前端可控排序必须经过字段白名单映射
- 本地可回看：
  - `README.md`
  - `README-zh.md`
  - `sql-test/src/main/java/com/easy/query/test/dameng/DamengQueryTest.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/ManyJoinTest.java`

```java
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
```

### 动态排序白名单

- 先把前端字段映射到有限的排序分支
- 不要把原始字段名直接透传进排序 DSL

```java
public PageResult<UserEntity> pageUsersWithSort(UserPageRequest request) {
    var query = easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.shopId().eq(request.getShopId()));

    String sortField = request.getSortField();
    boolean asc = request.isAsc();
    if ("createTime".equals(sortField)) {
        query = query.orderBy(user -> {
            if (asc) {
                user.createTime().asc();
                user.id().asc();
            } else {
                user.createTime().desc();
                user.id().desc();
            }
        });
    } else if ("name".equals(sortField)) {
        query = query.orderBy(user -> {
            if (asc) {
                user.name().asc();
                user.id().asc();
            } else {
                user.name().desc();
                user.id().desc();
            }
        });
    } else {
        query = query.orderBy(user -> user.id().desc());
    }

    return query.toPageResult(request.getPageIndex(), request.getPageSize());
}
```

### 投影查询

- 需要返回轻量结果时优先显式 `select`
- 不要把完整 Entity 无脑透传给上层

```java
public List<UserSummaryDTO> listUserSummaries(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.shopId().eq(shopId))
        .select(UserSummaryDTO.class, user -> new UserSummaryDTO(
            user.id(),
            user.name(),
            user.status()
        ))
        .toList();
}
```

### 聚合统计

- 基础统计优先直接下推到查询层，不要先查列表再在内存里聚合
- 聚合字段、过滤条件、分组维度要保持清晰，不要把业务语义埋进后处理

```java
public long countOrdersByShop(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .count();
}
```

```java
public BigDecimal sumPaidAmount(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> {
            order.shopId().eq(shopId);
            order.status().eq(OrderStatus.PAID);
        })
        .sumBigDecimal(order -> order.payAmount());
}
```

```java
public LocalDateTime maxCreateTime(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .maxOrNull(order -> order.createTime());
}
```

```java
public LocalDateTime minCreateTime(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .minOrNull(order -> order.createTime());
}
```

### `group by` 聚合

- 分组聚合适合报表、统计看板、按状态汇总等场景
- 先确认 DTO 字段与分组列、聚合列一一对应
- 本地可回看：
  - `README.md`
  - `README-zh.md`
  - `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest1.java`
  - `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest2.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/ManyJoinTest.java`

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

### `having` 过滤

- 需要对聚合结果继续筛选时，优先使用 `having`
- `having` 条件应围绕聚合表达式，不要和普通 `where` 条件混淆
- 本地可回看：
  - `README.md`
  - `README-zh.md`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable3/Havingable3.java`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable4/Havingable4.java`

```java
public List<UserOrderSummaryDTO> listActiveOrderUsers(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .groupBy(order -> order.userId())
        .having(order -> order.count().gt(3L))
        .select(UserOrderSummaryDTO.class, order -> new UserOrderSummaryDTO(
            order.userId(),
            null,
            order.count(),
            order.sumBigDecimal(o -> o.payAmount())
        ))
        .toList();
}
```

### `distinct` 去重

- 去重优先明确目标列或投影对象
- 不要先查出重复数据再在内存层 `distinct`
- 本地可回看：
  - `sql-test/src/main/java/com/easy/query/test/mysql8/MySQL8Test5.java`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable3/override/ClientOverrideQueryable3.java`
  - `sql-core/src/main/java/com/easy/query/core/basic/api/select/extension/queryable4/override/ClientOverrideQueryable4.java`

```java
public List<Long> listDistinctUserIds(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .where(order -> order.shopId().eq(shopId))
        .select(Long.class, order -> order.userId())
        .distinct()
        .toList();
}
```

### 多表关联查询

- 关联查询优先把关联条件、过滤条件和投影目标写清楚
- 先确保排序仍然稳定，避免联表分页结果漂移
- 本地可回看：
  - `README.md`
  - `README-zh.md`
  - `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest1.java`
  - `sql-test/src/main/java/com/easy/query/test/BaseEntityQueryAggregateTest2.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/ManyJoinTest.java`

```java
public List<OrderDetailDTO> listOrderDetails(Long shopId) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .leftJoin(UserEntity.class, (order, user) -> order.userId().eq(user.id()))
        .where((order, user) -> order.shopId().eq(shopId))
        .select(OrderDetailDTO.class, (order, user) -> new OrderDetailDTO(
            order.id(),
            order.orderNo(),
            user.name(),
            order.status()
        ))
        .toList();
}
```

### 联表分页 + DTO 投影

- 联表分页比单表更容易出稳定性和性能问题
- 排序字段尽量落在主表或可索引列上

```java
public PageResult<OrderPageDTO> pageOrders(Long shopId, int pageIndex, int pageSize) {
    return easyEntityQuery
        .queryable(OrderEntity.class)
        .leftJoin(UserEntity.class, (order, user) -> order.userId().eq(user.id()))
        .where((order, user) -> order.shopId().eq(shopId))
        .orderBy((order, user) -> {
            order.createTime().desc();
            order.id().desc();
        })
        .select(OrderPageDTO.class, (order, user) -> new OrderPageDTO(
            order.id(),
            order.orderNo(),
            user.name(),
            order.payAmount(),
            order.status()
        ))
        .toPageResult(pageIndex, pageSize);
}
```

### 子查询过滤

- 当条件来自另一张表或中间结果时，可优先考虑子查询过滤
- 子查询模板优先用来表达“先限定集合，再回主查询”的语义

```java
public List<UserEntity> listUsersWithPaidOrders(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.id().in(
            easyEntityQuery
                .queryable(OrderEntity.class)
                .where(order -> {
                    order.shopId().eq(shopId);
                    order.status().eq(OrderStatus.PAID);
                })
                .select(Long.class, order -> order.userId())
        ))
        .orderBy(user -> user.id().desc())
        .toList();
}
```

### `exists` 子查询

- 当业务语义是“主表记录是否存在匹配的子记录”时，优先考虑 `exists` 子查询
- 这种写法通常比先查子表 ID 列表再拼回主表更贴近 SQL 语义
- 本地可回看：
  - `README.md`
  - `README-zh.md`
  - `sql-core/src/main/java/com/easy/query/core/expression/parser/core/base/core/filter/SubQueryPredicate.java`

```java
public List<UserEntity> listUsersWithPendingOrders(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .where(user -> user.shopId().eq(shopId))
        .where(user -> user.exists(
            easyEntityQuery
                .queryable(OrderEntity.class)
                .where(order -> {
                    order.userId().eq(user.id());
                    order.status().eq(OrderStatus.CREATED);
                })
        ))
        .orderBy(user -> user.id().desc())
        .toList();
}
```

### `case when` 占位模板

- `case when` 属于 README 中可见的高级投影主题，但当前本地源码检索没有给出足够直接的公共 DSL 落点
- 降级时先保留占位说明，真实落地前优先回 MCP、README 示例和当前版本源码确认

```java
public Object caseWhenProjectionPlaceholder() {
    return "Prefer MCP or local README/source verification before implementing caseWhen projection DSL.";
}
```

### `union` 占位模板

- `union` / `union all` 的具体 DSL 形式在不同版本里可能存在差异
- MCP 不足时，只把它作为降级占位思路，真正落代码前优先回 MCP / 源码确认当前 API

```java
public Object unionUsersAndGuestsPlaceholder() {
    return "Prefer MCP verification before implementing easy-query union/unionAll DSL in production code.";
}
```

### 主表 + 聚合 DTO

- 需要“主对象 + 聚合值”时，优先直接投影成 DTO
- 不要先查主表，再对每条数据循环做一次 count/sum

```java
public List<UserOrderSummaryDTO> listUserOrderSummaries(Long shopId) {
    return easyEntityQuery
        .queryable(UserEntity.class)
        .leftJoin(OrderEntity.class, (user, order) -> user.id().eq(order.userId()))
        .where((user, order) -> user.shopId().eq(shopId))
        .groupBy((user, order) -> {
            user.id();
            user.name();
        })
        .select(UserOrderSummaryDTO.class, (user, order) -> new UserOrderSummaryDTO(
            user.id(),
            user.name(),
            order.count(),
            order.sumBigDecimal(o -> o.payAmount())
        ))
        .toList();
}
```
