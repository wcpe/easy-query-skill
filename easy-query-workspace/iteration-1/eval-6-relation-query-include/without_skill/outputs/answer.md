# Easy Query 一对多关系：SysUser → BankCard 的 include 查询（避免 N+1）

## 思路

Easy Query 用 `@Navigate` 注解在实体上声明关系，查询时用 `.include(...)` 把关联数据一次性带出来。
Easy Query 的 `include` 不是用 JOIN 把行展开，而是先查主表，再对子表发一条 `IN (...)` 的批量查询，然后在内存里组装。
所以无论用户有多少张卡，整个过程就是 **2 条 SQL**（1 条查 user，1 条 `WHERE bank_card.uid IN (...)`），从根本上避免 N+1。

---

## 1. 实体定义

### 主表 SysUser

```java
import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Navigate;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.enums.RelationTypeEnum;
import com.easy.query.core.proxy.ProxyEntityAvailable;
// 由 APT 生成的代理类
import com.example.entity.proxy.SysUserProxy;

import java.util.List;

@Table("t_sys_user")
@EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {

    @Column(primaryKey = true)
    private String id;

    private String name;

    private Integer age;

    /**
     * 一对多：一个用户有多张银行卡
     * selfProperty   : 当前实体(SysUser)用于关联的属性 -> id
     * targetProperty : 目标实体(BankCard)用于关联的属性 -> uid
     */
    @Navigate(
        value = RelationTypeEnum.OneToMany,
        selfProperty = {"id"},
        targetProperty = {"uid"}
    )
    private List<BankCard> bankCards;

    // getter / setter 省略
}
```

### 子表 BankCard

```java
import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Navigate;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.enums.RelationTypeEnum;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.example.entity.proxy.BankCardProxy;

@Table("t_bank_card")
@EntityProxy
public class BankCard implements ProxyEntityAvailable<BankCard, BankCardProxy> {

    @Column(primaryKey = true)
    private String id;

    /** 外键，指向 SysUser.id */
    private String uid;

    private String cardNo;

    private String bankName;

    // 可选：反向导航，方便从卡查用户（多对一）
    @Navigate(
        value = RelationTypeEnum.ManyToOne,
        selfProperty = {"uid"},
        targetProperty = {"id"}
    )
    private SysUser user;

    // getter / setter 省略
}
```

> 说明：`@Navigate` 中 `selfProperty` / `targetProperty` 写的是**实体属性名**，不是数据库列名。
> 如果是单键关联，也可以简写为 `selfProperty = "id"`、`targetProperty = "uid"`（注解里其实是字符串数组，单值时用 `{...}` 或直接字符串都行）。

---

## 2. 查询：一次性把用户和银行卡都加载出来

```java
import com.easy.query.api.proxy.client.EasyEntityQuery;
import java.util.List;

public class UserService {

    private final EasyEntityQuery easyEntityQuery;

    public UserService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    /** 查所有用户，并一起加载每个用户的银行卡 */
    public List<SysUser> listUsersWithCards() {
        return easyEntityQuery.queryable(SysUser.class)
                // include 一对多：u.bankCards()
                .include(u -> u.bankCards())
                .toList();
    }

    /** 带条件 + 子集合排序的写法 */
    public List<SysUser> listActiveUsersWithCards() {
        return easyEntityQuery.queryable(SysUser.class)
                .where(u -> u.age().ge(18))
                .include(u -> u.bankCards(), card -> card
                        .orderBy(c -> c.cardNo().asc())   // 对子集合排序
                        // .where(c -> c.bankName().eq("ICBC")) // 也可只加载部分卡
                )
                .toList();
    }
}
```

执行后生成的 SQL 大致是：

```sql
-- 第 1 条：查主表
SELECT id, name, age FROM t_sys_user WHERE age >= 18;

-- 第 2 条：根据上一步拿到的 id 批量查子表（关键，避免 N+1）
SELECT id, uid, card_no, bank_name
FROM t_bank_card
WHERE uid IN (?, ?, ?, ...);
```

Easy Query 自动按 `uid` 把卡分组回填到对应用户的 `bankCards` 字段。

---

## 关键点 / 注意事项

1. **避免 N+1 的本质**：`include` 走的是「主查询 + 子查询 IN 批量」两段式，固定 2 条 SQL（多层 include 则每层一条），不会随用户数量线性增长。
2. **代理类**：实体加 `@EntityProxy` 并实现 `ProxyEntityAvailable`，编译时 APT 会生成 `XxxProxy`，`u.bankCards()`、`u.age()` 这些是代理类上的方法。需要确保注解处理器（`sql-processor` / `apt`）已配置。
3. **多层关联**：可以链式 `.include(u -> u.bankCards()).include(...)`，或在 include 内部继续 `then`/嵌套 include 加载孙级关系。
4. **只查关系字段映射要对得上**：`selfProperty` 是 SysUser 的主键属性 `id`，`targetProperty` 是 BankCard 上的外键属性 `uid`，方向不要写反。
5. 如果你只想要「有银行卡的用户」做过滤而不加载卡，用关系子查询（`where(u -> u.bankCards().any(...))`）；要把卡数据带回来才用 `include`。
