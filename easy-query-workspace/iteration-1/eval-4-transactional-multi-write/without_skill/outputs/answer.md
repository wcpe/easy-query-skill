# Easy Query 纯 Java 下单事务（插入 Order + 扣减 Account 余额）

下面是一个**纯 Java（无 Spring）** 的实现：在**同一个事务**里插入订单并扣减账户余额，余额不足或扣款影响行数不对就回滚。

核心思路是用 `easyEntityQuery.transaction()` 拿到一个事务对象，手动 `commit()` / `rollback()`，并在余额不足或更新行数不为 1 时抛异常触发回滚。扣款时用 **SQL 内的条件更新**（`balance = balance - amount WHERE id = ? AND balance >= amount`），把"判断余额是否足够"和"扣款"合并成一条原子语句，避免读改写之间的竞态。

---

## 1. 实体定义

```java
import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Table("t_account")
@EntityProxy
public class Account implements ProxyEntityAvailable<Account, AccountProxy> {
    @Column(primaryKey = true)
    private String id;
    private String name;
    private BigDecimal balance;

    // getter / setter 省略
}
```

```java
import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Table("t_order")
@EntityProxy
public class Order implements ProxyEntityAvailable<Order, OrderProxy> {
    @Column(primaryKey = true)
    private String id;
    private String accountId;
    private BigDecimal amount;
    private String status;
    private LocalDateTime createTime;

    // getter / setter 省略
}
```

> 加了 `@EntityProxy` 后，Easy Query 的 APT 会生成 `AccountProxy` / `OrderProxy` 代理类，编译后即可使用强类型条件。

---

## 2. 初始化 EasyEntityQuery（纯 Java，DataSource）

```java
import com.easy.query.api.proxy.client.DefaultEasyEntityQuery;
import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper;
import com.easy.query.core.api.client.EasyQueryClient;
import com.easy.query.mysql.config.MySQLDatabaseConfiguration;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import javax.sql.DataSource;

public class EasyQueryFactory {

    public static EasyEntityQuery create() {
        HikariConfig hikari = new HikariConfig();
        hikari.setJdbcUrl("jdbc:mysql://127.0.0.1:3306/demo?useSSL=false&characterEncoding=utf-8");
        hikari.setUsername("root");
        hikari.setPassword("root");
        hikari.setDriverClassName("com.mysql.cj.jdbc.Driver");
        hikari.setMaximumPoolSize(10);
        DataSource dataSource = new HikariDataSource(hikari);

        EasyQueryClient client = EasyQueryBootstrapper.defaultBuilderConfiguration()
                .setDefaultDataSource(dataSource)
                .optionConfigure(op -> {
                    // 可按需配置，比如打印 SQL
                    op.setPrintSql(true);
                })
                .useDatabaseConfigure(new MySQLDatabaseConfiguration())
                .build();

        return new DefaultEasyEntityQuery(client);
    }
}
```

---

## 3. 下单逻辑（核心：手动事务）

```java
import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.basic.jdbc.tx.Transaction;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

public class OrderService {

    private final EasyEntityQuery easyEntityQuery;

    public OrderService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    /**
     * 下单：插入订单 + 扣减账户余额，整体一个事务。
     * 余额不足或扣款影响行数不为 1 时回滚并抛异常。
     *
     * @param accountId 账户 id
     * @param amount    订单金额（必须 > 0）
     * @return 生成的订单 id
     */
    public String placeOrder(String accountId, BigDecimal amount) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("订单金额必须大于 0");
        }

        // 开启事务（默认隔离级别 READ_COMMITTED，可传参指定）
        try (Transaction transaction = easyEntityQuery.beginTransaction()) {
            try {
                // 1) 扣减余额：用条件更新把"余额是否足够"和"扣款"合并成原子操作
                //    SQL 等价：UPDATE t_account
                //             SET balance = balance - ?
                //             WHERE id = ? AND balance >= ?
                long affectRows = easyEntityQuery.updatable(Account.class)
                        .setColumns(a -> a.balance().set(a.balance().subtract(amount)))
                        .where(a -> {
                            a.id().eq(accountId);
                            a.balance().ge(amount); // 余额 >= 订单金额 才会命中
                        })
                        .executeRows();

                // 2) 校验扣款影响行数：必须恰好为 1，否则视为余额不足/账户不存在/并发冲突
                if (affectRows != 1) {
                    throw new IllegalStateException(
                            "扣款失败：余额不足或账户不存在，accountId=" + accountId
                                    + ", amount=" + amount + ", affectRows=" + affectRows);
                }

                // 3) 插入订单
                Order order = new Order();
                order.setId(UUID.randomUUID().toString().replace("-", ""));
                order.setAccountId(accountId);
                order.setAmount(amount);
                order.setStatus("PAID");
                order.setCreateTime(LocalDateTime.now());

                long insertRows = easyEntityQuery.insertable(order).executeRows();
                if (insertRows != 1) {
                    throw new IllegalStateException("订单插入失败，insertRows=" + insertRows);
                }

                // 4) 全部成功 -> 提交
                transaction.commit();
                return order.getId();

            } catch (RuntimeException ex) {
                // 任意一步失败 -> 回滚
                transaction.rollback();
                throw ex; // 抛给上层，让调用方知道下单失败
            }
        }
    }
}
```

---

## 4. 调用示例

```java
public class Main {
    public static void main(String[] args) {
        EasyEntityQuery easyEntityQuery = EasyQueryFactory.create();
        OrderService service = new OrderService(easyEntityQuery);

        try {
            String orderId = service.placeOrder("acc_1001", new java.math.BigDecimal("99.50"));
            System.out.println("下单成功，订单号：" + orderId);
        } catch (Exception e) {
            System.out.println("下单失败：" + e.getMessage());
        }
    }
}
```

---

## 关键点说明

1. **事务边界**：用 `easyEntityQuery.beginTransaction()` 返回 `Transaction`，它实现了 `AutoCloseable`，配合 try-with-resources，即使忘记显式处理也能在关闭时自动回滚未提交的事务。手动 `commit()` / `rollback()` 控制提交与回滚。
   - 如需指定隔离级别：`beginTransaction(java.sql.Connection.TRANSACTION_READ_COMMITTED)`。

2. **原子扣款防并发**：扣款的 `where` 里带了 `balance >= amount` 条件，把"检查余额"和"扣款"放进同一条 UPDATE，数据库行锁保证并发安全。不要先 `query` 查余额、在 Java 里判断后再 `update`——那样会有 check-then-act 竞态，可能导致超扣。

3. **影响行数校验**：`executeRows()` 返回受影响行数。扣款行数 != 1 即说明余额不足、账户不存在或被并发改动，立即抛异常回滚。订单插入行数同样校验。

4. **回滚触发**：任何 `RuntimeException`（金额非法、余额不足、行数不对、SQL 异常等）都会进入 catch 执行 `rollback()` 并向上抛出，订单和扣款一并撤销，保证数据一致。

5. **金额类型**：用 `BigDecimal` 表示金额，避免浮点精度问题。

---

## 备选：lambda 事务写法（更简洁，自动提交/回滚）

如果不想手动管理 commit/rollback，可以用 `executeTransaction`（无返回值）或带返回值的写法，闭包正常结束自动提交、抛异常自动回滚：

```java
public String placeOrderV2(String accountId, BigDecimal amount) {
    if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
        throw new IllegalArgumentException("订单金额必须大于 0");
    }
    String[] orderIdHolder = new String[1];

    easyEntityQuery.executeTransaction(() -> {
        long affectRows = easyEntityQuery.updatable(Account.class)
                .setColumns(a -> a.balance().set(a.balance().subtract(amount)))
                .where(a -> {
                    a.id().eq(accountId);
                    a.balance().ge(amount);
                })
                .executeRows();
        if (affectRows != 1) {
            throw new IllegalStateException("扣款失败：余额不足或账户不存在");
        }

        Order order = new Order();
        order.setId(UUID.randomUUID().toString().replace("-", ""));
        order.setAccountId(accountId);
        order.setAmount(amount);
        order.setStatus("PAID");
        order.setCreateTime(LocalDateTime.now());

        if (easyEntityQuery.insertable(order).executeRows() != 1) {
            throw new IllegalStateException("订单插入失败");
        }
        orderIdHolder[0] = order.getId();
    });

    return orderIdHolder[0];
}
```

> 闭包内抛异常 -> 自动 `rollback`；正常返回 -> 自动 `commit`。逻辑等价于第 3 节的手动版本，推荐日常使用这种写法，更不容易漏掉回滚。

---

### 注意事项 / 版本差异

- 上面用的是 `sql-api-proxy`（强类型 Proxy）写法，需要 `@EntityProxy` 注解 + APT 生成代理类。
- 不同 Easy Query 版本里事务 API 命名可能略有差异：常见为 `beginTransaction()` 返回 `Transaction`，以及 `executeTransaction(Runnable)`。如果你的版本方法名不同，思路（手动 commit/rollback 或闭包事务 + 行数校验 + 条件扣款）保持一致即可。
- 表名 / 字段名按你的实际库结构调整 `@Table` / `@Column`。
