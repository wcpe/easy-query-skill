# 字段 ↔ 列的映射扩展（转换器 / TypeHandler / 加密）

控制一个 Java 字段如何读写数据库列，有三个由浅入深的扩展点：

| 扩展点 | 绑定方式 | 典型场景 |
|--------|----------|----------|
| **ValueConverter**（值转换器） | `@Column(conversion = X.class)` | 枚举 ↔ 数字/字符串；对象/集合 ↔ JSON 字符串 |
| **JdbcTypeHandler**（类型处理器） | `@Column(typeHandler = X.class)` | 对接特殊 JDBC 类型，如 PG 的 jsonb、自定义日期格式 |
| **@Encryption**（列加密） | `@Encryption(strategy = X.class)` | 手机号/地址等敏感列透明加解密 |

经验：能用 ValueConverter 解决就别上 TypeHandler——前者在"值"层面转换、跨方言通用；后者直接操作
`PreparedStatement`/`ResultSet`，多用于特定数据库类型。

## 1. ValueConverter —— 枚举与 JSON 列

接口 `ValueConverter<TProperty, TProvider>`（包 `com.easy.query.core.basic.extension.conversion`），
`serialize` 写库、`deserialize` 读库。绑定到字段：`@Column(conversion = XxxConverter.class)`。

枚举 ↔ 数字：
```java
import com.easy.query.core.basic.extension.conversion.ValueConverter;
import com.easy.query.core.metadata.ColumnMetadata;

public class TopicTypeConverter implements ValueConverter<TopicTypeEnum, Integer> {
    @Override public Integer serialize(TopicTypeEnum e, ColumnMetadata c) { return e == null ? null : e.getCode(); }
    @Override public TopicTypeEnum deserialize(Integer code, ColumnMetadata c) { return TopicTypeEnum.fromCode(code); }
}

// 实体字段
@Column(conversion = TopicTypeConverter.class)
private TopicTypeEnum topicType;
```

对象/集合 ↔ JSON 字符串（用你项目的 JSON 库，如 fastjson2/jackson）：
```java
public class JsonConverter implements ValueConverter<Object, String> {
    @Override public String serialize(Object o, ColumnMetadata c) { return o == null ? null : JSON.toJSONString(o); }
    @Override public Object deserialize(String s, ColumnMetadata c) {
        return EasyStringUtil.isBlank(s) ? null : JSON.parseObject(s, c.getPropertyType());
    }
}

@Column(conversion = JsonConverter.class)
private TopicExtra extra;                 // 单对象
@Column(conversion = JsonConverter.class)
private List<TopicTag> tags;             // 集合
```

**自动应用（免逐字段标注）**：实现 `ValueAutoConverter<TProperty, TProvider>`（多一个
`apply(entityClass, propertyType)`），并在 bootstrap 注册 `configuration.applyValueConverter(new EnumConverter())`，
之后所有匹配 `apply` 的字段（如所有枚举）自动转换，无需写 `@Column(conversion=...)`。

## 2. JdbcTypeHandler —— 直接控制 JDBC 读写

接口 `JdbcTypeHandler`（包 `com.easy.query.core.basic.jdbc.types.handler`）：
`getValue(JdbcProperty, StreamResultSet)` 读、`setParameter(EasyParameter)` 写。绑定：
`@Column(typeHandler = XxxHandler.class)`。

```java
import com.easy.query.core.basic.jdbc.types.handler.JdbcTypeHandler;

// 例：SQLite 把 LocalDateTime 以字符串存取
public class SQLiteLocalDateTimeTypeHandler implements JdbcTypeHandler {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    @Override public Object getValue(JdbcProperty p, StreamResultSet rs) throws SQLException {
        Timestamp ts = rs.getTimestamp(p.getJdbcIndex());
        return ts == null ? null : ts.toLocalDateTime();
    }
    @Override public void setParameter(EasyParameter parameter) throws SQLException {
        LocalDateTime v = (LocalDateTime) parameter.getValue();
        parameter.getPs().setString(parameter.getIndex(), v.format(FMT));
    }
}

@Column(typeHandler = SQLiteLocalDateTimeTypeHandler.class)
private LocalDateTime createTime;
```
PG 的 jsonb 列同理：在 `setParameter` 里 `new PGobject().setType("jsonb")`。

## 3. @Encryption —— 列加密（可选模糊查询）

注解 `@Encryption`（包 `com.easy.query.core.annotation`），属性 `strategy`（必填）和
`supportQueryLike`（默认 false，true 时支持对密文做 LIKE）。策略接口 `EncryptionStrategy`
（包 `com.easy.query.core.basic.extension.encryption`）：`encrypt(...)` / `decrypt(...)`。

```java
import com.easy.query.core.annotation.Encryption;
import com.easy.query.core.basic.extension.encryption.EncryptionStrategy;

public class Base64EncryptionStrategy implements EncryptionStrategy {
    @Override public Object encrypt(Class<?> e, String prop, Object plain) {
        return plain == null ? null : Base64.getEncoder().encodeToString(plain.toString().getBytes(StandardCharsets.UTF_8));
    }
    @Override public Object decrypt(Class<?> e, String prop, Object cipher) {
        return cipher == null ? null : new String(Base64.getDecoder().decode(cipher.toString()), StandardCharsets.UTF_8);
    }
}

@Data @Table("t_sys_user") @EntityProxy
public class SysUser implements ProxyEntityAvailable<SysUser, SysUserProxy> {
    @Column(primaryKey = true) private String id;
    @Encryption(strategy = Base64EncryptionStrategy.class) private String phone;
    @Encryption(strategy = MyAesStrategy.class, supportQueryLike = true) private String address; // 可 LIKE
}
```
框架还提供 AES 基类 `AbstractUnSupportEmojiAesBase64EncryptionStrategy` /
`AbstractSupportEmojiAesBase64EncryptionStrategy`（重写 `getKey()` / `getIv()` 即可）。
策略需在 bootstrap 注册：`configuration.applyEncryptionStrategy(new Base64EncryptionStrategy())`
（Spring Boot 下用 `@Component` 自动注册）。

`supportQueryLike = false` 的加密列只能整体 `eq`，不能 LIKE/排序/范围（密文无序）。

## 常见错误

- 给 JSON 列手写 `like`/`order by` 业务条件——JSON 文本列无法当结构化列用。
- 用 TypeHandler 做枚举/JSON 这类纯值转换——应优先 ValueConverter（更通用）。
- 加密列设了 `supportQueryLike=false` 却要模糊查询——改 true 或换可检索方案。
- 自定义转换器/加密策略忘了注册（非 Spring 漏 `applyXxx`，Spring 漏 `@Component`）。

## Sources
- 源码验证: `ValueConverter`/`ValueAutoConverter` @ `com.easy.query.core.basic.extension.conversion`
  (`sql-test/.../conversion/{EnumValueConverter,JsonConverter}.java`，实体 `.../entity/TopicTypeArrayJson.java`)；
  `JdbcTypeHandler` @ `com.easy.query.core.basic.jdbc.types.handler`
  (`sql-test/.../common/SQLiteLocalDateTimeTypeHandler.java`)；`@Encryption` @ `com.easy.query.core.annotation`，
  `EncryptionStrategy` @ `com.easy.query.core.basic.extension.encryption`
  (`sql-test/.../entity/SysUserEncryption.java`，`BaseTest` `applyEncryptionStrategy`/`applyValueConverter`)。
- 官方文档: `easy-query-doc/src/adv/{value-converter,type-handler,column-encryption}.md`。
