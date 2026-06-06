# Topic 实体定义与查询（Kotlin + easy-query）

## 1. 实体定义

easy-query 在 Kotlin 中通常使用注解 `@Table` / `@Column` 来映射实体，并配合代码生成的 proxy 类（APT/KSP）来支持类型安全的 lambda 查询。

```kotlin
package com.example.entity

import com.easy.query.core.annotation.Column
import com.easy.query.core.annotation.EntityProxy
import com.easy.query.core.annotation.Table
import com.easy.query.core.proxy.ProxyEntityAvailable
import com.example.entity.proxy.TopicProxy
import java.time.LocalDateTime

@Table("t_topic")
@EntityProxy
data class Topic(
    @Column(primaryKey = true)
    var id: String = "",
    var stars: Int = 0,
    var title: String = "",
    var createTime: LocalDateTime = LocalDateTime.now(),
) : ProxyEntityAvailable<Topic, TopicProxy> {

    // 由 easy-query 的注解处理器（APT/KSP）自动生成，需在构建后保留
    override fun createProxy(): TopicProxy = TopicProxy()
}
```

说明：
- `@Table("t_topic")` 指定表名。
- `@Column(primaryKey = true)` 标记主键字段 `id`（String 类型）。
- `createTime` 用 `java.time.LocalDateTime` 映射数据库的时间字段（也可换成 `java.util.Date`）。
- `@EntityProxy` + `ProxyEntityAvailable<Topic, TopicProxy>` 让该实体支持 easy-query 的 Kotlin 类型安全 lambda 写法（`TopicProxy` 由注解处理器生成，编译后即可用）。

如果你的项目用的是 KSP，需要在 `build.gradle.kts` 中添加 easy-query 的 KSP 处理器依赖；用 APT（kapt）同理。

## 2. 查询：stars > 100，按 createTime 倒序，取前 N 条

```kotlin
package com.example.repository

import com.easy.query.api.proxy.client.EasyEntityQuery
import com.example.entity.Topic

class TopicRepository(private val easyEntityQuery: EasyEntityQuery) {

    /**
     * 查询 stars > 100 的 Topic，按 createTime 倒序，取前 limit 条
     */
    fun findTopStarTopics(limit: Long = 10): List<Topic> {
        return easyEntityQuery
            .queryable(Topic::class.java)
            .where { it.stars().gt(100) }              // WHERE stars > 100
            .orderBy { it.createTime().desc() }         // ORDER BY create_time DESC
            .limit(limit)                               // LIMIT N
            .toList()                                   // 返回 List<Topic>
    }
}
```

调用示例：

```kotlin
fun main() {
    // easyEntityQuery 通常由框架（如 Spring Boot starter）注入，这里假设已获得实例
    val easyEntityQuery: EasyEntityQuery = TODO("从容器/构建器获取 EasyEntityQuery 实例")

    val repo = TopicRepository(easyEntityQuery)
    val topics: List<Topic> = repo.findTopStarTopics(limit = 10)

    topics.forEach { println("${it.id} | stars=${it.stars} | ${it.title} | ${it.createTime}") }
}
```

## 3. 关键点

- `EasyEntityQuery` 是 Kotlin 类型安全 API 的入口。如果用的是 Java 风格 API，则入口为 `EasyQueryClient` + `easyQuery(...)`，lambda 内字段访问写法会不同（用字符串列名或 Java proxy）。
- `where { it.stars().gt(100) }`：`gt` 表示 greater than（大于），即 `stars > 100`。
- `orderBy { it.createTime().desc() }`：倒序。
- `limit(n)`：限制条数，参数为 `Long`。也可用 `limit(offset, rows)` 做分页。
- `toList()` 返回 `List<Topic>`。

## 4. 依赖（Gradle Kotlin DSL，参考）

```kotlin
dependencies {
    implementation("com.easy-query:sql-api-proxy:<version>")
    implementation("com.easy-query:sql-mysql:<version>")     // 按你的数据库选择方言
    ksp("com.easy-query:sql-ksp-processor:<version>")        // KSP 处理器，生成 Proxy 类
}
```

> 请将 `<version>` 替换为你项目实际使用的 easy-query 版本，并确认 KSP/kapt 已正确启用，否则 `TopicProxy` 不会生成、代码无法编译。
