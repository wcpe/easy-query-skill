# Entity mapping & the proxy model

How an easy-query entity is declared and how its proxy works. This is the foundation every other reference
builds on.

## The proxy model in one paragraph

Each entity is paired with a generated `*Proxy` class. You annotate the entity with `@EntityProxy` and make
it `implements ProxyEntityAvailable<Entity, EntityProxy>`. At compile time the processor (APT for Java, KSP
for Kotlin) generates `<entity-package>.proxy.<Entity>Proxy`, which extends `AbstractProxyEntity` and exposes
one typed column accessor per field (`id()`, `title()`, …). The proxy is what gives you the strong-typed DSL
inside `where(o -> o.title().eq(x))` — `o` is the proxy. You never hand-write or edit the proxy.

## Core annotations

| Annotation | Package | Purpose |
|------------|---------|---------|
| `@Table("t_name")` | `com.easy.query.core.annotation` | Maps the class to a table. |
| `@EntityProxy` | `com.easy.query.core.annotation` | Triggers proxy generation. |
| `@Column(...)` | `com.easy.query.core.annotation` | Per-column options (see below). |
| `@Version(strategy = ...)` | `com.easy.query.core.annotation` | Optimistic-lock column. |
| `@LogicDelete(strategy = ...)` | `com.easy.query.core.annotation` | Soft-delete column. |
| `@Navigate(...)` | `com.easy.query.core.annotation` | Relation to another entity (see `relation-query.md`). |
| `@Encryption(...)` | `com.easy.query.core.annotation` | Encrypt a column (see `type-mapping.md`). |
| `@UpdateIgnore` / `@InsertIgnore` | `com.easy.query.core.annotation` | Exclude a field from update / insert (audit fields; see `interceptors.md`). |
| `@ValueObject` | `com.easy.query.core.annotation` | Embed a nested value object as flattened columns. |

### `@Column` options

- `primaryKey = true` — marks the primary key.
- `generatedKey = true` — DB-generated key (auto-increment); backfilled after insert.
- `value = "col_name"` — explicit column name (otherwise name-conversion applies, default snake_case).
- `exist = false` — field is **not** a DB column (computed/transient).
- `autoSelect` — whether the column is included in `SELECT *` by default.
- `conversion = X.class` — value converter for enum/JSON columns (see `type-mapping.md`).
- `typeHandler = X.class` — custom JDBC type handler (see `type-mapping.md`).
- `primaryKeyGenerator = X.class` — auto-generate the PK on insert, e.g. UUID/snowflake (see `advanced.md`).

## A complete annotated entity (Java)

```java
package com.test.entity;

import com.easy.query.core.annotation.*;
import com.easy.query.core.basic.extension.logicdel.LogicDeleteStrategyEnum;
import com.easy.query.core.basic.extension.version.VersionLongStrategy;
import com.easy.query.core.proxy.ProxyEntityAvailable;
import com.test.entity.proxy.SysUserProxy;
import lombok.Data;

@Data
@Table("t_sys_user")
@EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {

    @Column(primaryKey = true)
    private String id;

    private String username;
    private String phone;

    @Column(value = "id_card")     // explicit column name
    private String idCard;

    @Column(exist = false)         // not persisted
    private String displayLabel;

    @Version(strategy = VersionLongStrategy.class)
    private Long version;

    @LogicDelete(strategy = LogicDeleteStrategyEnum.BOOLEAN)
    private Boolean deleted;
}
```

## The same entity in Kotlin

```kotlin
package com.test.entity

import com.easy.query.core.annotation.*
import com.easy.query.core.basic.extension.logicdel.LogicDeleteStrategyEnum
import com.easy.query.core.basic.extension.version.VersionLongStrategy
import com.easy.query.core.proxy.ProxyEntityAvailable
import com.test.entity.proxy.SysUserProxy

@Table("t_sys_user")
@EntityProxy
class SysUser : ProxyEntityAvailable<SysUser, SysUserProxy> {
    @Column(primaryKey = true)
    var id: String? = null
    var username: String? = null
    var phone: String? = null
    @Column(value = "id_card")
    var idCard: String? = null
    @Version(strategy = VersionLongStrategy::class)
    var version: Long? = null
    @LogicDelete(strategy = LogicDeleteStrategyEnum.BOOLEAN)
    var deleted: Boolean? = null
}
```

## What logic-delete and version mean at runtime

- **`@LogicDelete`**: `deletable(...).executeRows()` becomes an `UPDATE ... SET deleted = ?`, and every query
  automatically appends `WHERE deleted = <not-deleted>`. To truly delete a row, see the physical-delete escape
  hatch in `write.md`.
- **`@Version`**: updates append `WHERE version = ?` and bump the version; a `0` row count means the row was
  changed concurrently. Controlled via `withVersion(...)` / `ignoreVersion()` — see `write.md`.

## Value objects — `@ValueObject` (embed nested columns)

Group several columns into a nested Java object while keeping them as flat columns in the same table. Mark
the nested field `@ValueObject` (`com.easy.query.core.annotation`); it can nest further.

```java
@Table("my_company")
@EntityProxy
public class Company implements ProxyEntityAvailable<Company, CompanyProxy> {
    @Column(primaryKey = true) private String id;
    private String name;
    @ValueObject private CompanyAddress address;   // province/city/area become columns of my_company
}

@Data
public class CompanyAddress {   // plain class, not a @Table
    private String province;
    private String city;
    private String area;
}
```
Insert flattens it to `... (id, name, province, city, area) VALUES (...)`. Query nested props via the proxy
(`o.address().province()`) or string path (`o.eq("address.province", "x")`); `select(o -> o.column("address"))`
selects the whole group.

## Common mistakes

- Missing `implements ProxyEntityAvailable<Entity, EntityProxy>` → no proxy, no strong-typed DSL.
- Importing the wrong `proxy.<Entity>Proxy` (it lives in the `.proxy` subpackage of the entity).
- Putting business-only fields without `@Column(exist = false)` → easy-query tries to map them to columns.
- Confusing logic-delete with physical delete (see `write.md`).

## Sources
- 源码验证: `sql-test/.../entity/SysUserVersionLongLogicDel.java`, `.../entity/Topic.java`; annotations @
  `com.easy.query.core.annotation`; `LogicDeleteStrategyEnum` @
  `com.easy.query.core.basic.extension.logicdel`; `VersionLongStrategy` @
  `com.easy.query.core.basic.extension.version`. Skill baseline 3.1.89-dev.
