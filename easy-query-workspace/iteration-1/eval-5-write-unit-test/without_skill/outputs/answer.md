# Easy-Query 查询代码单元测试（不依赖外部数据库）

目标：测试 `Topic` 实体上 `stars > 100` 的过滤条件能查到正确数据，使用 JUnit，且不连接真实/外部数据库。

## 思路

Easy-Query 是一个标准的 ORM/查询框架，本质上还是通过 JDBC 连接数据库执行 SQL。要"不依赖外部数据库"，最稳妥、最贴近真实执行路径的做法是用 **内存数据库 H2**。它是嵌入式的、随测试进程启停，不需要任何外部服务，但又真实地执行 SQL，能验证 `where(t -> t.gt(Topic::getStars, 100))` 这类条件是否被正确翻译成 SQL 并返回正确结果。

> 备选方案：用 Mockito 把 `EasyEntityQuery` 全部 mock 掉。但那样只是验证"我调用了某个方法"，并不会真正执行过滤逻辑，**测不出 stars>100 的正确性**，所以这里不推荐。内存库才是这个测试目标的正确选择。

## 依赖（Maven）

```xml
<!-- JUnit 5 -->
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.10.2</version>
    <scope>test</scope>
</dependency>

<!-- 内存数据库 H2 -->
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <version>2.2.224</version>
    <scope>test</scope>
</dependency>

<!-- easy-query 核心 + api 代理实现（版本以你工程实际为准） -->
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-api-proxy</artifactId>
    <version>2.5.0</version>
</dependency>
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-h2</artifactId>
    <version>2.5.0</version>
</dependency>
```

> easy-query 的代理（proxy）API 会为实体生成 `TopicProxy` 等辅助类（通过 APT 注解处理器），需要 `@EntityProxy` 注解 + 注解处理器开启。下面实体里同时给出了基于 lambda 的写法（`Topic::getStars`），它不依赖代理生成类，更适合直接写测试。

## 实体定义

```java
package com.example.entity;

import com.easy.query.core.annotation.Column;
import com.easy.query.core.annotation.Table;

import java.time.LocalDateTime;

@Table("t_topic")
public class Topic {

    @Column(primaryKey = true)
    private String id;

    private Integer stars;

    private String title;

    @Column("createTime")
    private LocalDateTime createTime;

    // getter / setter
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public Integer getStars() { return stars; }
    public void setStars(Integer stars) { this.stars = stars; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public LocalDateTime getCreateTime() { return createTime; }
    public void setCreateTime(LocalDateTime createTime) { this.createTime = createTime; }
}
```

## 单元测试

```java
package com.example;

import com.easy.query.api.proxy.client.DefaultEasyEntityQuery;
import com.easy.query.api.proxy.client.EasyEntityQuery;
import com.easy.query.core.api.client.EasyQueryClient;
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper;
import com.easy.query.core.basic.api.database.CodeFirstCommand;
import com.easy.query.core.basic.api.database.DatabaseCodeFirst;
import com.easy.query.core.datasource.DefaultDataSourceUnitFactory;
import com.example.entity.Topic;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import javax.sql.DataSource;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public class TopicQueryTest {

    private EasyEntityQuery entityQuery;

    @BeforeAll
    void setUp() {
        // 1. 准备 H2 内存数据库（嵌入式，进程内，无需外部服务）
        JdbcDataSource ds = new JdbcDataSource();
        // DB_CLOSE_DELAY=-1 让数据在整个 JVM 生命周期内保留；MODE 兼容 MySQL 语法可按需加
        ds.setURL("jdbc:h2:mem:topic_test;DB_CLOSE_DELAY=-1");
        ds.setUser("sa");
        ds.setPassword("");

        // 2. 构建 easy-query 客户端，方言指定为 H2
        EasyQueryClient client = EasyQueryBootstrapper.defaultBuilderConfiguration()
                .setDefaultDataSource(ds)
                .optionConfigure(op -> {
                    // 可在此调整命名策略、打印 SQL 等
                    op.setPrintSql(true);
                })
                .useDatabaseConfigure(new com.easy.query.h2.config.H2DatabaseConfiguration())
                .build();

        entityQuery = new DefaultEasyEntityQuery(client);

        // 3. Code First 自动建表（避免手写 DDL）
        DatabaseCodeFirst databaseCodeFirst = entityQuery.getDatabaseCodeFirst();
        CodeFirstCommand command =
                databaseCodeFirst.syncTableCommand(Arrays.asList(Topic.class));
        command.executeWithTransaction(arg -> arg.commit());

        // 4. 插入测试数据：跨越 stars=100 边界
        entityQuery.insertable(Arrays.asList(
                newTopic("low",      50,  "stars=50"),
                newTopic("boundary", 100, "stars=100 边界，不应被 >100 选中"),
                newTopic("high1",    150, "stars=150"),
                newTopic("high2",    200, "stars=200")
        )).executeRows();
    }

    private Topic newTopic(String idPrefix, int stars, String title) {
        Topic t = new Topic();
        t.setId(idPrefix + "-" + UUID.randomUUID());
        t.setStars(stars);
        t.setTitle(title);
        t.setCreateTime(LocalDateTime.now());
        return t;
    }

    @Test
    void should_return_only_topics_with_stars_greater_than_100() {
        // 被测查询：stars > 100
        List<Topic> result = entityQuery.queryable(Topic.class)
                .where(t -> t.gt(Topic::getStars, 100))
                .toList();

        // 断言：只命中 150 和 200 两条；边界 100 与 50 都不在内
        assertEquals(2, result.size(), "stars>100 应当只有 2 条记录");
        assertTrue(result.stream().allMatch(t -> t.getStars() > 100),
                "返回结果中每条的 stars 都必须 > 100");
        assertTrue(result.stream().noneMatch(t -> t.getStars() == 100),
                "边界值 stars=100 不应被 > 100 选中");

        List<Integer> stars = result.stream().map(Topic::getStars).sorted().toList();
        assertEquals(List.of(150, 200), stars);
    }

    @Test
    void should_return_empty_when_no_match() {
        List<Topic> result = entityQuery.queryable(Topic.class)
                .where(t -> t.gt(Topic::getStars, 1000))
                .toList();
        assertTrue(result.isEmpty(), "stars>1000 没有数据，应返回空列表");
    }
}
```

## 说明与要点

- **不依赖外部数据库**：H2 用 `jdbc:h2:mem:...` 跑在测试进程内存里，测试结束随 JVM 退出，无需安装/启动任何 DB 服务，CI 上也能直接跑。
- **真实执行 SQL**：`where(t -> t.gt(Topic::getStars, 100))` 会被 easy-query 翻译成 `WHERE stars > ?` 并真正在 H2 上执行，因此能真正验证过滤逻辑的正确性，而不是只验证调用。
- **边界用例**：特意放了一条 `stars=100`，验证 `gt`（>）严格大于、不含等于，避免把 `>` 误写成 `>=` 也"测试通过"。
- **建表方式**：用 easy-query 的 Code First (`syncTableCommand`) 按实体自动建表；如果你的 easy-query 版本没有该 API，可用 H2 的 `INIT` 脚本或一条手写 DDL 替代：

  ```sql
  CREATE TABLE t_topic (
      id VARCHAR(64) PRIMARY KEY,
      stars INT,
      title VARCHAR(255),
      createTime TIMESTAMP
  );
  ```
  通过 `ds.setURL("jdbc:h2:mem:topic_test;DB_CLOSE_DELAY=-1;INIT=RUNSCRIPT FROM 'classpath:schema.sql'")` 引入。

- **版本适配**：不同 easy-query 版本的 Bootstrapper / 方言配置类名可能略有差异（如 `H2DatabaseConfiguration` 的包路径、`getDatabaseCodeFirst` 是否存在）。请以你工程引用的版本为准，核心思路（H2 内存库 + 真实执行 + 边界断言）不变。
- **lambda vs proxy 写法**：上面用的是 `Topic::getStars` 的 lambda 写法，无需 APT 生成代理类。若你的代码用的是 proxy 写法（`.where((t, e) -> e.expression().lt(...))` 或 `t.stars().gt(100)`），把建表和插入保留不变，仅把查询那一行替换成你的 proxy 表达式即可，断言部分通用。
