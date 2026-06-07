# 拦截器（Interceptor）

拦截器是 easy-query 的核心扩展点：在 insert/update 执行前改写实体或 SQL，或给查询/更新/删除自动追加
WHERE 条件。最常见的两个用途是**自动填充审计字段**（创建人/时间、更新人/时间）和**多租户隔离**。

## 何时用 / 不用

需要"对一类实体统一加行为"时用拦截器：审计字段自动填充、租户过滤、软过滤、统一改写更新列。
单次、一次性的逻辑不要用拦截器，直接在业务代码里写。

## 拦截器家族（包 `com.easy.query.core.basic.extension.interceptor`）

所有拦截器都继承基接口 `Interceptor`，必须实现 `name()` 与 `apply(Class<?> entityClass)`，可选 `order()`
（默认 100，越小越先执行）和 `enable()`：

| 接口 | 触发时机 | 关键方法 |
|------|----------|----------|
| `EntityInterceptor` | 实体 insert / update 执行前 | `configureInsert(cls, builder, entity)` / `configureUpdate(cls, builder, entity)` |
| `PredicateFilterInterceptor` | 查询/更新/删除拼条件时 | `configure(cls, builder, WherePredicate<Object>)` |
| `UpdateSetInterceptor` | 表达式 update 拼 SET 时 | `configure(cls, builder, ColumnSetter<Object>)` |
| `UpdateEntityColumnInterceptor` | 实体 update 选列时 | `configure(cls, builder, ColumnOnlySelector<Object>, entity)` |

`apply(entityClass)` 决定这个拦截器作用于哪些实体（返回 true 才生效）。

## 注册方式

- **Spring Boot**：拦截器类加 `@Component` 即自动注册。
- **纯 Java**：在 bootstrap 阶段拿到 `QueryConfiguration` 调 `applyInterceptor(...)`（easy-query 自带测试
  即如此：`configuration.applyInterceptor(new MyEntityInterceptor());`）。

## 用途一：自动填充审计字段（EntityInterceptor）

实体里把审计字段标上 `@UpdateIgnore` / `@InsertIgnore`（见 `entity-mapping.md`），由拦截器统一赋值。

```java
@Table("t_topic")
@EntityProxy
public class Topic implements ProxyEntityAvailable<Topic, TopicProxy> {
    @Column(primaryKey = true) private String id;
    private String title;
    @UpdateIgnore private LocalDateTime createTime;  // 只在 insert 填，update 不动
    @UpdateIgnore private String createBy;
    private LocalDateTime updateTime;                // insert + update 都填
    private String updateBy;
    @UpdateIgnore private String tenantId;
}
```

```java
import com.easy.query.core.basic.extension.interceptor.EntityInterceptor;
import com.easy.query.core.expression.sql.builder.EntityInsertExpressionBuilder;
import com.easy.query.core.expression.sql.builder.EntityUpdateExpressionBuilder;

// @Component   // Spring Boot 下加这行即可自动注册
public class AuditInterceptor implements EntityInterceptor {
    @Override
    public void configureInsert(Class<?> entityClass, EntityInsertExpressionBuilder builder, Object entity) {
        Topic t = (Topic) entity;
        if (t.getCreateTime() == null) t.setCreateTime(LocalDateTime.now());
        if (t.getCreateBy() == null)   t.setCreateBy(CurrentUserHelper.getUserId());
        if (t.getUpdateTime() == null) t.setUpdateTime(LocalDateTime.now());
        if (t.getUpdateBy() == null)   t.setUpdateBy(CurrentUserHelper.getUserId());
    }
    @Override
    public void configureUpdate(Class<?> entityClass, EntityUpdateExpressionBuilder builder, Object entity) {
        Topic t = (Topic) entity;
        t.setUpdateTime(LocalDateTime.now());
        t.setUpdateBy(CurrentUserHelper.getUserId());
    }
    @Override public String name() { return "AuditInterceptor"; }
    @Override public boolean apply(Class<?> entityClass) { return Topic.class.isAssignableFrom(entityClass); }
}
```

`configureInsert/Update` 改的是**实体对象**，只对"传实体的" `insertable(entity)` / `updatable(entity)` 生效。
对"表达式 update"（`updatable(Topic.class).setColumns(...)`）要追加列，用下面的 `UpdateSetInterceptor`。

## 用途二：表达式 update 自动补列（UpdateSetInterceptor）

```java
import com.easy.query.core.basic.extension.interceptor.UpdateSetInterceptor;
import com.easy.query.core.expression.parser.core.base.ColumnSetter;

public class UpdateAuditInterceptor implements UpdateSetInterceptor {
    @Override
    public void configure(Class<?> entityClass, EntityUpdateExpressionBuilder builder, ColumnSetter<Object> columnSetter) {
        // 若调用方没显式 set updateTime/updateBy，则补上（判断是否已在 SET 段里，避免覆盖）
        columnSetter.set("updateBy", CurrentUserHelper.getUserId());
        columnSetter.set("updateTime", LocalDateTime.now());
    }
    @Override public String name() { return "UpdateAuditInterceptor"; }
    @Override public boolean apply(Class<?> entityClass) { return Topic.class.isAssignableFrom(entityClass); }
}
```
（一个类可以同时 `implements EntityInterceptor, UpdateSetInterceptor` 兼顾两条路径。）

## 用途三：多租户 / 软过滤（PredicateFilterInterceptor）

给一类实体的查询/更新/删除自动追加 `WHERE tenant_id = ?`，业务层无需每次手写：

```java
import com.easy.query.core.basic.extension.interceptor.PredicateFilterInterceptor;
import com.easy.query.core.expression.parser.core.base.WherePredicate;

public class TenantInterceptor implements PredicateFilterInterceptor {
    @Override
    public void configure(Class<?> entityClass, LambdaEntityExpressionBuilder builder, WherePredicate<Object> wherePredicate) {
        wherePredicate.eq("tenantId", CurrentTenantHelper.getTenantId());
    }
    @Override public String name() { return "TenantInterceptor"; }
    @Override public boolean apply(Class<?> entityClass) {
        return TenantAware.class.isAssignableFrom(entityClass);  // 例如所有实现某标记接口的实体
    }
}
```

## 临时关闭拦截器

单次查询/写入可用 `.noInterceptor()` 关闭全部，或 `.useInterceptor(name)` / `.noInterceptor(name)` 精确控制。
标记接口 `ProtectedInterceptor` 的拦截器不会被 `noInterceptor()` 移除（适合租户这种安全相关的）。

## 常见错误

- `apply()` 永远返回 `true` 却只想作用于一类实体 → 误伤其它实体。用 `isAssignableFrom` 或标记接口收窄。
- 期望 `configureInsert/Update`（EntityInterceptor）能影响"表达式 update" → 不会，表达式 update 走
  `UpdateSetInterceptor`。
- 审计字段没加 `@UpdateIgnore`，导致每次 update 都覆盖 createBy/createTime。
- 多租户用普通 `PredicateFilterInterceptor` 但被 `noInterceptor()` 关掉 → 安全相关的应实现 `ProtectedInterceptor`。

## Sources
- 源码验证: 接口 @ `com.easy.query.core.basic.extension.interceptor`（`Interceptor`/`EntityInterceptor`/
  `PredicateFilterInterceptor`/`UpdateSetInterceptor`/`UpdateEntityColumnInterceptor`）；`sql-test/.../
  interceptor/MyEntityInterceptor.java`、`.../entity/TopicInterceptor.java`、`BaseTest.java`
  (`configuration.applyInterceptor(...)`)。`@UpdateIgnore`/`@InsertIgnore` @ `com.easy.query.core.annotation`。
- 官方文档: `easy-query-doc/src/adv/interceptor.md`。
