# Setup — Spring Boot

The starter auto-configures `EasyQueryClient` and `EasyEntityQuery` from your `DataSource`. You inject
`EasyEntityQuery` and use it directly.

## When to use / not

Use for a Spring Boot project. You still need the proxy processor on the compile path: **APT (`sql-processor`)
for Java**, **KSP (`sql-ksp-processor`) for Kotlin** (Kotlin Spring projects should use Gradle + KSP — see
`setup-kotlin.md` for the KSP block). Entity definition is identical to `setup-java.md` / `setup-kotlin.md`.

## 1. Dependencies (Maven, Java)

```xml
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-springboot-starter</artifactId>
    <version>3.1.89</version>
</dependency>
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-mysql</artifactId>      <!-- dialect -->
    <version>3.1.89</version>
</dependency>
<dependency>
    <groupId>com.easy-query</groupId>
    <artifactId>sql-processor</artifactId>  <!-- APT; KSP instead for Kotlin -->
    <version>3.1.89</version>
    <scope>provided</scope>
</dependency>
```

## 2. application.yml

The config prefix is `easy-query`. You must set `enable: true` and the `database` dialect.

```yaml
spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://127.0.0.1:3306/mydb?serverTimezone=GMT%2B8&characterEncoding=utf-8&useSSL=false&allowMultiQueries=true&rewriteBatchedStatements=true
    username: root
    password: root

easy-query:
  enable: true              # required — the starter is off by default
  database: mysql           # dialect: mysql / h2 / pgsql / mssql / oracle ...
  name-conversion: underlined   # camel field -> snake column (myProp -> my_prop); default
  print-sql: true           # log generated SQL
  print-nav-sql: true       # log SQL for navigation/relation queries
  delete-throw: true        # throw on an unconditional delete instead of silently running it
```

`enable` defaults to `false` — if you forget it, no beans are created and injection fails. `name-conversion:
underlined` is the default mapping (override per-column with `@Column("custom_name")`).

## 3. Inject and use

```java
import com.easy.query.api.proxy.client.EasyEntityQuery;
import org.springframework.stereotype.Service;

@Service
public class TopicService {

    private final EasyEntityQuery easyEntityQuery;

    public TopicService(EasyEntityQuery easyEntityQuery) {   // constructor injection
        this.easyEntityQuery = easyEntityQuery;
    }

    public List<Topic> search(String title) {
        return easyEntityQuery.queryable(Topic.class)
                .where(o -> o.title().like(title))
                .orderBy(o -> o.createTime().desc())
                .toList();
    }
}
```

Kotlin is the same bean, with the Kotlin lambda surface:

```kotlin
@Service
class TopicService(private val easyEntityQuery: EasyEntityQuery) {
    fun search(title: String): List<Topic> =
        easyEntityQuery.queryable(Topic::class.java)
            .where { it.title().like(title) }
            .orderBy { it.createTime().desc() }
            .toList()
}
```

## Transactions in Spring

Prefer Spring's declarative transactions — `@Transactional` on the service method participates in the host
transaction; don't also open a manual `beginTransaction()` inside it. See `transaction.md`.

## Common mistakes

- Omitting `easy-query.enable: true` → beans not registered, `EasyEntityQuery` injection fails.
- `easy-query.database` not matching the `sql-*` dialect artifact on the classpath.
- Adding `@Transactional` *and* a manual `beginTransaction()` in the same method (double transaction).
- Forgetting the proxy processor (APT/KSP) — entities compile but proxies are missing.

## Sources
- 官方文档: `easy-query-doc/src/guide/spring-boot.md` (application.yml, code-first, navigate).
- 源码验证: `EasyQueryProperties` @ `com.easy.query.sql.starter.config` (keys: enable, database,
  name-conversion, print-sql, print-nav-sql, delete-throw); auto-config registers `EasyQueryClient` and
  `EasyEntityQuery` beans. Starter artifact `sql-springboot-starter`. Skill baseline 3.1.89-dev.
