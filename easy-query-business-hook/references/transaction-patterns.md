# Transaction Patterns

在 MCP 无法明确给出事务接入细节时，使用本文件作为事务边界与协调方式的本地降级参考。

## 使用方式

- 先判断是否真的需要事务，不要把所有查询都包进事务。
- 事务边界默认跟随业务边界，通常放在 Service 层。
- 如果宿主框架已有事务体系，优先参与宿主事务。

## Local Source Pointers

继续核对事务相关内容时，优先回看这些本地来源：

- `sql-core/src/main/java/com/easy/query/core/basic/jdbc/conn/impl/DefaultConnectionManager.java`
  - `beginTransaction(...)`
- `sql-db-support/sql-dameng/src/main/java/com/easy/query/dameng/migration/DamengCodeFirstCommand.java`
  - Code First 命令内部事务
- `sql-db-support/sql-oracle/src/main/java/com/easy/query/oracle/migration/OracleCodeFirstCommand.java`
  - Code First 命令内部事务

## Kotlin Snippets

- Kotlin 事务模板优先保持 service 边界清晰，异常语义明确。
- `use` 风格或 `try/finally` 风格都可以，优先跟随项目现有写法。

```kotlin
fun createOrder(command: CreateOrderCommand) {
    try {
        easyQueryClient.beginTransaction().use { transaction ->
            orderRepository.insert(command.toEntity())
            orderLogRepository.insert(OrderLogEntity.created(command.orderNo))
            transaction.commit()
        }
    } catch (ex: Exception) {
        throw IllegalStateException("create order failed", ex)
    }
}
```

```kotlin
fun cancelOrder(orderId: Long) {
    easyQueryClient.beginTransaction().use { transaction ->
        val order = orderRepository.mustFindById(orderId)
        check(order.status == OrderStatus.CREATED) { "order status not cancellable" }

        val rows = orderRepository.cancel(orderId, order.version)
        check(rows == 1L) { "cancel order concurrency conflict" }
        transaction.commit()
    }
}
```

## 典型模式

### 单服务事务

- 在一个 Service 方法内协调查询校验、写入、日志和回滚语义

```java
public void createOrder(CreateOrderCommand command) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        orderRepository.insert(command.toEntity());
        orderLogRepository.insert(OrderLogEntity.created(command.getOrderNo()));
        transaction.commit();
    } catch (Exception ex) {
        throw new RuntimeException("create order failed", ex);
    }
}
```

### 跨 Repository 协调

- 多个 Repository 的一致性写操作要么放进同一事务，要么明确给出补偿策略

```java
public void payOrder(PayOrderCommand command) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        OrderEntity order = orderRepository.mustFindByOrderNo(command.getOrderNo());
        paymentRepository.insert(command.toPayment(order.getId()));
        orderRepository.markPaid(order.getId(), order.getVersion());
        transaction.commit();
    } catch (Exception ex) {
        throw new RuntimeException("pay order failed", ex);
    }
}
```

### 查询后插入防重

- 先查后插这类逻辑要么依赖唯一键，要么放进事务并在失败时正确翻译异常
- 不能把“查不到”直接当成“后面一定能插入”

```java
public void createDepartment(CreateDepartmentCommand command) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        boolean exists = departmentRepository.existsByCode(command.getCode());
        if (exists) {
            throw new IllegalStateException("department code duplicated");
        }
        departmentRepository.insert(command.toEntity());
        transaction.commit();
    }
}
```

### 先查后改保护

- 需要先查后改时，把查询、校验、更新放进同一业务事务，并补版本或行数断言
- 不要把“先查状态再更新”拆成两个独立无保护步骤

```java
public void cancelOrder(Long orderId) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        OrderEntity order = orderRepository.mustFindById(orderId);
        if (order.getStatus() != OrderStatus.CREATED) {
            throw new IllegalStateException("order status not cancellable");
        }
        long rows = orderRepository.cancel(orderId, order.getVersion());
        if (rows != 1) {
            throw new IllegalStateException("cancel order concurrency conflict");
        }
        transaction.commit();
    }
}
```

### 不应开事务的场景

- 纯列表查询
- 报表导出
- 无原子性要求的只读读取
- 含远程调用或长时间等待的链路

```java
public PageResult<UserEntity> pageUsers(UserPageRequest request) {
    return userRepository.pageUsers(request);
}
```

### 事务内不要混长耗时步骤

- 先把数据库状态变更和长耗时外部步骤拆开
- 发送通知、远程调用、文件上传等尽量不要放在事务持有期内

```java
public void completeOrderAndNotify(Long orderId) {
    try (Transaction transaction = easyQueryClient.beginTransaction()) {
        long rows = orderRepository.complete(orderId);
        if (rows != 1) {
            throw new IllegalStateException("complete order failed");
        }
        transaction.commit();
    }
    notificationService.sendOrderCompleted(orderId);
}
```
