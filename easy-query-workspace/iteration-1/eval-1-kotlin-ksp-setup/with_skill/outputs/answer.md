# Kotlin + Gradle 接入 easy-query（MySQL）

## 先回答你的问题：不用 kapt，用 KSP

easy-query 的 Kotlin 路径用 **KSP**（`com.google.devtools.ksp`）来生成代理类（`*Proxy`），**不是 kapt**。请不要加 kapt 插件。原因：每个实体在编译期会生成一个强类型代理类（Java 用 APT，Kotlin 用 KSP），代理 DSL（`where { it.id().eq(...) }`）就靠这个代理类工作。如果你按旧习惯用 kapt，代理类不会被正确生成，会出现 “找不到 XxxProxy”。

注意：KSP 版本号必须和 Kotlin 版本配对（格式 `<kotlin版本>-<ksp版本>`，例如 `1.9.21-1.0.15`）。

## 1. build.gradle.kts —— 插件 + 依赖

```kotlin
plugins {
    kotlin("jvm") version "1.9.21"
    id("com.google.devtools.ksp") version "1.9.21-1.0.15"   // KSP 版本和 Kotlin 版本成对，不要用 kapt
}

repositories { mavenCentral() }

dependencies {
    implementation(kotlin("stdlib"))
    implementation("com.easy-query:sql-core:3.1.89")
    implementation("com.easy-query:sql-mysql:3.1.89")        // MySQL 方言
    implementation("com.easy-query:sql-api-proxy:3.1.89")    // 强类型代理 API（EasyEntityQuery）
    ksp("com.easy-query:sql-ksp-processor:3.1.89")           // ★ KSP 处理器：生成代理类（这一行替代 kapt）
    implementation("com.mysql:mysql-connector-j:9.2.0")
    implementation("com.zaxxer:HikariCP:3.3.1")
    testImplementation(kotlin("test"))
}

kotlin {
    jvmToolchain(17)
    // 把 KSP 生成目录加入源集，IntelliJ 才能解析 *Proxy 类型；
    // 不加这行 gradle build 仍能过，但 IDE 会标红代理类。
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}
```

代理类生成在 `build/generated/ksp/main/kotlin`。如果某个 `*Proxy` 解析不了：确认 `ksp(...)` 这行在、跑一次 build、确认上面的 `srcDir` 那行也在。

> 版本说明：以上 easy-query 版本号 `3.1.89` 是本技能的基线参考版本，不是硬锁。请以你项目实际使用/想用的版本为准；不同版本时优先用你项目里的号。

## 2. 实体（Kotlin）

普通类或 `data class` 都行。用 `@Table` + `@EntityProxy` 标注，并实现 `ProxyEntityAvailable<实体, 实体Proxy>`。这里的 `TopicProxy` 由 KSP 生成到 `<包名>.proxy` 下。

```kotlin
package com.test.entity

import com.easy.query.core.annotation.Column
import com.easy.query.core.annotation.EntityProxy
import com.easy.query.core.annotation.Table
import com.easy.query.core.proxy.ProxyEntityAvailable
import com.test.entity.proxy.TopicProxy   // KSP 生成

@Table("t_topic")
@EntityProxy
class Topic : ProxyEntityAvailable<Topic, TopicProxy> {
    @Column(primaryKey = true)
    var id: String? = null
    var stars: Int? = null
    var title: String? = null
}
```

## 3. main 里初始化 EasyEntityQuery（纯 Kotlin，无 Spring）

```kotlin
package com.test

import com.easy.query.api.proxy.client.DefaultEasyEntityQuery
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper
import com.easy.query.core.logging.LogFactory
import com.easy.query.mysql.config.MySQLDatabaseConfiguration
import com.test.entity.Topic
import com.zaxxer.hikari.HikariDataSource

fun main() {
    val dataSource = HikariDataSource().apply {
        jdbcUrl = "jdbc:mysql://127.0.0.1:3306/easy-query-test?serverTimezone=GMT%2B8&characterEncoding=utf-8&useSSL=false&allowMultiQueries=true&rewriteBatchedStatements=true"
        username = "root"
        password = "root"
        driverClassName = "com.mysql.cj.jdbc.Driver"
        maximumPoolSize = 20
    }
    LogFactory.useStdOutLogging()

    val easyQueryClient = EasyQueryBootstrapper.defaultBuilderConfiguration()
        .setDefaultDataSource(dataSource)
        .useDatabaseConfigure(MySQLDatabaseConfiguration())   // 方言：要和你引的 sql-mysql 对应
        .build()
    val entityQuery = DefaultEasyEntityQuery(easyQueryClient)  // 这就是你的 EasyEntityQuery

    // 用一下：注意 Kotlin 用 Topic::class.java，以及尾随 lambda where { it... }
    val list = entityQuery.queryable(Topic::class.java)
        .where { it.id().eq("123") }
        .toList()
}
```

几个 Kotlin 专属细节：
- 传 `Topic::class.java`，不是 Java 的 `Topic.class`。
- 条件用尾随 lambda `where { it.id().eq("123") }`。
- 方言三处要一致：依赖 `sql-mysql`、`useDatabaseConfigure(MySQLDatabaseConfiguration())`。

## 4. 可选：infix 语法糖

easy-query 提供 Kotlin infix 扩展，可写成 `it.id eq "123"` 代替 `it.id().eq("123")`，两者编译成同一条查询。不确定项目是否配好 infix 时，优先用显式的 `it.id().eq("123")`，它一定能用。

## 易错点清单
- 给 Kotlin 用 **kapt** —— 错，Kotlin 路径是 **KSP**，别加 kapt 插件。
- 漏了 `kotlin.srcDir("build/generated/ksp/main/kotlin")` → IDE 里代理类标红。
- KSP 版本和 Kotlin 版本不配对（后缀 `-a.b.c` 是跟 Kotlin 版本绑定的）。
- 传了 `Topic.class` 而不是 `Topic::class.java`。

---
来源：本回答基于 easy-query 技能的 `references/setup-kotlin.md`（官方文档 Gradle KSP 构建 / 实体 / 初始化 / infix；共享运行时 API 经源码验证）。技能基线版本 3.1.89-dev，版本号请按你项目实际为准。
