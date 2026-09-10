# 预编译组件：二进制检查与处置

适用于未随本仓重新编译的 SDK/starter。先处理无目标兼容证据、直接依赖变化 API、未触达关键路径或已有链接错误的组件；按发现扩大到关联类/模块，不把所有第三方 jar 的全量反汇编作为每仓必选任务。

## 取得可核对的证据

1. 记录调用方 jar 的精确坐标、来源、SHA256、触发类/方法；记录目标实际 classpath、JDK、profile、启动入口与制品标识。依赖树是起点，外置容器、手工/shaded jar、重复类及实际加载来源也要核查。
2. `jdeps -verbose:class` 用于定位类/包依赖与缺失类，**不能证明方法或字段签名兼容**。用 `javap -p -c -s -verbose` 检查调用方，核对 owner、成员名、JVM descriptor（含返回类型）、调用指令/静态性；再用目标 jar 的 `javap -p -s` 核对成员、父类/接口及可见性。不能因方法不在本类声明中就忽略继承后判为删除。[jdeps](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jdeps.html)、[javap](https://docs.oracle.com/en/java/javase/21/docs/specs/man/javap.html)
   **签名存在仍可能不兼容**：核对参数/返回值及接收对象的实际类型、接口实现与继承关系是否变化，查看调用前的数据来源、checkcast 和后续 invokeinterface；不能仅凭目标成员存在判定调用安全。
3. 下列为 PowerShell 参数模板。先填写已解析的独立 jar/class 目录和目标运行 JDK major；classpath 分隔符 Windows 为 `;`，Unix 为 `:`。JDK 工具需可调用，不假定只有 JRE 的机器提供它们。

```powershell
$sdkJar = '<调用方 jar 绝对路径>'
$sdkClass = '<实际调用方全限定类名>'
$targetClasspath = '<已核实的目标 classpath>'
$targetApiClass = '<被调用 API 全限定类名>'
$runtimeMajor = '<目标运行 JDK major>'
jar tf $sdkJar
if ($LASTEXITCODE -ne 0) { throw 'jar enumeration failed' }
jdeps --multi-release $runtimeMajor -verbose:class --class-path $targetClasspath $sdkJar
if ($LASTEXITCODE -ne 0) { throw 'jdeps failed; inspect diagnostics' }
javap --multi-release $runtimeMajor -p -c -s -verbose -classpath $sdkJar $sdkClass
if ($LASTEXITCODE -ne 0) { throw 'caller disassembly failed' }
javap --multi-release $runtimeMajor -p -s -classpath $targetClasspath $targetApiClass
if ($LASTEXITCODE -ne 0) { throw 'target API inspection failed' }
```

从 `jar tf` 结果选实际 class，包含命中的内部类；保留各命令的完整输出，文本过滤仅用于导航。扩大扫描时逐类/分批处理，不能将多个 `.class` 拼接后通过 `unzip ... | javap` 当作合法输入。Boot 嵌套 jar 要先在隔离目录取得实际内部 jar；multi-release jar 按目标 JDK 选择版本，不能只看 base classes。

**命中后检查同一 jar**：一旦确认一个调用不兼容，对该 jar 的全部有效 class（含内部类、目标 JDK 选中的 multi-release 类）逐类/分批执行上述 javap，检索已发现的成员 descriptor 及相关类型关系变化；必要时扩展到关联 companion jar。登记总类数、成功分析数、失败/未覆盖项及每个命中的调用类/方法、实际入参来源、已触达/未触达/未知和处置。不要修首个堆栈后就称 SDK 已适配，也不把搜到 MultiValueMap/RestTemplate 名称直接判成缺陷；无法完成的覆盖仍记缺口。

类依赖与已知删除项只能提供线索：方法句柄/invokedynamic、反射、ServiceLoader、动态生成类、JNI 等不能靠简单字符串搜索完整验证。编译期常量（如旧 JSON UTF8 字符串常量）可能已内联，没有字段名引用也不能证明协议行为不变。未扫描/无法判断的部分记 unknown，零命中不等于全部兼容。

## 已知 API 线索：连接超时

`HttpComponentsClientHttpRequestFactory.setConnectTimeout(int)` 在 [Framework 6.2 API](https://docs.spring.io/spring-framework/docs/6.2.x/javadoc-api/org/springframework/http/client/HttpComponentsClientHttpRequestFactory.html) 中存在，在 [7.0 API](https://docs.spring.io/spring-framework/docs/7.0.x/javadoc-api/org/springframework/http/client/HttpComponentsClientHttpRequestFactory.html) 中已移除；`setConnectionRequestTimeout` 与 `setReadTimeout` 仍有对应重载。执行时仍核对实际目标 jar，不能把本例扩展成整个类或包都删除。

修复须保留连接建立、连接池租用、响应/读取、TLS 等各自的超时语义和原有可配置性。按实际 HttpClient 版本配置 client/connection manager；当前 [RequestConfig.Builder](https://hc.apache.org/httpcomponents-client-5.6.x/current/httpclient5/apidocs/org/apache/hc/client5/http/config/RequestConfig.Builder.html) 的 connect timeout setter 已废弃并指向 `ConnectionConfig.Builder`。不把“统一搬到 RequestConfig”或固定 5000ms 写成通用修复，不能以取消超时、放宽 TLS/鉴权换取通过；用受控服务验证受影响行为。

## 已知 API 线索：HttpHeaders 与 MultiValueMap

Framework 7 的 `HttpHeaders` 不再实现 `MultiValueMap`，见 [官方变更](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-7.0-Release-Notes#httpheaders-changes)。这是类型契约变化，不只是删除方法；[HttpEntity 的旧 MultiValueMap 构造器](https://docs.spring.io/spring-framework/docs/7.0.x/javadoc-api/org/springframework/http/HttpEntity.html) 仍存在但已标记待移除。检查同一 SDK 的 javap 输出，重点定位以下旧调用及 headers-only、RequestEntity/ResponseEntity 等相关入口：

```text
org/springframework/http/HttpEntity."<init>":(Ljava/lang/Object;Lorg/springframework/util/MultiValueMap;)V
org/springframework/http/HttpHeaders."<init>":(Lorg/springframework/util/MultiValueMap;)V
```

逐个追实际入参：若旧字节码将 `HttpHeaders` 当作 MultiValueMap 传入且无有效适配，可能将其作为 backing map 保存，在后续 `isEmpty()` 等接口调用处抛 `IncompatibleClassChangeError`；不一定构造时就失败。真正实现 MultiValueMap 的实参不因命中此 descriptor 自动失败；也不是所有 Spring 6 SDK 都受影响。

复现优先运行原 SDK，或将最小调用方针对旧 API 编译后，仅切换到目标运行 classpath；用 javap 确认 descriptor、实际对象来源和指令序列与原调用一致，再触发 headers 读取/实际请求。不要把针对新 API 重新编译的调用当旧字节码复现。反射、显式强转或 MethodHandle 适配可在进入构造器前因参数检查失败，异常位置/类型可能不同；可作辅助探测，不能代替原始路径复现，更不规定反射必然抛某一种异常。[Constructor.newInstance](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/Constructor.html)

在调用方按目标 API 使用 HttpHeaders 重载，确需 map 边界时提供真正相容的表示；目标的 `asMultiValueMap()` 也已废弃，不作为全仓机械替换。验证 header 大小写、多值、空值/缺失、只读/复制语义及请求契约，不能用 `(MultiValueMap) (Object) headers` 强转绕过类型变化。

## 处置与验收

优先采用维护方兼容版本或官方扩展点/适配配置；有可维护源码时修补重建并使用可追溯的新制品坐标。不能静默覆盖本地缓存/私服中同一坐标的 jar，再以哈希相同或 BUILD SUCCESS 宣称修复；摘要只证明文件一致性，不证明来源或行为兼容。

同包名类覆盖仅作已有范围允许且替代方案不足时的**例外兼容桥**，不作为默认第二步，也不把“按反编译结果 1:1 移植”当作行为等价保证。采用时必须：

- 登记原 SDK 坐标/哈希、覆盖类、差异原因、维护责任、退出条件；核对构造器、字段/方法签名、内部类、静态初始化及包内访问，评估签名/sealed package/模块边界等实际约束。
- 在实际支持的 fat jar、容器/WAR、启动器等入口验证类来源与 ClassLoader；可用目标 JDK 的类加载日志或 `Class.getProtectionDomain().getCodeSource()` 等诊断。不把 `BOOT-INF/classes` 在某次运行优先于 `BOOT-INF/lib` 推广成所有启动方式的保证。
- 用**最终打包制品**触发原失败 Bean/SDK 调用，验证超时、TLS、鉴权及资源释放等受影响语义。只编译、检查覆盖类字节码或加载类而不调用均不足；未选中的原 SDK 类仍有旧引用与实际路径仍调用旧类须分开判断。
- 升级 SDK 后重新确认覆盖是否必要，满足退出条件即移除并复测；运行与契约未通过仍为 implemented-unverified，全部适用验证通过且桥保留才为 verified-with-bridges。

**覆盖范围不得自动扩大到框架核心**：优先将修补限制在 SDK 自有调用类；SDK 类覆盖无法解决时，不自动进入覆盖 `org.springframework.*` 的下一档。框架类覆盖须单独说明替代方案为何不可行、影响面和维护方案，确认在授权范围内。以 HttpEntity 为例，除原 SDK 路径外，还需核对 RequestEntity/ResponseEntity 等继承链的构造器 descriptor、字段/方法契约及 HTTP 客户端/MVC 等实际消费者回归。仍须满足前述最终制品加载来源及桥接验收；只修一个 token/GET 调用不足以覆盖全局框架替换，无法验证时保持未验证/阻塞。

不默认直接改 jar 字节码、降级单个 Spring jar、关闭鉴权或移除关键 Bean 来绕过失效调用。无可维护兼容路径时如实阻塞；仍可继续独立诊断。静态检查与隔离 consumer 测试补覆盖，不替代完整应用及部署形态验收。
