# Kotlin + Gradle 接入 easy-query（连 MySQL）

## 先回答你最关心的问题：用 kapt 还是 ksp？

**用 KSP，不要用 kapt。**

easy-query 的 Kotlin API（`sql-ksp-processor`）官方就是基于 **KSP**（Kotlin Symbol Processing）做注解处理 / 代理对象（apt proxy）生成的。理由：

- easy-query 官方对 Kotlin 提供的是 KSP processor，没有提供 kapt 版本的处理器。
- KSP 是 Kotlin 原生的注解处理方案，比 kapt 快很多（kapt 要先把 Kotlin 编译成 Java stub 再走 javac 的 apt，慢且正在被废弃）。
- 你之前别的库（比如 Room、早期 MapStruct 配置）可能用 kapt，但接 easy-query 时请切到 KSP。如果项目里同时还有别的库仍需 kapt，两者可以共存（kapt 和 ksp 插件都加上即可），互不影响。

> 注意：KSP 插件的版本号要和你的 Kotlin 版本对应（KSP 版本格式是 `<kotlin版本>-<ksp版本>`，例如 Kotlin `1.9.25` 对应 `1.9.25-1.0.20`）。版本不匹配会编译报错。

---

## build.gradle.kts

```kotlin
plugins {
    kotlin("jvm") version "1.9.25"
    // KSP 插件：版本前半段必须与上面的 Kotlin 版本一致
    id("com.google.devtools.ksp") version "1.9.25-1.0.20"
    application
}

group = "com.example"
version = "1.0.0"

repositories {
    mavenCentral()
}

// 把 KSP 生成的 Kotlin 代码加入源码集，IDE 才能正确识别生成的代理类
kotlin {
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}

dependencies {
    // easy-query Kotlin API（核心，包含 EasyEntityQuery）
    implementation("com.easy-query:sql-api-proxy:版本号")
    implementation("com.easy-query:sql-api4kt:版本号")

    // 数据库方言：MySQL
    implementation("com.easy-query:sql-mysql:版本号")

    // KSP 注解处理器，负责为 @EntityProxy 实体生成代理对象
    ksp("com.easy-query:sql-ksp-processor:版本号")

    // MySQL JDBC 驱动
    implementation("com.mysql:mysql-connector-j:8.3.0")

    // 连接池（推荐 HikariCP）
    implementation("com.zaxxer:HikariCP:5.1.0")

    // 日志（easy-query 通过 slf4j 打印 SQL）
    implementation("org.slf4j:slf4j-simple:2.0.13")
}

application {
    mainClass.set("com.example.MainKt")
}
```

> 关于 `版本号`：请到 Maven Central 搜 `com.easy-query` 取最新稳定版，几个 `com.easy-query:*` 工件用同一个版本号即可保持一致。我没有写死具体数字，避免给你一个过期或不存在的版本。MySQL 8.x 数据库用 `mysql-connector-j` 8.x 驱动。

---

## 实体示例（用 KSP 必须有这一步才能看到生成效果）

```kotlin
package com.example.entity

import com.easy.query.core.annotation.Column
import com.easy.query.core.annotation.EntityProxy
import com.easy.query.core.annotation.Table
import com.easy.query.core.proxy.ProxyEntityAvailable

@Table("t_user")
@EntityProxy
class User : ProxyEntityAvailable<User, UserProxy> {
    @Column(primaryKey = true)
    var id: String = ""
    var name: String = ""
    var age: Int = 0
}
```

- `@EntityProxy` 是触发 KSP 生成代理类（`UserProxy`）的注解。
- `ProxyEntityAvailable<User, UserProxy>` 里的 `UserProxy` 由 KSP 在 `build/generated/ksp/main/kotlin` 下生成。**第一次写完实体后需要先 build 一次（`./gradlew build` 或 `./gradlew kspKotlin`），生成代理类后红线才会消失。**

---

## main 里初始化 EasyEntityQuery

```kotlin
package com.example

import com.easy.query.api.proxy.client.DefaultEasyEntityQuery
import com.easy.query.api.proxy.client.EasyEntityQuery
import com.easy.query.core.bootstrapper.EasyQueryBootstrapper
import com.easy.query.core.api.client.EasyQueryClient
import com.zaxxer.hikari.HikariConfig
import com.zaxxer.hikari.HikariDataSource
import javax.sql.DataSource

fun buildDataSource(): DataSource {
    val config = HikariConfig().apply {
        jdbcUrl = "jdbc:mysql://127.0.0.1:3306/your_db?" +
                "useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai&useSSL=false"
        username = "root"
        password = "your_password"
        driverClassName = "com.mysql.cj.jdbc.Driver"
        maximumPoolSize = 10
    }
    return HikariDataSource(config)
}

fun main() {
    val dataSource = buildDataSource()

    // 1. 先用 Bootstrapper 构建底层 EasyQueryClient，指定数据源 + MySQL 方言
    val client: EasyQueryClient = EasyQueryBootstrapper.defaultBuilderConfiguration()
        .setDataSource(dataSource)
        .optionConfigure { op ->
            op.setPrintSql(true)              // 控制台打印执行的 SQL，方便调试
            op.setKeepNativeStyle(true)
        }
        .useDatabaseConfigure(com.easy.query.mysql.config.MySQLDatabaseConfiguration())
        .build()

    // 2. 包装成 Kotlin 的 EasyEntityQuery 入口
    val easyEntityQuery: EasyEntityQuery = DefaultEasyEntityQuery(client)

    // 3. 使用示例：链式查询
    val users = easyEntityQuery
        .queryable(com.example.entity.User::class.java)
        .where { it.age().gt(18) }
        .toList()

    println("查询到 ${users.size} 条记录")
}
```

### 说明
- `EasyEntityQuery` 是 easy-query 在 Kotlin/Proxy 模式下的主入口对象，整个应用通常初始化**一次并复用**（它内部持有连接池、配置等，是线程安全的，做成全局单例/Spring Bean 即可）。
- 初始化两步走：先 `EasyQueryBootstrapper` 构建 `EasyQueryClient`（绑定 `DataSource` 和 `MySQLDatabaseConfiguration` 方言），再用 `DefaultEasyEntityQuery(client)` 包装成 `EasyEntityQuery`。
- `setPrintSql(true)` 强烈建议开发期开启，能看到实际发出的 SQL。
- 查询里的 `it.age()` 这种属性访问方法来自 KSP 生成的代理类，所以**必须先成功跑过一次 KSP 生成**。

---

## 落地步骤清单
1. `build.gradle.kts` 里加 `com.google.devtools.ksp` 插件（版本对齐 Kotlin），依赖里加 `ksp("com.easy-query:sql-ksp-processor:...")` 以及 api / mysql / 驱动 / 连接池。
2. 把 `build/generated/ksp/main/kotlin` 加进 main 源码集。
3. 写带 `@Table` + `@EntityProxy` 的实体，实现 `ProxyEntityAvailable`。
4. 跑一次 `./gradlew kspKotlin`（或 build）生成代理类。
5. main 里按上面两步初始化 `EasyEntityQuery`，复用单例。

---

## 一句话总结
**不要用 kapt，用 KSP**（easy-query 官方 Kotlin 处理器就是 KSP），KSP 插件版本要和 Kotlin 版本对齐；其余按上面的依赖、实体、初始化代码接即可。
