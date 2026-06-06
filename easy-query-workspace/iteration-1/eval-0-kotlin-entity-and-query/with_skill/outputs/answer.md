# Easy Query (Kotlin / KSP) — Topic 实体 + 查询

下面是可直接编译的 Kotlin 代码：`Topic` 实体（表 `t_topic`）+ 查询「`stars > 100`、按 `createTime` 倒序、取前 N 条、返回 `List<Topic>`」。

Kotlin 走 **KSP** 生成代理类（不是 KAPT）。`TopicProxy` 由 KSP 在编译期生成到 `<包名>.proxy` 下，写完代码先跑一次 build 即可解析。

## 1. 实体 Topic（表 t_topic）

```kotlin
package com.test.entity

import com.easy.query.core.annotation.Column
import com.easy.query.core.annotation.EntityProxy
import com.easy.query.core.annotation.Table
import com.easy.query.core.proxy.ProxyEntityAvailable
import com.test.entity.proxy.TopicProxy   // 由 KSP 生成到 <pkg>.proxy
import java.time.LocalDateTime

@Table("t_topic")
@EntityProxy
class Topic : ProxyEntityAvailable<Topic, TopicProxy> {
    @Column(primaryKey = true)
    var id: String? = null
    var stars: Int? = null
    var title: String? = null
    var createTime: LocalDateTime? = null
}
```

说明：
- 字段名 `createTime` 默认会映射到列。若数据库列名是 `create_time`，在全局配置里开启驼峰转下划线，或显式标注 `@Column("create_time")`。
- 主键用 `@Column(primaryKey = true)`。
- `createTime` 的类型按你的库选 `LocalDateTime`（也可用 `java.util.Date`），这里用 `LocalDateTime`。

## 2. 查询：stars > 100，createTime 倒序，前 N 条，返回 List

`queryable → where → orderBy → 终端`。Kotlin 用尾随 lambda `where { it... }`，并传 `Topic::class.java`。

「取前 N 条」用 `toPageResult(1, n)` 取第一页（在 SQL 层做 LIMIT，并保证稳定排序），再 `.getData()` 拿到 `List<Topic>`：

```kotlin
import com.easy.query.api.proxy.client.EasyEntityQuery

fun findTopTopics(entityQuery: EasyEntityQuery, topN: Int): List<Topic> {
    val page = entityQuery.queryable(Topic::class.java)
        .where { it.stars().gt(100) }
        .orderBy {
            it.createTime().desc()
            it.id().desc()          // 稳定排序的兜底键，避免 createTime 相同导致分页错乱
        }
        .toPageResult(1, topN)      // 第 1 页、每页 topN 条 → 即“前 N 条”
    return page.data               // List<Topic>
}
```

调用示例（前 10 条）：

```kotlin
val list: List<Topic> = findTopTopics(entityQuery, 10)
```

## 3. 初始化 EasyEntityQuery（纯 Kotlin，无 Spring；如已有实例可跳过）

```kotlin
import com.easy.query.api.proxy.client.DefaultEasyEntityQuery
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper
import com.easy.query.core.logging.LogFactory
import com.easy.query.mysql.config.MySQLDatabaseConfiguration
import com.zaxxer.hikari.HikariDataSource

fun main() {
    val dataSource = HikariDataSource().apply {
        jdbcUrl = "jdbc:mysql://127.0.0.1:3306/easy-query-test?serverTimezone=GMT%2B8&characterEncoding=utf-8&useSSL=false"
        username = "root"
        password = "root"
        driverClassName = "com.mysql.cj.jdbc.Driver"
        maximumPoolSize = 20
    }
    LogFactory.useStdOutLogging()

    val easyQueryClient = EasyQueryBootstrapper.defaultBuilderConfiguration()
        .setDefaultDataSource(dataSource)
        .useDatabaseConfigure(MySQLDatabaseConfiguration())  // 方言要和 sql-* 依赖一致
        .build()
    val entityQuery = DefaultEasyEntityQuery(easyQueryClient)

    val top10 = findTopTopics(entityQuery, 10)
    println(top10)
}
```

## 4. Gradle 关键依赖（KSP）

```kotlin
plugins {
    kotlin("jvm") version "1.9.21"
    id("com.google.devtools.ksp") version "1.9.21-1.0.15"  // KSP 版本号与 Kotlin 版本配对
}

dependencies {
    implementation("com.easy-query:sql-core:3.1.89")
    implementation("com.easy-query:sql-mysql:3.1.89")      // 方言，按库选 sql-h2 / sql-pgsql ...
    implementation("com.easy-query:sql-api-proxy:3.1.89")  // 强类型代理 API
    ksp("com.easy-query:sql-ksp-processor:3.1.89")         // ★ KSP 处理器，生成 *Proxy
}

kotlin {
    jvmToolchain(17)
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")   // 让 IDE 能解析 *Proxy
    }
}
```

## 备注

- 来源：实体与初始化来自 skill 的 `references/setup-kotlin.md`；查询链 / 排序 / `toPageResult` 来自 `references/query.md`（均为源码/官方文档验证的模式）。
- 关于「前 N 条」：skill 的终端方法表里没有独立的 `limit/take` 方法，验证过的「在 SQL 层取前 N 条」写法就是 `toPageResult(1, n).getData()`，且它强制配套 `orderBy` 保证稳定，正好满足需求。
- `.gt(100)` 中 `stars` 为 `Int?`，自动装箱比较无需额外处理；动态可选条件应改用门控重载 `.gt(condition, value)`，本题是固定条件故直接 `.gt(100)`。
- 版本基线 3.1.89-dev，请对齐你项目里的实际版本；若你的列名是下划线风格记得配驼峰映射或 `@Column`。
- `EasyEntityQuery` 接口位于 `com.easy.query.api.proxy.client`，其默认实现为 `DefaultEasyEntityQuery`。
