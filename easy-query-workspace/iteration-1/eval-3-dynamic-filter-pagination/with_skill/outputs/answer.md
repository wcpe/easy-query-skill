# 订单后台分页查询（easy-query, Java）

按可选的 `name`(模糊)、可选的 `status`、可选的创建时间区间过滤 `Order`，分页返回。

要点：
- **空参数不拼条件**：用 easy-query 的「门控重载」`.like(condition, value)` / `.eq(condition, value)`，以及时间区间的 `rangeClosed(beginCond, begin, endCond, end)`。当 condition 为 `false` 时该条件被直接跳过——不会拼进 SQL，也不需要任何字符串拼接。
- **分页稳定**：`toPageResult` 必须配 `orderBy`，且因为 `createTime` 不唯一，追加主键 `id` 作为 tiebreaker，避免翻页时行重复/遗漏。
- **不把实体直接返回接口**：用 `select(...)` 投影到 DTO，避免泄露 version / 逻辑删除 / 审计字段。

---

## 实体 Order

```java
package com.test.entity;

import com.easy.query.core.annotation.*;
import com.easy.query.core.basic.extension.logicdel.LogicDeleteStrategyEnum;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.OrderProxy;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Table("t_order")
@EntityProxy
public class Order implements ProxyEntityAvailable<Order, OrderProxy> {

    @Column(primaryKey = true)
    private String id;

    /** 订单名称（用于模糊查询） */
    private String name;

    /** 订单状态：0 待支付 / 1 已支付 / 2 已取消 ... */
    private Integer status;

    private LocalDateTime createTime;

    @LogicDelete(strategy = LogicDeleteStrategyEnum.BOOLEAN)
    private Boolean deleted;
}
```

> `OrderProxy` 是编译期生成的（Java 走 APT），不要手写。若提示找不到 `OrderProxy`，那是构建配置问题，不是代码问题。

## 查询入参

```java
package com.test.query;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class OrderPageQuery {
    private String name;             // 可选：模糊
    private Integer status;          // 可选：精确
    private LocalDateTime beginTime; // 可选：创建时间下界（含）
    private LocalDateTime endTime;   // 可选：创建时间上界（含）

    private Integer pageIndex = 1;   // 1-based
    private Integer pageSize = 20;
}
```

## 返回 DTO（不直接返回实体）

```java
package com.test.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class OrderItemDTO {
    private String id;
    private String name;
    private Integer status;
    private LocalDateTime createTime;
}
```

## 分页查询逻辑

```java
import com.easy.query.core.api.client.EasyEntityQuery;
import com.easy.query.core.api.pagination.EasyPageResult;
import com.easy.query.core.proxy.core.draft.proxy.Select;
import com.easy.query.core.util.EasyStringUtil;
import com.test.dto.OrderItemDTO;
import com.test.entity.Order;
import com.test.query.OrderPageQuery;

public class OrderQueryService {

    private final EasyEntityQuery easyEntityQuery;

    public OrderQueryService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    public EasyPageResult<OrderItemDTO> page(OrderPageQuery req) {
        return easyEntityQuery.queryable(Order.class)
                // 空参数不拼条件：门控重载，condition=false 时整条跳过
                .where(o -> {
                    o.name().like(EasyStringUtil.isNotBlank(req.getName()), req.getName());
                    o.status().eq(req.getStatus() != null, req.getStatus());
                    o.createTime().rangeClosed(
                            req.getBeginTime() != null, req.getBeginTime(),
                            req.getEndTime()   != null, req.getEndTime());   // [begin, end] 闭区间
                })
                // 分页必须有稳定排序：createTime 不唯一 → 追加 id 做 tiebreaker
                .orderBy(o -> {
                    o.createTime().desc();
                    o.id().desc();
                })
                // 投影到 DTO，避免把实体（含 deleted 等字段）泄露给接口
                .select(OrderItemDTO.class, s -> Select.of(
                        s.id().as(OrderItemDTO::getId),
                        s.name().as(OrderItemDTO::getName),
                        s.status().as(OrderItemDTO::getStatus),
                        s.createTime().as(OrderItemDTO::getCreateTime)
                ))
                .toPageResult(req.getPageIndex(), req.getPageSize());
    }
}
```

调用方拿到 `EasyPageResult<OrderItemDTO>` 后用 `getData()` / `getTotal()` 取数据和总数：

```java
EasyPageResult<OrderItemDTO> result = orderQueryService.page(req);
List<OrderItemDTO> rows = result.getData();
long total              = result.getTotal();
```

---

## 为什么这样写（对应任务三个诉求）

1. **空参数不拼进条件** —— 每个谓词都用「布尔门控」重载：`like(cond, v)`、`eq(cond, v)`、`rangeClosed(beginCond, begin, endCond, end)`。当 `name` 为空、`status` 为 null、时间端点为 null 时，对应条件不会进入 SQL。绝不用字符串拼接，也不需要手写 `if`。
2. **分页稳定** —— `toPageResult(pageIndex, pageSize)` 始终配 `orderBy`；由于 `createTime` 可能重复，追加唯一主键 `id` 作为 tiebreaker，保证翻页结果确定、不重不漏。`pageIndex` 是 1-based。
3. **时间区间** —— `rangeClosed` 是闭区间 `[begin, end]`；两端各自带门控，单边传入（只有开始或只有结束）也能正确生成单边条件。

## 备选：用 `where(condition, lambda)` 门控整条 where

如果更偏好「整条 where 子句级别」的门控，可改成：

```java
easyEntityQuery.queryable(Order.class)
        .where(EasyStringUtil.isNotBlank(req.getName()), o -> o.name().like(req.getName()))
        .where(req.getStatus() != null,    o -> o.status().eq(req.getStatus()))
        .where(req.getBeginTime() != null, o -> o.createTime().ge(req.getBeginTime()))
        .where(req.getEndTime() != null,   o -> o.createTime().le(req.getEndTime()))
        .orderBy(o -> { o.createTime().desc(); o.id().desc(); })
        .select(OrderItemDTO.class, s -> Select.of(
                s.id().as(OrderItemDTO::getId),
                s.name().as(OrderItemDTO::getName),
                s.status().as(OrderItemDTO::getStatus),
                s.createTime().as(OrderItemDTO::getCreateTime)))
        .toPageResult(req.getPageIndex(), req.getPageSize());
```

两种写法等价，主版本（谓词级门控 + `rangeClosed`）更紧凑且区间语义更清晰。

---

### 来源与版本说明
- 模式来自本 skill 的 `references/query.md`（动态/可选条件的门控重载、`rangeClosed`、`toPageResult` 配稳定 `orderBy`+tiebreaker、`select` 投影到 DTO）与 `references/entity-mapping.md`（实体/`@EntityProxy` 注解）。
- skill 基线版本 easy-query **3.1.89-dev**。若你项目版本不同，以你项目实际 API 为准。
- 注意：`Order` 是 SQL 关键字，已用 `@Table("t_order")` 显式指定表名规避。
- 逻辑删除（`deleted`）由 easy-query 自动加 `where deleted = false`，无需手动处理。
```
