# 给 Topic 查询写单元测试（H2 内存库，不依赖外部数据库）

思路：用 **H2 内存数据库 + code-first 建表**，在内存里跑真实 SQL，再断言返回的数据。这是 easy-query 业务项目里最常用的测试方式——测的是“代码真实跑出来的行为”，且不需要任何外部服务。

## 1. 测试依赖（test scope）

```xml
<!-- H2 方言支持 -->
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-h2</artifactId>
    <scope>test</scope>
</dependency>
<!-- H2 数据库 -->
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>test</scope>
</dependency>
<!-- 连接池 -->
<dependency>
    <groupId>com.zaxxer</groupId>
    <artifactId>HikariCP</artifactId>
    <scope>test</scope>
</dependency>
<!-- JUnit 5 -->
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
```

> 版本以你项目里现有的为准（技能基线 easy-query 3.1.89-dev）。`sql-h2` 的版本要和你主项目的 easy-query 版本对齐。

## 2. 实体 Topic

实体必须 `@Table` + `@EntityProxy` 并实现 `ProxyEntityAvailable`，代理类 `TopicProxy` 在编译期由 APT 自动生成（位于实体的 `.proxy` 子包，不要手写）。

```java
package com.test.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.EntityProxy;
import com.easy.query.core.annotation.Table;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.TopicProxy;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Table("t_topic")
@EntityProxy
public class Topic implements ProxyEntityAvailable<Topic, TopicProxy> {

    @Column(primaryKey = true)
    private String id;

    private Integer stars;

    private String title;

    // 默认 snake_case 列名映射：createTime -> create_time
    private LocalDateTime createTime;
}
```

## 3. 单元测试（JUnit 5）

```java
package com.test;

import com.easy.query.api.proxy.client.DefaultEasyEntityQuery;
import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.api.client.EasyQueryClient;
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper;
import com.easy.query.h2.config.H2DatabaseConfiguration;
import com.test.entity.Topic;
import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TopicQueryTest {

    static EasyEntityQuery easyEntityQuery;

    @BeforeAll
    static void setup() {
        HikariDataSource ds = new HikariDataSource();
        // DB_CLOSE_DELAY=-1：整个测试期间保持内存库存活，否则首个连接关闭后表就没了
        // MODE=MySQL：让 H2 生成更接近 MySQL 的 SQL
        ds.setJdbcUrl("jdbc:h2:mem:test;DB_CLOSE_DELAY=-1;MODE=MySQL");
        ds.setDriverClassName("org.h2.Driver");
        ds.setUsername("sa");
        ds.setPassword("");

        EasyQueryClient client = EasyQueryBootstrapper.defaultBuilderConfiguration()
                .setDefaultDataSource(ds)
                .useDatabaseConfigure(new H2DatabaseConfiguration())   // H2 方言
                .build();
        easyEntityQuery = new DefaultEasyEntityQuery(client);

        // code-first：根据实体类自动建表
        easyEntityQuery.getDatabaseCodeFirst()
                .syncTableCommand(Arrays.asList(Topic.class))
                .executeWithTransaction(arg -> arg.commit());

        // 造数据：3 条 stars>100，1 条 stars=100（边界，gt 不应包含），1 条 stars<100
        easyEntityQuery.insertable(Arrays.asList(
                newTopic("1", 150, "hello"),
                newTopic("2", 200, "world"),
                newTopic("3", 101, "edge-in"),
                newTopic("4", 100, "edge-out"),  // 恰好 100，gt(100) 不命中
                newTopic("5", 50, "low")
        )).executeRows();
    }

    private static Topic newTopic(String id, int stars, String title) {
        Topic t = new Topic();
        t.setId(id);
        t.setStars(stars);
        t.setTitle(title);
        t.setCreateTime(LocalDateTime.now());
        return t;
    }

    @Test
    void filters_by_stars_gt_100() {
        List<Topic> list = easyEntityQuery.queryable(Topic.class)
                .where(o -> o.stars().gt(100))   // stars > 100
                .orderBy(o -> o.id().asc())      // 稳定排序，断言可重复
                .toList();

        // 只命中 stars=150 / 200 / 101 这三条，边界 100 与 50 被排除
        assertEquals(3, list.size());
        assertEquals(Arrays.asList("1", "2", "3"),
                list.stream().map(Topic::getId).toList());
        // 全部满足 stars>100
        assertTrue(list.stream().allMatch(t -> t.getStars() > 100));
    }
}
```

> 如果你用的是 JUnit 4，把 `org.junit.jupiter.api.*` 换成 `org.junit.*`，`@BeforeAll` 换成 `@BeforeClass`（方法仍为 `static`），断言用 `org.junit.Assert.*`。DSL 部分完全不变。

## 关键点 / 易错点

- **`gt` 是严格大于**：`stars > 100`，所以 `stars=100` 的那条不会命中。如果你的“>100”其实想含等于，用 `.ge(100)`。测试里特意放了 `stars=100` 和 `stars=101` 两条边界数据来卡住这一点。
- **H2 url 必须带 `DB_CLOSE_DELAY=-1`**，否则连接一关表就被丢弃。
- **别忘了 `syncTableCommand(...)` 建表**，否则查询时报表不存在。
- **方言要配 `H2DatabaseConfiguration`**，不要在 H2 上用 `MySQLDatabaseConfiguration`（加 `MODE=MySQL` 只是让 SQL 风格更像 MySQL）。
- **`TopicProxy` 是编译期生成的**（Java 走 APT）。如果报 “找不到 TopicProxy / 代理未生成”，那是构建配置问题，不是代码问题——检查 annotation processor 是否启用。
- 测试里加了 `orderBy(o -> o.id().asc())`，让结果顺序稳定，断言才可重复。

## （可选）只想验证 SQL 形状、连内存库都不想跑

如果只关心“过滤条件有没有正确翻成 SQL”，可以用 `.toSQL()` 零执行断言（仍需一个已构建的 `easyEntityQuery` 实例，但不需要造数据、不真正执行）：

```java
String sql = easyEntityQuery.queryable(Topic.class)
        .where(o -> o.stars().gt(100))
        .orderBy(o -> o.id().asc())
        .toSQL();
// 断言 sql 含有期望的 WHERE `stars` > ? / ORDER BY `id` 等片段
assertTrue(sql.contains("stars"));
```

---

参考来源：本方案出自技能 `references/testing.md` 的 §1（H2 内存行为测试，主方案）与 §2（`.toSQL()` 形状断言，可选），实体注解出自 `references/entity-mapping.md`。`getDatabaseCodeFirst().syncTableCommand(...).executeWithTransaction(arg -> arg.commit())` 与 `H2DatabaseConfiguration`（`com.easy.query.h2.config`，来自 `sql-h2`）均为源码验证。技能基线版本 easy-query 3.1.89-dev——若你项目版本不同，以你的项目为准。
