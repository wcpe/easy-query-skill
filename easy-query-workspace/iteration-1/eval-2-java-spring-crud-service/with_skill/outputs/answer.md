# UserService (Spring Boot + easy-query)

下面是基于 easy-query 强类型 proxy DSL（`EasyEntityQuery`）的完整实现，包含实体、Service 三个方法和 `application.yml` 配置。

## 1. 实体 SysUser

```java
package com.example.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.example.entity.proxy.SysUserProxy;   // 编译期由处理器生成，勿手写
import lombok.Data;

@Data
@Table("t_sys_user")
@EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {

    @Column(primaryKey = true)
    private String id;

    private String username;

    private String phone;
}
```

要点：
- `@Table` + `@EntityProxy` + `implements ProxyEntityAvailable<SysUser, SysUserProxy>` 三件套缺一不可，否则没有强类型 DSL。
- `SysUserProxy` 是编译期生成在实体包的 `.proxy` 子包下（`com.example.entity.proxy.SysUserProxy`），不要手写或编辑。
- `username`、`phone` 默认按 name-conversion=underlined 映射为 `username`、`phone`（本例字段本身就是单词，无需 `@Column` 改名）。

## 2. UserService

```java
package com.example.service;

import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.example.entity.SysUser;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserService {

    private final EasyEntityQuery easyEntityQuery;

    // 构造器注入（starter 已自动装配 EasyEntityQuery bean）
    public UserService(EasyEntityQuery easyEntityQuery) {
        this.easyEntityQuery = easyEntityQuery;
    }

    /**
     * 按手机号查唯一用户。
     * 业务键唯一 -> 用 singleOrNull()（不是 firstOrNull），出现重复时会暴露而不是悄悄返回第一条。
     */
    public SysUser getByPhone(String phone) {
        return easyEntityQuery.queryable(SysUser.class)
                .where(o -> o.phone().eq(phone))
                .singleOrNull();
    }

    /**
     * 新增用户。executeRows() 返回受影响行数。
     * 主键为 String（非 DB 自增），由调用方/业务生成后塞进 user。
     */
    @Transactional
    public long addUser(SysUser user) {
        return easyEntityQuery.insertable(user).executeRows();
    }

    /**
     * 按 id 更新用户名。
     * setColumns 选要更新的列，where 限定主键。
     * executeRows(1, "...") 断言恰好更新一行：0 行说明 id 不存在，会抛异常而不是当成功。
     */
    @Transactional
    public void updateUsernameById(String id, String username) {
        easyEntityQuery.updatable(SysUser.class)
                .setColumns(o -> o.username().set(username))
                .where(o -> o.id().eq(id))
                .executeRows(1, "更新用户名失败：用户不存在");
    }
}
```

行为说明：
- **按手机号查唯一**：手机号是唯一业务键，所以用 `singleOrNull()` 而非 `firstOrNull()`。如果手机号不保证唯一，再换 `firstOrNull()`。
- **新增**：`insertable(user).executeRows()`。本例主键是 `String`，由业务生成；若你改成数据库自增主键，实体上加 `@Column(primaryKey = true, generatedKey = true)`，并用 `executeRows(true)` 回填 id。
- **按 id 更新用户名**：`updatable(...).setColumns(...).where(...)`，并用 `executeRows(1, msg)` 断言只更新一行——这样 id 不存在时（返回 0 行）会抛错，避免把“没更新到”当成功。
- 两个写方法加了 `@Transactional`（Spring 声明式事务）。不要在方法内再手动 `beginTransaction()`，否则会重复开事务。

## 3. application.yml

```yaml
spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://127.0.0.1:3306/mydb?serverTimezone=GMT%2B8&characterEncoding=utf-8&useSSL=false&allowMultiQueries=true&rewriteBatchedStatements=true
    username: root
    password: root

easy-query:
  enable: true                # 必填！starter 默认关闭，忘了它 EasyEntityQuery 注入会失败
  database: mysql             # 方言，要和 classpath 上的 sql-* 方言依赖一致
  name-conversion: underlined # 驼峰字段 -> 蛇形列名（默认）
  print-sql: true             # 打印生成的 SQL，便于调试
  delete-throw: true          # 无条件 delete 时抛错而不是静默执行
```

配置要点：
- `easy-query.enable: true` 是**必填**，默认 `false`；不加则不创建任何 bean，`EasyEntityQuery` 注入直接失败。
- `easy-query.database` 必须和你引入的方言依赖（如 `sql-mysql`）匹配。
- `name-conversion: underlined` 是默认的驼峰转蛇形映射，需要自定义列名用 `@Column("custom_name")`。

## 4. 依赖（Maven，Java）

别忘了编译期的 proxy 处理器（APT），否则实体能编译但 `SysUserProxy` 生成不出来：

```xml
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-springboot-starter</artifactId>
    <version>3.1.89</version>
</dependency>
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-mysql</artifactId>           <!-- 方言，对应 database: mysql -->
    <version>3.1.89</version>
</dependency>
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-processor</artifactId>       <!-- APT 处理器，生成 *Proxy -->
    <version>3.1.89</version>
    <scope>provided</scope>
</dependency>
```

> 如果是 Kotlin 项目，把 `sql-processor`(APT) 换成 KSP 的 `sql-ksp-processor`，并在 Gradle 配置 KSP 插件。

## 备注

- 代码来源：easy-query skill 的 `setup-spring-boot.md` / `entity-mapping.md` / `query.md` / `write.md` 验证模式（skill 基线版本 3.1.89-dev）。
- 版本提醒：以上依赖版本为 `3.1.89`，请按你项目实际版本对齐；若版本不同，以你项目为准。
- 生产建议：对外接口不要直接返回 ORM 实体，建议用 DTO；本例为聚焦 Service 三个方法未加 DTO 层。
- “proxy 找不到 / SysUserProxy 不存在”属于构建配置问题（处理器没配好），不是代码问题。
