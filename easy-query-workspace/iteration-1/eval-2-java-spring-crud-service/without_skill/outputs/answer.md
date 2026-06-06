# Easy-Query 实现 UserService

下面是基于 [easy-query](https://github.com/dromara/easy-query) 在 Spring Boot 中实现的完整代码。

## 1. 实体类 SysUser

```java
package com.example.demo.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.example.demo.entity.proxy.SysUserProxy;

/**
 * 系统用户实体，对应表 t_sys_user
 */
@Table("t_sys_user")
@EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {

    /** 主键 id */
    @Column(primaryKey = true)
    private String id;

    /** 用户名 */
    private String username;

    /** 手机号 */
    private String phone;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }
}
```

说明：

- `@Table("t_sys_user")` 指定表名。
- `@Column(primaryKey = true)` 标记主键。
- `@EntityProxy` + 实现 `ProxyEntityAvailable` 是 easy-query 的 APT（注解处理器）方式，编译后会自动生成 `SysUserProxy` 代理类，支持强类型 lambda 写法（`u -> u.phone()`）。
  - 如果你不想用 APT 代理，可以去掉 `@EntityProxy`、`ProxyEntityAvailable` 和那个 import，改用字符串属性名写法（见文末备注）。

> id 这里用 String（比如 UUID/雪花算法字符串）。如果你的 id 是自增 long，把类型改成 `Long`，并加上 `@Column(primaryKey = true, generatedKey = true)`。

## 2. UserService

```java
package com.example.demo.service;

import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.example.demo.entity.SysUser;
import com.example.demo.entity.proxy.SysUserProxy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
public class UserService {

    private final EasyEntityQuery easyEntityQuery;

    // 推荐构造器注入
    public UserService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    /**
     * 按手机号查询唯一用户。
     * 查不到返回 null；查到多条会抛异常（保证唯一）。
     */
    public SysUser getByPhone(String phone) {
        return easyEntityQuery.queryable(SysUser.class)
                .where(u -> u.phone().eq(phone))
                .firstOrNull();
        // 如果业务上要求“必须唯一，多条即异常”，用 singleOrNull() 代替 firstOrNull()
    }

    /**
     * 新增用户，返回新用户 id。
     */
    @Transactional(rollbackFor = Exception.class)
    public String addUser(String username, String phone) {
        SysUser user = new SysUser();
        user.setId(UUID.randomUUID().toString().replace("-", ""));
        user.setUsername(username);
        user.setPhone(phone);

        easyEntityQuery.insertable(user).executeRows();
        return user.getId();
    }

    /**
     * 按 id 更新用户名，返回受影响行数。
     */
    @Transactional(rollbackFor = Exception.class)
    public long updateUsername(String id, String newUsername) {
        return easyEntityQuery.updatable(SysUser.class)
                .setColumns(u -> u.username().set(newUsername))
                .where(u -> u.id().eq(id))
                .executeRows();
    }
}
```

要点：

- `EasyEntityQuery` 是 easy-query 在 Spring Boot starter 下自动注入的核心 API（proxy 强类型版本）。直接构造器注入即可。
- **查唯一**：
  - `firstOrNull()`：取第一条，没有返回 null（生成的 SQL 带 `limit 1`）。
  - `singleOrNull()`：明确要求最多一条，查到多条会抛异常，更符合“唯一用户”语义。按需选一个。
- **新增**：`insertable(实体).executeRows()`，返回插入行数；id 自己生成。
- **更新部分字段**：`updatable(类).setColumns(...).where(...).executeRows()`，只更新 username，生成 `UPDATE t_sys_user SET username = ? WHERE id = ?`。
- `executeRows()` 返回受影响行数（long）。

## 3. 依赖（pom.xml）

```xml
<!-- easy-query Spring Boot starter -->
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-springboot-starter</artifactId>
    <version>2.4.5</version>  <!-- 用一个较新的稳定版本即可 -->
</dependency>

<!-- APT 注解处理器：用于生成 SysUserProxy 强类型代理类 -->
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-processor</artifactId>
    <version>2.4.5</version>
    <scope>provided</scope>
</dependency>

<!-- 数据库驱动，按你的库选，示例 MySQL -->
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
</dependency>
```

> easy-query 的 groupId/artifactId 和版本号请以你引入时仓库中的实际最新版为准。APT 处理器必须引入，否则 `SysUserProxy` 不会被生成、编译报错。如果用 IDEA，记得在 Settings 里开启 Annotation Processing。

## 4. application.yml 配置

easy-query 的 Spring Boot starter 复用 Spring 的数据源，再加一段 `easy-query` 自己的配置：

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/your_db?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
    username: root
    password: your_password
    driver-class-name: com.mysql.cj.jdbc.Driver
    # 建议配连接池（Spring Boot 默认 HikariCP）
    hikari:
      maximum-pool-size: 10
      minimum-idle: 2

# easy-query 配置
easy-query:
  enable: true                 # 开启 easy-query
  database: mysql              # 数据库方言：mysql / pgsql / oracle / mssql / h2 / sqlite 等
  name-conversion: underlined  # 实体属性(驼峰) <-> 表字段(下划线) 自动转换
  # 上面这条很关键：开启后 username 自动映射到 username，
  # 像 createTime 这种会自动映射到 create_time。
  # 因为你的字段就是 username/phone（无驼峰），underlined 不影响也最通用。
  print-sql: true              # 开发期打印执行的 SQL，方便调试，生产可关
```

各项说明：

| 配置项 | 作用 |
|--------|------|
| `easy-query.enable` | 启用 starter，必须为 true |
| `easy-query.database` | 指定数据库方言，决定生成的 SQL 语法和分页方式 |
| `easy-query.name-conversion` | 命名转换策略，`underlined` 表示驼峰转下划线（最常用）；如果库字段就是驼峰可用 `default` |
| `easy-query.print-sql` | 是否在日志打印实际 SQL，开发期建议开 |

如果用其它库，把 `spring.datasource` 和 `easy-query.database` 同时改掉，例如 PostgreSQL：`database: pgsql`、driver 改 `org.postgresql.Driver`。

## 5. 备注：不使用 APT 代理的写法（可选）

如果你不想引入 `sql-processor` / 不想用强类型代理，可以注入 `EasyQueryClient`（或老版本的 `EasyQuery`），用字符串属性名：

```java
// 查唯一
SysUser u = easyQueryClient.queryable(SysUser.class)
        .where(o -> o.eq("phone", phone))
        .firstOrNull();

// 更新用户名
easyQueryClient.updatable(SysUser.class)
        .setColumns(o -> o.column("username"))   // 配合实体上的值，或用 set 方式
        .where(o -> o.eq("id", id))
        .executeRows();
```

推荐还是用 `EasyEntityQuery` + APT 代理（第 2 节那种），编译期检查、重构友好、不会写错字段名。

## 小结

- 实体用 `@Table` + `@Column(primaryKey=true)` + `@EntityProxy`。
- 注入 `EasyEntityQuery`，三个方法分别用 `queryable().where().firstOrNull()`、`insertable().executeRows()`、`updatable().setColumns().where().executeRows()`。
- yml 关键四项：`enable`、`database`、`name-conversion: underlined`、`print-sql`，数据源仍走标准 `spring.datasource`。
- 别忘了引入 `sql-processor` 这个 APT 依赖并开启 IDE 注解处理，否则代理类生成不出来。
