# 基于请求对象的查询（whereObject / 动态排序 / 扁平映射）

把"前端传来的查询请求对象"直接喂给 easy-query，自动拼条件、排序，并把关联表字段扁平映射进 VO。
适合后台列表/检索接口，省掉大量手写 `where` 分支。

## 何时用 / 不用

请求参数固定、字段较多、想"对象驱动"地拼条件时用 `whereObject`。逻辑分支复杂、需要 OR/嵌套/
权限拼接的，回到显式 DSL（见 `query.md`）。两者可混用：`whereObject(req).where(o -> ...)`。

## 1. whereObject —— 用注解声明每个字段如何过滤

在请求 DTO 的字段上加 `@EasyWhereCondition`（包 `com.easy.query.core.annotation`），然后
`queryable(...).whereObject(请求对象)`。字段为空（null/空串）时该条件自动跳过。

```java
import com.easy.query.core.annotation.EasyWhereCondition;
import com.easy.query.core.annotation.EasyWhereCondition.Condition;

@Data
public class SysUserQueryRequest {
    @EasyWhereCondition(type = Condition.LIKE)            // name LIKE ?
    private String name;
    @EasyWhereCondition(type = Condition.LIKE)
    private String phone;
    @EasyWhereCondition(type = Condition.EQUAL)           // account = ?
    private String account;
    @EasyWhereCondition(type = Condition.RANGE_LEFT_CLOSED, propName = "createTime")  // createTime >= ?
    private LocalDateTime createTimeBegin;
    @EasyWhereCondition(type = Condition.RANGE_RIGHT_CLOSED, propName = "createTime") // createTime <= ?
    private LocalDateTime createTimeEnd;
}
```

```java
List<SysUser> list = easyEntityQuery.queryable(SysUser.class)
        .whereObject(request)                  // 按上面的注解自动拼条件，空字段跳过
        .where(o -> o.deleted().eq(false))     // 可继续叠加显式条件
        .orderBy(o -> o.createTime().desc())
        .toList();
```

`@EasyWhereCondition` 关键属性：
- `type`：条件类型，默认 `Condition.DEFAULT`。可选值含 `EQUAL` / `NOT_EQUAL` / `LIKE` /
  `LIKE_MATCH_LEFT` / `LIKE_MATCH_RIGHT` / `GREATER_THAN(_EQUAL)` / `LESS_THAN(_EQUAL)` / `IN` / `NOT_IN` /
  `RANGE_LEFT_CLOSED` / `RANGE_RIGHT_CLOSED` / `RANGE_OPEN` / `RANGE_CLOSED` 等。**建议显式写 type**，别依赖默认。
- `propName`：当 DTO 字段名 ≠ 实体属性名时指定（如 `createTimeBegin`/`createTimeEnd` 都映射到 `createTime`，
  组成区间）。多列用 `propNames`。
- `tableIndex`：多表查询时该条件作用于第几张表（默认 0，主表）。
- `allowEmptyStrings`：默认 false，空串视为"无此条件"；true 则空串也参与。

调试时用 `.whereObject(req).toSQL()` 看生成的 SQL 是否符合预期。

## 2. 动态排序（orderByObject）

前端传"排序字段+方向"时，让请求对象实现 `ObjectSort`（包 `com.easy.query.core.api.dynamic.sort`），在
`configure(ObjectSortBuilder)` 里把字段映射成排序项，再 `.orderByObject(请求对象)`。**务必用
`builder.allowed(...)` 或自己的白名单约束可排序字段**——严格模式只能挡非法字段，不等于业务白名单。

```java
import com.easy.query.core.api.dynamic.sort.ObjectSort;
import com.easy.query.core.api.dynamic.sort.ObjectSortBuilder;
import com.easy.query.core.enums.OrderByModeEnum;

@Data
public class BlogSortRequest implements ObjectSort {
    private String sort;     // 排序字段
    private Boolean asc;     // 是否升序
    @Override
    public void configure(ObjectSortBuilder builder) {
        if (EasyStringUtil.isNotBlank(sort)) {
            builder.orderBy(sort, asc == null || asc);                       // 升/降序
            // builder.orderBy(sort, asc == null || asc, OrderByModeEnum.NULLS_LAST); // 控制 NULL 顺序
        }
    }
}

List<BlogEntity> list = easyEntityQuery.queryable(BlogEntity.class)
        .whereObject(filterRequest)        // 可与 whereObject 组合
        .orderByObject(sortRequest)        // 动态排序
        .toList();
```

多字段排序：在 `configure` 里循环多次 `builder.orderBy(prop, asc, OrderByModeEnum.NULLS_LAST)`。
`ObjectSortBuilder` 还有 `allowed(prop)` / `notAllowed(prop)` 做字段白/黑名单。`orderByObject` 由
`Orderable1` 提供，也有 `orderByObject(boolean condition, ObjectSort)` 的带条件重载。

## 3. @NavigateFlat —— 把关联表字段扁平进 VO

VO 里想直接拿到关联对象的某个字段（而不是嵌套对象），用 `@NavigateFlat`（包
`com.easy.query.core.annotation`），`pathAlias` 指定导航路径。前提：实体上有对应的 `@Navigate` 关系
（见 `relation-query.md`）。

```java
@Data
public class SysUserCardVO {
    private String id;
    private String name;
    private Integer age;

    @NavigateFlat(pathAlias = "firstCard.code")     // 取关联 firstCard 的 code 列
    private String cardCode;
    @NavigateFlat(pathAlias = "firstCard.openTime")
    private LocalDateTime openTime;
}
```
查询时 `select` 到该 VO，框架自动按导航路径取关联字段，无需手写 join。可与 `@Column(conversion=...)`
叠加对扁平字段再做值转换。

## 常见错误

- `whereObject` 不写 `type`、依赖默认行为 → 显式声明 `EQUAL`/`LIKE`/`RANGE_*` 更可控。
- 区间查询忘了用 `propName` 把 `xxxBegin`/`xxxEnd` 都指向同一实体属性。
- 动态排序把前端字段名直接透传（无白名单）→ 注入/越权风险。
- `@NavigateFlat` 的 `pathAlias` 路径与实体 `@Navigate` 属性名对不上。

## Sources
- 源码验证: `@EasyWhereCondition`（含嵌套枚举 `Condition`）@ `com.easy.query.core.annotation`
  (`sql-test/.../doc/dto/SysUserQueryRequest.java`，用法 `.whereObject(request)`)；`ObjectSort` @
  `com.easy.query.core.api.dynamic.sort`；`@NavigateFlat` @ `com.easy.query.core.annotation`
  (`sql-test/.../mysql8/vo/SysUserFirstCardDTO.java`)。
- 官方文档: `easy-query-doc/src/dto-query/{filter,sort,map1,map2,map3}.md`。
