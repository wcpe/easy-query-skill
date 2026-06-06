# 下单 + 扣款（单事务，纯 Java，无 Spring）

下单要同时做两件事：插入 `Order`、扣减对应 `Account.balance`，二者必须同生共死。
关键点：

1. 用 easy-query 自带的 `beginTransaction()` + try-with-resources（无 Spring，不能用 `@Transactional`）。
2. **余额不足在 SQL 里拦截**：扣款 `where` 同时带上 `balance >= amount`，余额不够时这条 UPDATE 影响 0 行。
3. 用 `executeRows(1, "...")` 断言「必须恰好扣 1 行」：影响行数不对（账户不存在 / 余额不足 / 被并发改动）直接抛异常 → 触发回滚。
4. `tx.commit()` 不调用，任何提前退出（异常 / return）都会在 `close()` 时自动回滚。

> 把扣款条件做成原子的 `balance >= amount` + 行数断言，是这里的核心：它把「余额不足」和「并发扣款」合并成一次原子检查，避免「先查后改」的竞态。

## 实体

```java
package com.test.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.OrderProxy;     // APT 在 <pkg>.proxy 下生成
import java.math.BigDecimal;
import java.time.LocalDateTime;
import lombok.Data;

@Data
@Table("t_order")
@EntityProxy
public class Order implements ProxyEntityAvailable<Order, OrderProxy> {
    @Column(primaryKey = true)
    private String id;
    private String accountId;
    private BigDecimal amount;
    private LocalDateTime createTime;
}
```

```java
package com.test.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.AccountProxy;   // APT 生成
import java.math.BigDecimal;
import lombok.Data;

@Data
@Table("t_account")
@EntityProxy
public class Account implements ProxyEntityAvailable<Account, AccountProxy> {
    @Column(primaryKey = true)
    private String id;
    private BigDecimal balance;
}
```

## 下单服务

```java
import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.basic.jdbc.tx.Transaction;

public class OrderService {

    private final EasyEntityQuery easyEntityQuery;

    public OrderService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    /**
     * 下单：插入订单 + 扣减账户余额，一个事务内完成。
     * 余额不足或扣款影响行数不为 1 → 抛异常 → 自动回滚。
     */
    public void placeOrder(Order order) {
        try (Transaction tx = easyEntityQuery.beginTransaction()) {

            // 1) 插入订单
            easyEntityQuery.insertable(order).executeRows();

            // 2) 原子扣款：balance >= amount 才扣；否则影响 0 行
            easyEntityQuery.updatable(Account.class)
                    .setColumns(a -> a.balance().decrement(order.getAmount()))   // balance = balance - amount
                    .where(a -> {
                        a.id().eq(order.getAccountId());
                        a.balance().ge(order.getAmount());                       // 余额不足则不命中
                    })
                    .executeRows(1, "扣款失败：账户不存在或余额不足");          // 行数 != 1 → 抛异常 → 回滚

            // 3) 两步都成功才提交；不提交则 close() 时自动回滚
            tx.commit();
        }
        // 异常 / 未 commit 都会在 try-with-resources 的 close() 中自动回滚
    }
}
```

### 想区分「余额不足」和「账户不存在」？

`executeRows(1, ...)` 只告诉你「没扣到 1 行」，分不清原因。若要给出更精确的提示，
可在事务里先用 `singleOrNull()` 查一次余额再判断（注意：仍要把扣款的 `balance >= amount`
留在 UPDATE 里，防止查到改之间的并发扣款）：

```java
public void placeOrder(Order order) {
    try (Transaction tx = easyEntityQuery.beginTransaction()) {
        easyEntityQuery.insertable(order).executeRows();

        Account account = easyEntityQuery.queryable(Account.class)
                .where(a -> a.id().eq(order.getAccountId()))
                .singleOrNull();                      // 业务主键唯一 → single 而非 first
        if (account == null) {
            throw new IllegalStateException("账户不存在");   // 抛出即回滚
        }
        if (account.getBalance().compareTo(order.getAmount()) < 0) {
            throw new IllegalStateException("余额不足");
        }

        easyEntityQuery.updatable(Account.class)
                .setColumns(a -> a.balance().decrement(order.getAmount()))
                .where(a -> {
                    a.id().eq(order.getAccountId());
                    a.balance().ge(order.getAmount());     // 仍保留，挡住并发扣款
                })
                .executeRows(1, "扣款失败：余额已被并发修改");
        tx.commit();
    }
}
```

## 构建 EasyEntityQuery（纯 Java bootstrap，仅供参考）

```java
HikariDataSource dataSource = new HikariDataSource();
dataSource.setJdbcUrl("jdbc:mysql://127.0.0.1:3306/mydb?serverTimezone=GMT%2B8&characterEncoding=utf-8&useSSL=false");
dataSource.setUsername("root");
dataSource.setPassword("root");
dataSource.setDriverClassName("com.mysql.cj.jdbc.Driver");

EasyQueryClient client = EasyQueryBootstrapper.defaultBuilderConfiguration()
        .setDefaultDataSource(dataSource)
        .useDatabaseConfigure(new MySQLDatabaseConfiguration())   // 与 sql-mysql 方言一致
        .build();
EasyEntityQuery easyEntityQuery = new DefaultEasyEntityQuery(client);

new OrderService(easyEntityQuery).placeOrder(order);
```

## 易错点（务必避免）

- **忘记 `tx.commit()`** → 全部静默回滚，看起来「成功」实则没写进去。
- **在 try 里 catch 并吞掉异常** → commit 照常执行，半成品状态被提交。
- **把 `executeRows() == 0` 当成功** → 0 行恰恰代表余额不足 / 账户不存在 / 并发冲突。
- **无 Spring 却用 `@Transactional`**，或在 `beginTransaction()` 外再套 `@Transactional`（双重事务）。
- 金额用 `BigDecimal`，不要用 `double`。
- 事务里不要放远程调用 / 文件 IO / 长等待。

---

**来源**：easy-query skill — `references/transaction.md`（`beginTransaction()` + try-with-resources 的下单扣款范例，含行数断言回滚）、`references/write.md`（`decrement` / `executeRows(expectRows, msg)` / `singleOrNull`）、`references/setup-java.md`（纯 Java bootstrap 与实体）。
基线版本 easy-query 3.1.89-dev；若你的项目版本不同，以项目实际 API 为准。
