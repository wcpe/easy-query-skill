# SysUser 一对多加载 BankCard（用 `@Navigate` + `.include` 避免 N+1）

在 easy-query 里，加载关联对象的惯用方式是**导航属性**：在实体上用 `@Navigate` 声明关系，查询时用 `.include(...)` 触发预加载。`.include(...)` 会把关联当成一条**独立的批量查询**执行，所以不会产生 N+1（每个父实体单独查一次子表的那种）。

## 1. 实体定义

### SysUser（一的一方，持有 `List<BankCard>`）

```java
package com.test.entity;

import com.easy.query.core.annotation.*;
import com.easy.query.core.enums.RelationTypeEnum;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.SysUserProxy;
import lombok.Data;

import java.util.List;

@Data
@Table("t_sys_user")
@EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {

    @Column(primaryKey = true)
    private String id;

    private String username;
    private String phone;

    /**
     * 一对多：一个用户有多张银行卡。
     * selfProperty   = 本实体（SysUser）的关联列  -> id
     * targetProperty = 对方实体（BankCard）的关联列 -> userId
     */
    @Navigate(value = RelationTypeEnum.OneToMany,
              selfProperty = {"id"},
              targetProperty = {"userId"})
    private List<BankCard> bankCards;
}
```

### BankCard（多的一方，外键 `userId` 指回用户）

```java
package com.test.entity;

import com.easy.query.core.annotation.*;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.BankCardProxy;
import lombok.Data;

@Data
@Table("t_bank_card")
@EntityProxy
public class BankCard implements ProxyEntityAvailable<BankCard, BankCardProxy> {

    @Column(primaryKey = true)
    private String id;

    @Column(value = "user_id")   // 外键列，指向 SysUser.id
    private String userId;

    private String code;         // 卡号
    private String type;         // 卡类型，如 储蓄卡 / 信用卡
}
```

要点：
- `@Navigate` 来自 `com.easy.query.core.annotation`，`RelationTypeEnum` 是其 `value`，表示基数（这里是 `OneToMany`）。
- `selfProperty` 是**本实体**的关联列，`targetProperty` 是**对方实体**的关联列，方向不要写反。
- `bankCards` 是导航属性，本身不是数据库列，框架知道它是 `@Navigate` 不会当成普通字段映射。
- 两个实体都必须 `implements ProxyEntityAvailable<...>` 才会生成对应的 `Proxy`（APT/KSP 编译期生成），DSL 才能用 `user.bankCards()` 这种强类型访问器。

## 2. 查询：查用户并预加载银行卡

```java
List<SysUser> users = easyEntityQuery.queryable(SysUser.class)
        .include(user -> user.bankCards())   // 预加载每个用户的银行卡（独立批量查询，无 N+1）
        .toList();

// 之后 user.getBankCards() 已经填充好了
for (SysUser u : users) {
    List<BankCard> cards = u.getBankCards();
    // ...
}
```

执行后框架会发两条 SQL：一条查 `t_sys_user`，一条用 `WHERE user_id IN (...)` 一次性批量查出所有用户的银行卡，再回填到各自的 `bankCards`。**不是**每个用户查一次。

## 3. 常见变体

加 `where` 过滤主表用户，关联照样预加载：

```java
List<SysUser> users = easyEntityQuery.queryable(SysUser.class)
        .where(user -> user.username().like("张"))
        .include(user -> user.bankCards())
        .toList();
```

只加载满足条件的银行卡（在 `include` 内对关联再过滤），并可在 `where` 里基于关系做条件：

```java
List<SysUser> users = easyEntityQuery.queryable(SysUser.class)
        .include(user -> user.bankCards().where(bc -> bc.type().eq("储蓄卡")))
        .where(user -> {
            // 只保留“拥有储蓄卡”的用户（关系条件，仍走批量子查询，不是内存过滤）
            user.bankCards().where(bc -> bc.type().eq("储蓄卡")).any();
        })
        .toList();
```

## 注意事项

- **不要**自己写 `for` 循环逐个用户再查银行卡 —— 那才是 N+1。声明 `@Navigate` 后一律用 `.include(...)`。
- Spring Boot 下可在配置里开 `easy-query.print-nav-sql: true`，能看到生成的导航 SQL，确认是批量查询。
- 如果是反向（`BankCard` 查所属用户，一对多的“多”方查“一”方），用 `RelationTypeEnum.ManyToOne`，`selfProperty = {"userId"}`、`targetProperty = {"id"}`，持有单个 `SysUser` 而非列表。

---
来源：easy-query skill `references/relation-query.md`（`@Navigate` 一对多 + `.include` 批量预加载，源码验证）与 `references/entity-mapping.md`（实体/代理模型）。基线版本 3.1.89-dev —— 若你的项目版本不同，以项目实际为准。`RelationTypeEnum` 在不同版本可能位于 `com.easy.query.core.enums` 或 `...annotation`，import 报错时按 IDE 提示调整即可。
