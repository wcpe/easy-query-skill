# Easy Query 后台分页查询接口（订单 Order 动态过滤）

下面是一个用 [easy-query](https://github.com/dromara/easy-query) 实现的后台分页查询逻辑。需求：

- 可选 `name`（模糊匹配）
- 可选 `status`（精确匹配）
- 可选创建时间区间 `createTimeStart` / `createTimeEnd`
- 分页返回，空参数不拼进 SQL 条件，分页稳定（确定性排序）

核心要点：easy-query 的链式条件方法都支持一个 `condition`（布尔）重载，只有当 condition 为 `true` 时该条件才会被拼进 SQL。利用这个特性即可优雅地实现“空参数不拼条件”，无需手写一堆 `if`。

---

## 1. 实体类 Order

```java
package com.example.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.example.entity.proxy.OrderProxy;

import java.time.LocalDateTime;

@Table("t_order")
@EntityProxy
public class Order implements ProxyEntityAvailable<Order, OrderProxy> {

    @Column(primaryKey = true)
    private String id;

    /** 订单名称 / 单号，用于模糊查询 */
    private String name;

    /** 订单状态：0=待支付 1=已支付 2=已取消 ... */
    private Integer status;

    /** 创建时间 */
    private LocalDateTime createTime;

    // getter / setter 省略，实际项目用 lombok @Data 即可

    @Override
    public Class<OrderProxy> proxyTableClass() {
        return OrderProxy.class;
    }
}
```

> `OrderProxy` 由 easy-query 的 APT 注解处理器（`@EntityProxy`）在编译期自动生成，提供类型安全的属性引用（`o.name()`、`o.status()`、`o.createTime()` 等）。

---

## 2. 查询参数 DTO

```java
package com.example.dto;

import java.time.LocalDateTime;

public class OrderQueryRequest {

    /** 名称模糊，可空 */
    private String name;

    /** 状态精确，可空 */
    private Integer status;

    /** 创建时间起（含），可空 */
    private LocalDateTime createTimeStart;

    /** 创建时间止（含），可空 */
    private LocalDateTime createTimeEnd;

    /** 页码，从 1 开始 */
    private Integer pageIndex = 1;

    /** 每页大小 */
    private Integer pageSize = 20;

    // getter / setter 省略
}
```

---

## 3. 分页查询逻辑（Service）

```java
package com.example.service;

import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.basic.api.select.Query;
import com.easy.query.core.basic.extension.track.OrderByModeEnum;
import com.easy.query.core.util.StringUtil;
import com.easy.query.core.basic.api.select.Page; // PageResult
import com.example.dto.OrderQueryRequest;
import com.example.entity.Order;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class OrderQueryService {

    private final EasyEntityQuery easyEntityQuery;

    public OrderQueryService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    public Page<Order> pageQuery(OrderQueryRequest req) {

        String name = req.getName();
        Integer status = req.getStatus();
        LocalDateTime start = req.getCreateTimeStart();
        LocalDateTime end = req.getCreateTimeEnd();

        // 参数兜底，保证分页参数稳定合法
        int pageIndex = (req.getPageIndex() == null || req.getPageIndex() < 1) ? 1 : req.getPageIndex();
        int pageSize  = (req.getPageSize()  == null || req.getPageSize()  < 1) ? 20 : req.getPageSize();
        // 上限保护，避免一次拉太多
        if (pageSize > 200) {
            pageSize = 200;
        }

        boolean hasName   = StringUtil.isNotBlank(name);   // null 和空白都视为“未传”
        boolean hasStatus = status != null;
        boolean hasStart  = start != null;
        boolean hasEnd    = end != null;

        return easyEntityQuery.queryable(Order.class)
                .where(o -> {
                    // 第一个参数是 condition：为 false 时该条件根本不会拼进 SQL
                    o.name().like(hasName, name);              // 模糊：LIKE %name%
                    o.status().eq(hasStatus, status);          // 精确
                    o.createTime().ge(hasStart, start);        // >= start
                    o.createTime().le(hasEnd, end);            // <= end
                })
                // 稳定排序：先按业务字段（创建时间倒序），再用唯一主键兜底，保证翻页顺序确定
                .orderBy(o -> {
                    o.createTime().desc();
                    o.id().asc(); // tie-breaker，避免相同 createTime 时跨页记录乱序/重复
                })
                // toPageResult 会自动执行 count + 分页查询；count 时会自动剥离 orderBy
                .toPageResult(pageIndex, pageSize);
    }
}
```

`Page<Order>`（即 `PageResult`）返回内容包含：

- `getTotal()`：满足条件的总记录数
- `getData()`：当前页数据列表

---

## 4. Controller

```java
package com.example.controller;

import com.easy.query.core.basic.api.select.Page;
import com.example.dto.OrderQueryRequest;
import com.example.entity.Order;
import com.example.service.OrderQueryService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin/order")
public class OrderController {

    private final OrderQueryService orderQueryService;

    public OrderController(OrderQueryService orderQueryService) {
        this.orderQueryService = orderQueryService;
    }

    @PostMapping("/page")
    public Page<Order> page(@RequestBody OrderQueryRequest req) {
        return orderQueryService.pageQuery(req);
    }
}
```

---

## 生成的 SQL 说明

- **全部参数都为空**时（前端只传了分页参数）：

  ```sql
  -- count
  SELECT COUNT(*) FROM t_order;
  -- 数据
  SELECT id, name, status, create_time
  FROM t_order
  ORDER BY create_time DESC, id ASC
  LIMIT 20 OFFSET 0;
  ```

  WHERE 子句完全不出现，因为所有 condition 都是 `false`。

- **传入 name + status + 时间区间**时：

  ```sql
  SELECT id, name, status, create_time
  FROM t_order
  WHERE name LIKE '%xxx%'
    AND status = ?
    AND create_time >= ?
    AND create_time <= ?
  ORDER BY create_time DESC, id ASC
  LIMIT 20 OFFSET 0;
  ```

---

## 关键设计说明（为什么这样写）

1. **空参数不拼条件**
   easy-query 每个条件方法（`like` / `eq` / `ge` / `le` …）的第一个 `boolean` 重载即“条件生效开关”。`false` 时该条件被整体忽略，不会产生任何 SQL 片段，也不会产生 `1=1` 这类无意义条件。这比手写 `if (xxx != null) wrapper.eq(...)` 更干净。

2. **字符串用 `StringUtil.isNotBlank` 判断**
   避免把空字符串 `""` 当成有效模糊条件（否则会生成 `LIKE '%%'`，相当于全表扫描却又像有过滤，容易踩坑）。

3. **分页稳定（确定性排序）**
   分页若没有确定的排序，数据库返回顺序不保证，翻页时可能出现某条记录重复出现或漏掉。这里用 `createTime DESC` 作为业务排序，再加 `id ASC` 作为 tie-breaker（唯一键兜底），保证排序是全序、确定的，翻页结果稳定。

4. **分页参数兜底**
   对 `pageIndex` / `pageSize` 做了非空、最小值、最大值保护，避免负数 offset、`pageSize=0` 或恶意超大 `pageSize` 拖垮数据库。

5. **`toPageResult` 自动处理 count**
   easy-query 的 `toPageResult` 会自动先发一条优化过的 `COUNT` 查询（自动去掉 `ORDER BY`），再发分页数据查询，无需手动拆两段。total=0 时也不会再发第二条数据查询。

---

## 备注 / 可选增强

- 时间区间若希望“右开区间”（`< end`），把 `le` 换成 `lt` 即可。
- 若需要区间合法性校验（start > end 直接返回空），可在 service 入口加一行判断。
- 若 status 是枚举，建议 DTO 用枚举类型并在实体上配合 `@Column(value = ..., conversion = ...)` 做转换。
- 若担心深翻页（OFFSET 很大）性能问题，可改用游标/keyset 分页（基于 `id` 或 `createTime + id` 的 `where ... > lastValue`），但常规后台管理分页用上面的 offset 分页足够。
