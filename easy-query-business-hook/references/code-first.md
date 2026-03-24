# Code First

在 MCP 暂时无法提供 easy-query Code First 的完整源码或测试证据时，使用本文件作为本地降级参考。

## Source Truth First

- Code First 相关结论必须优先来自源码、测试和官方仓库内文档，而不是二手博客或模糊记忆。
- 当前已知可优先回查的证据点：
  - `MigrationTest`
  - `src/code-first/readme.md`
  - `@Table`
  - `@Column`
  - `@EntityProxy`
- 已被现有证据确认的 Code First 基本事实：
  - 可以生成 `CREATE TABLE`
  - 可以生成 rename / add / change 迁移 SQL
  - `syncTableCommand` 有明显安全边界
  - 默认 sync 只做相对安全的同步动作，危险操作不会默认全自动执行

如果 MCP 缺失，降级模板也必须尽量贴着这些已知事实写，不能伪造自动迁移、删表、无损重命名之类的“全自动能力”。

## Local Source Pointers

继续核对 Code First 内容时，优先回看这些本地来源：

- `sql-core/src/main/java/com/easy/query/core/annotation/Table.java`
- `sql-core/src/main/java/com/easy/query/core/annotation/Column.java`
- `sql-core/src/main/java/com/easy/query/core/annotation/EntityProxy.java`
- `sql-core/src/main/java/com/easy/query/core/basic/api/database/DatabaseCodeFirst.java`
- `sql-core/src/main/java/com/easy/query/core/basic/api/database/DefaultDatabaseCodeFirst.java`
- `sql-test/src/main/java/com/easy/query/test/MigrationTest.java`
- `sql-test/src/main/java/com/easy/query/test/BaseTest.java`
- `sql-test/src/main/java/com/easy/query/test/dameng/DamengBaseTest.java`
- `README.md`
- `README-zh.md`

## Quick Start

快速开始阶段，优先完成三件事：

1. 定义实体与字段注解
2. 确认代理生成入口与宿主初始化流程
3. 用测试或只读迁移命令确认 schema 变化是否符合预期

建议最小流程：

- 先定义 `@Table`、`@Column`、`@EntityProxy`
- 再补主键、版本号、逻辑删除、审计字段
- 最后才接 Code First 初始化或同步命令

## API Overview

以下内容是当前可写进降级参考、且尽量贴近源码事实的 Code First 元数据能力：

### `@Table`

已证实字段：

- `value`
- `schema`
- `ignoreProperties`
- `shardingInitializer`
- `oldName`
- `comment`
- `keyword`

结论：

- 表名、schema、忽略属性、旧表名、注释、关键字开关属于真实存在的元数据能力
- 涉及分片初始化器时，要注意它不等于“任意动态表名运行时切换”

### `@Column`

已证实字段：

- `primaryKey`
- `generatedKey`
- `value`
- `conversion`
- `sqlConversion`
- `generatedSQLColumnGenerator`
- `complexPropType`
- `autoSelect`
- `typeHandler`
- `primaryKeyGenerator`
- `exist`
- `nullable`
- `dbType`
- `dbDefault`
- `comment`
- `oldName`
- `length`
- `scale`
- `sqlExpression`
- `jdbcType`

结论：

- `@Column` 不只是列名映射，还承担了主键、类型转换、类型处理器、迁移元数据和 SQL 表达式配置能力
- 列重命名相关信息至少可以通过 `oldName` 表达，但真正迁移行为仍要以测试与当前版本实现为准

### `@EntityProxy`

已证实：

- 它是代码生成入口，不是运行时元注解
- 相关字段包括 `value`、`ignoreProperties`、`version`、`revision`、`generatePackage`

结论：

- Code First 与代理生成链路是相关的，不应只盯着实体字段本身

## Quick Start Template

### Java

```java
@Table(value = "t_user", comment = "user table")
@EntityProxy
public class UserEntity {

    @Column(primaryKey = true)
    private Long id;

    @Column(value = "user_name", length = 64, comment = "username")
    private String username;

    @Column(length = 64)
    private String nickname;

    @Column(length = 32, dbDefault = "'INIT'")
    private String status;

    @Column
    private LocalDateTime createTime;

    @Version
    private Integer version;

    @LogicDelete
    private Boolean deleted;

    // getters / setters
}
```

### Kotlin

```kotlin
@Table(value = "t_user", comment = "user table")
@EntityProxy
class UserEntity {

    @Column(primaryKey = true)
    var id: Long? = null

    @Column(value = "user_name", length = 64, comment = "username")
    var username: String? = null

    @Column(length = 64)
    var nickname: String? = null

    @Column(length = 32, dbDefault = "'INIT'")
    var status: String? = null

    @Column
    var createTime: LocalDateTime? = null

    @Version
    var version: Int? = null

    @LogicDelete
    var deleted: Boolean? = null
}
```

## Custom Parsing

如果你说的“自定义解析”是字段级自定义转换或列解析，那么当前已知最接近源码事实的入口主要在这些注解能力上：

- `conversion`
- `sqlConversion`
- `typeHandler`
- `complexPropType`
- `generatedSQLColumnGenerator`

这意味着降级时可以保守认为：

- Java 对象字段到数据库列值的转换是可配置主题
- SQL 层转换与类型处理器是不同关注点
- 复杂属性解析与普通标量列解析不能混成一类

### Custom Parsing Template

```java
@Table("t_user_profile")
@EntityProxy
public class UserProfileEntity {

    @Column(primaryKey = true)
    private Long id;

    @Column(conversion = UserProfileConverter.class)
    private UserProfile profile;

    @Column(typeHandler = JsonTypeHandler.class)
    private String extJson;
}
```

```kotlin
@Table("t_user_profile")
@EntityProxy
class UserProfileEntity {

    @Column(primaryKey = true)
    var id: Long? = null

    @Column(conversion = UserProfileConverter::class)
    var profile: UserProfile? = null

    @Column(typeHandler = JsonTypeHandler::class)
    var extJson: String? = null
}
```

说明：

- 这里的类名是降级模板，表达的是“当前源码证据表明 conversion / typeHandler 这类入口存在”
- 真正的 converter / handler 接口签名和注册方式，落地前仍应回 MCP / 源码确认

## Dynamic Table / Column Sync

这部分必须非常保守，且一切以源码和测试为准。

### 当前可以保守确认的点

- `@Table.oldName` 可用于表达旧表名
- `@Column.oldName` 可用于表达旧列名
- `@Table.shardingInitializer` 存在，说明表级初始化和分片相关元数据是现实能力
- `MigrationTest` 与 `code-first/readme.md` 共同表明 rename / add / change 迁移 SQL 是被覆盖的主题
- `syncTableCommand` 默认只做相对安全的同步动作

### 必须避免的误导

- 不要把“支持 `oldName`”直接翻译成“任意自动无损重命名一定成功”
- 不要把“有分片初始化器”直接翻译成“运行时动态表名任意切换且自动迁移”
- 不要把“能做列同步”翻译成“危险列变更默认自动执行”

### Rename-aware Template

```java
@Table(value = "t_user", oldName = "user")
@EntityProxy
public class UserEntity {

    @Column(primaryKey = true)
    private Long id;

    @Column(value = "user_name", oldName = "name", length = 64)
    private String username;
}
```

```kotlin
@Table(value = "t_user", oldName = "user")
@EntityProxy
class UserEntity {

    @Column(primaryKey = true)
    var id: Long? = null

    @Column(value = "user_name", oldName = "name", length = 64)
    var username: String? = null
}
```

## Sync / Migration Safety

Code First 同步必须强调安全边界：

- 默认 sync 只做相对安全动作
- 危险变更通常需要显式命令或人工确认
- 不要默认它是“无限制自动迁移器”

### Sync Template Placeholder

```java
public class EasyQueryCodeFirstBootstrap {

    public void init() {
        // 占位模板：真正的 sync / migration 入口请优先通过 MCP、MigrationTest、
        // 以及 code-first/readme.md 核对当前版本实现，再决定是否启用。
    }
}
```

```kotlin
class EasyQueryCodeFirstBootstrap {
    fun init() {
        // 占位模板：真正的 sync / migration 入口需先回 MCP / 源码 / 测试确认
    }
}
```

## Modeling Checklist

- 表名、列名、长度、精度、nullable 是否清晰定义
- 主键是否明确，是否需要生成策略
- 列转换、SQL 转换、类型处理器是否各司其职
- 逻辑删除字段与版本字段是否真实需要
- 审计字段是否统一，例如 `createTime`、`updateTime`
- 涉及 `oldName` 时，是否同时评估了 rename 风险与回滚策略
- 变更实体时，是否评估了旧字段迁移、默认值与兼容性

## Risks

- 不要在 MCP 缺失时臆造初始化 API、迁移 API 或注解参数
- 不要只因为文档里出现过某个注解字段，就默认当前版本仍然可用
- 不要把 `oldName`、`shardingInitializer` 这类元数据，误解成“危险迁移一定自动完成”
- Code First 能力通常和宿主配置、方言、迁移策略一起评估，不能孤立看实体类
