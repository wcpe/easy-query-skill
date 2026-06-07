# 计算属性（派生列 / 数据库计算列）

"计算属性"指实体里有一个字段，它的值不是普通列，而是**由 SQL 表达式、其它列、甚至关联子查询算出来的**。
easy-query 把这类属性分两大类：

- **内存计算**（读出来后在 Java 侧转换）：枚举、JSON、集合 → 用 `@Column(conversion = ...)`，见
  `type-mapping.md`。
- **数据库计算**（在 SQL 里算）：拼接列、函数、状态判断、跨表统计 → 用 `@Column(sqlExpression = ...)` 或
  `@Column(sqlConversion = ...)`，本文件讲这一类。

数据库计算列通常配 `@InsertIgnore @UpdateIgnore`（它不是真实可写列），按需加 `autoSelect = false`
（默认不查、显式 select 才算，适合较贵的跨表统计）。

## 1. 简单表达式列 —— `@Column(sqlExpression = @ColumnSQLExpression(...))`

最轻量：直接给一段 SQL 模板 + 参数列。适合 `CONCAT`、简单运算等。

```java
import com.easy.query.core.annotation.*;

@Data
@Table("t_user_extra")
@EntityProxy
public class UserExtra implements ProxyEntityAvailable<UserExtra, UserExtraProxy> {
    @Column(primaryKey = true) private String id;
    private String firstName;
    private String lastName;

    @InsertIgnore
    @UpdateIgnore
    @Column(sqlExpression = @ColumnSQLExpression(sql = "CONCAT({0},{1})", args = {
            @ExpressionArg(prop = "firstName"),
            @ExpressionArg(prop = "lastName"),
    }))
    private String fullName;   // SELECT 时 = CONCAT(first_name, last_name)
}
```
`@ColumnSQLExpression` / `@ExpressionArg` 都在 `com.easy.query.core.annotation`。`{0}`/`{1}` 按 `args` 顺序
替换为对应属性的列。

## 2. 表达式转换器 —— `@Column(sqlConversion = ColumnValueSQLConverter.class)`

需要更复杂的逻辑（CASE WHEN、日期函数、AES 等）时，实现 `ColumnValueSQLConverter`
（包 `com.easy.query.core.basic.extension.conversion`）。三个核心方法：
`selectColumnConvert`（查询时怎么取）、`propertyColumnConvert`（作为条件/属性引用时怎么写）、
`valueConvert`（写入/比较值时怎么处理）；`isRealColumn()` 返回该属性是否对应真实物理列。

```java
@Data
@Table("t_certificate")
@EntityProxy
public class Certificate implements ProxyEntityAvailable<Certificate, CertificateProxy> {
    @Column(primaryKey = true) private String id;
    private String name;
    private String invalidTime;

    // 根据 invalidTime 距今天数算出状态枚举：纯数据库计算，非真实列
    @Column(sqlConversion = CertStatusColumnValueSQLConverter.class)
    @InsertIgnore @UpdateIgnore
    private CertStatusEnum status;
}

public class CertStatusColumnValueSQLConverter implements ColumnValueSQLConverter {
    @Override public boolean isRealColumn() { return false; }          // 非物理列
    @Override public boolean isMergeSubQuery() { return false; }
    @Override public void selectColumnConvert(TableAvailable table, ColumnMetadata col,
            SQLPropertyConverter conv, QueryRuntimeContext ctx) {
        SQLFunc fx = ctx.fx();
        SQLFunction days = fx.duration(x -> x.column(table, "invalidTime").sqlFunc(fx.now()), DateTimeDurationEnum.Days);
        SQLFunction expr = fx.anySQLFunction("(CASE WHEN {0}>30 THEN 1 WHEN {0}>=0 THEN 2 ELSE 3 END)", c -> c.sqlFunc(days));
        conv.sqlNativeSegment(expr.sqlSegment(table), context -> {
            expr.consume(context.getSQLNativeChainExpressionContext());
            context.setAlias(col.getName());
        });
    }
    @Override public void propertyColumnConvert(TableAvailable table, ColumnMetadata col,
            SQLPropertyConverter conv, QueryRuntimeContext ctx) { /* 同上但不 setAlias */ }
    @Override public void valueConvert(TableAvailable table, ColumnMetadata col, SQLParameter p,
            SQLPropertyConverter conv, QueryRuntimeContext ctx, boolean isCompareValue) {
        conv.sqlNativeSegment("{0}", context -> context.value(p));
    }
}
```
对于"数据库列加密"（写时 `AES_ENCRYPT`、读时 `AES_DECRYPT`）也是同样的 `ColumnValueSQLConverter`
模式，`isRealColumn()` 返回 true（它对应真实密文列），在 `selectColumnConvert`/`valueConvert` 里包
解密/加密函数。这是"SQL 层加密"，与 `type-mapping.md` 里的 `@Encryption`（Java 层加密）是两条不同路线。

## 3. 跨表统计列 —— 子查询计算

`isMergeSubQuery()` 返回 true 时，转换器可以用一个关联子查询当计算值，常见于"班级的学生数"这类聚合：

```java
@Table("school_class")
@Data
@EntityProxy
public class SchoolClass implements ProxyEntityAvailable<SchoolClass, SchoolClassProxy> {
    @Column(primaryKey = true) private String id;
    private String name;

    @Navigate(value = RelationTypeEnum.OneToMany, targetProperty = "classId")
    private List<SchoolStudent> students;

    @Column(sqlConversion = StudentSizeColumnValueSQLConverter.class, autoSelect = false)  // 默认不查，贵
    @InsertIgnore @UpdateIgnore
    private Long studentSize;   // = (SELECT COUNT(id) FROM school_student WHERE class_id = school_class.id)
}
```
转换器里用 `ctx.getSQLClientApiFactory().createQueryable(SchoolStudent.class, ctx)` 构造子查询，
`where(t -> t.eq(new SimpleEntitySQLTableOwner<>(table), "classId", "id"))` 关联外层主键，再 `columnCount`。
完整实现见官方文档。

## 常见错误

- 计算列忘了 `@InsertIgnore @UpdateIgnore` → 框架当成可写列，insert/update 报错或写错。
- 较贵的跨表统计列没加 `autoSelect = false` → 每次查询都带上昂贵子查询。
- 把数据库计算（`sqlConversion`/`sqlExpression`）和内存转换（`conversion`）混为一谈——前者在 SQL 里算、
  能参与 where/order，后者只在读出后转换。

## Sources
- 源码验证: `@ColumnSQLExpression` / `@ExpressionArg` @ `com.easy.query.core.annotation`；
  `ColumnValueSQLConverter` @ `com.easy.query.core.basic.extension.conversion`；`@Column` 属性
  `sqlExpression` / `sqlConversion` / `autoSelect`；`sql-test/.../entity/school/SchoolClassAggregateProp.java`
  (跨表统计 + `autoSelect=false` + `@Insert/UpdateIgnore`)。
- 官方文档: `easy-query-doc/src/prop/{simple-sql-prop,sql-column-prop,status-prop,combine-prop,
  cross-table-prop,json-prop,enum-prop}.md`。
