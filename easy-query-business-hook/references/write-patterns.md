# Write Patterns

在 MCP 不足以确认插入、更新、删除、版本控制等行为时，使用本文件作为本地降级参考。

## 使用方式

- 优先确认当前任务是单条写入、批量写入还是条件写入。
- 本文件只提供保守模式，不代表 easy-query 所有版本都完全一致。
- 如果找到 MCP 测试或源码实现，立即用更高证据替换本文件结论。

## Local Source Pointers

继续核对本文件里的写入能力时，优先回看这些本地来源：

- `sql-test/src/main/java/com/easy/query/test/BaseTest.java`
  - `disableLogicDelete()`、`allowDeleteStatement(true)`、Code First 初始化
- `sql-test/src/main/java/com/easy/query/test/EncryptionTest.java`
  - 基础更新、主键路径
- `sql-test/src/main/java/com/easy/query/test/mysql8/M8SaveTest.java`
  - `whereById`、批量保存前后的数据确认
- `sql-test/src/main/java/com/easy/query/test/mysql8/M8Save2Test.java`
  - `whereByIds`、批量场景
- `sql-test/src/main/java/com/easy/query/test/dameng/DamengBaseTest.java`
  - `allowDeleteStatement(true)`、Code First 预处理
- `sql-core/src/main/java/com/easy/query/core/expression/parser/core/base/ColumnSetter.java`
  - `setIncrement(...)`
- `sql-platform/sql-api-proxy/src/main/java/com/easy/query/api/proxy/entity/update/abstraction/AbstractExpressionUpdatable.java`
  - `withVersion(...)`

## Kotlin Snippets

- Kotlin 写入模板优先保持空安全、不可变参数和项目现有异常风格。
- 如果项目已经封装 Repository 扩展函数，优先复用封装，不要把所有 DSL 都摊回 Service。

```kotlin
fun createUser(entity: UserEntity): Long {
    return easyEntityQuery
        .insertable(entity)
        .executeRows()
}
```

```kotlin
fun updateUserPhone(userId: Long, phone: String): Long {
    return easyEntityQuery
        .updatable(UserEntity::class.java)
        .setColumns { user -> user.phone().set(phone) }
        .where { user -> user.id().eq(userId) }
        .executeRows()
}
```

```kotlin
fun increaseLoginCount(userId: Long): Long {
    return easyEntityQuery
        .updatable(UserEntity::class.java)
        .setColumns { user -> user.loginCount().setIncrement(1) }
        .where { user -> user.id().eq(userId) }
        .executeRows()
}
```

```kotlin
fun createUserIdempotent(entity: UserEntity) {
    try {
        easyEntityQuery
            .insertable(entity)
            .executeRows()
    } catch (ex: Exception) {
        throw IllegalStateException("create user maybe duplicated by unique key", ex)
    }
}
```

## 典型模式

### 插入

- 先确认是否依赖唯一键、默认值、回填或事务
- 不要在应用层先查全表再决定插入

```java
public long createUser(UserEntity entity) {
    return easyEntityQuery
        .insertable(entity)
        .executeRows();
}
```

### 按状态条件更新

- 状态流转类写入要把旧状态一起放进 `where`
- 这样比“先查状态再裸更新”更适合做基础并发保护

```java
public long markOrderPaid(Long orderId) {
    return easyEntityQuery
        .updatable(OrderEntity.class)
        .setColumns(order -> order.status().set(OrderStatus.PAID))
        .where(order -> {
            order.id().eq(orderId);
            order.status().eq(OrderStatus.CREATED);
        })
        .executeRows();
}
```

### 更新

- 更新条件必须完整
- 返回 0 行时要判断语义，不要默认成功
- 涉及并发时，优先考虑版本控制或受影响行数断言

```java
public long updateUserPhone(Long userId, String phone) {
    return easyEntityQuery
        .updatable(UserEntity.class)
        .setColumns(user -> user.phone().set(phone))
        .where(user -> user.id().eq(userId))
        .executeRows();
}
```

```java
public long completeOrder(Long orderId, Integer version) {
    return easyEntityQuery
        .updatable(OrderEntity.class)
        .setColumns(order -> order.status().set(OrderStatus.COMPLETED))
        .withVersion(version)
        .where(order -> order.id().eq(orderId))
        .executeRows();
}
```

### 更新表达式

- 自增、自减、累加余额、累计次数这类写法优先考虑更新表达式
- 不要把“先查当前值再加减后写回”作为默认路径
- 本地可回看：
  - `sql-core/src/main/java/com/easy/query/core/expression/parser/core/base/ColumnSetter.java`

```java
public long increaseLoginCount(Long userId) {
    return easyEntityQuery
        .updatable(UserEntity.class)
        .setColumns(user -> user.loginCount().setIncrement(1))
        .where(user -> user.id().eq(userId))
        .executeRows();
}
```

### 删除

- 删除操作必须先审查命中条件
- 物理删除相关放宽开关要谨慎，不能把底层保护当成上层偷懒理由
- 本地可回看：
  - `sql-test/src/main/java/com/easy/query/test/BaseTest.java`
  - `sql-test/src/main/java/com/easy/query/test/dameng/DamengBaseTest.java`
  - `sql-core/src/main/java/com/easy/query/core/expression/sql/builder/impl/DeleteExpressionBuilder.java`

```java
public long deleteById(Long userId) {
    return easyEntityQuery
        .deletable(UserEntity.class)
        .where(user -> user.id().eq(userId))
        .executeRows();
}
```

### 软删语义占位

- 如果项目实体启用了逻辑删除，优先保留默认删除路径
- 需要恢复、跳过逻辑删除或做物理删时，先回到 MCP / 源码确认当前版本能力

```java
public long removeOrder(Long orderId) {
    return easyEntityQuery
        .deletable(OrderEntity.class)
        .where(order -> order.id().eq(orderId))
        .executeRows();
}
```

### 逻辑删除恢复占位

- 逻辑删除恢复通常依赖具体版本是否公开恢复 DSL，或是否要通过普通更新把删除标记回写
- MCP 不足时，优先把它标记为“待源码确认”的恢复模板，而不是直接编造 API

```java
public Object restoreLogicDeletedUserPlaceholder(Long userId) {
    return "Prefer MCP verification before implementing logic delete restore DSL for userId=" + userId;
}
```

### 批量写

- 先区分“要求全成功”还是“允许部分成功”
- 注意驱动返回行数的精度差异
- 本地可回看：
  - `sql-test/src/main/java/com/easy/query/test/mysql8/M8Save2Test.java`
  - `sql-test/src/main/java/com/easy/query/test/mysql8/M8SaveTest.java`

```java
public long batchInsert(List<UserEntity> entities) {
    return easyEntityQuery
        .insertable(entities)
        .batch()
        .executeRows();
}
```

### 批量条件更新

- 批量更新优先把命中范围明确收窄
- 涉及状态或版本时，不要因为批量操作就放弃约束条件

```java
public long batchDisableUsers(Collection<Long> userIds) {
    if (userIds == null || userIds.isEmpty()) {
        return 0L;
    }
    return easyEntityQuery
        .updatable(UserEntity.class)
        .setColumns(user -> user.status().set(UserStatus.DISABLED))
        .where(user -> user.id().in(userIds))
        .executeRows();
}
```

### 受影响行数断言

- 业务要求“必须命中 1 行”时，优先把 0 行更新视为异常信号
- 这类模板适合状态迁移、乐观锁更新、幂等确认

```java
public void disableUser(Long userId) {
    long rows = easyEntityQuery
        .updatable(UserEntity.class)
        .setColumns(user -> user.status().set(UserStatus.DISABLED))
        .where(user -> user.id().eq(userId))
        .executeRows();
    if (rows != 1) {
        throw new IllegalStateException("disable user failed, affected rows=" + rows);
    }
}
```

### 幂等插入降级模板

- 当项目要求唯一业务键幂等，但 MCP 暂时无法确认 `onConflictThen` 等能力时，先把“数据库唯一键 + 异常翻译”作为保守降级策略
- 如果后续确认了方言与 API 能力，再替换成真正的 upsert / conflict 写法

```java
public void createUserIdempotent(UserEntity entity) {
    try {
        easyEntityQuery
            .insertable(entity)
            .executeRows();
    } catch (Exception ex) {
        throw new IllegalStateException("create user maybe duplicated by unique key", ex);
    }
}
```

### conflict / upsert 占位模板

- `onConflictThen`、`insertOrUpdate`、批量 upsert 等能力很依赖方言与版本
- MCP 不足时，不要伪造具体链式 API；先保留明确的占位说明，并在最终实现前回源码确认

```java
public Object upsertUserPlaceholder(UserEntity entity) {
    return "Prefer MCP verification before implementing dialect-specific easy-query upsert/conflict DSL for " + entity.getUsername();
}
```

```java
public Object batchUpsertUsersPlaceholder(List<UserEntity> entities) {
    return "Prefer MCP verification before implementing batch upsert/conflict DSL, size=" + entities.size();
}
```
