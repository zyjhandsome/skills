# OpenRewrite 与构建命令

## 使用原则

OpenRewrite 负责可解析范围内的结构化转换，不保证私有框架或业务兼容。没有可用 recipe 时可手工迁移。不要因此安装无关工具或把企业源码上传第三方服务。

无论 recipe 已运行还是改用手工路径，覆盖记录都应包含：Java 移除/搬家 API、starter/BOM、应用与部署属性键（含外部配置）、预编译 SDK。只 grep 旧 Java 包名不能结项；配置按 [离线绑定预检](verification.md#离线配置绑定预检) 补证据，不能因“没跑 Rewrite”或“recipe 无差异”省略。

核实并固定三个不同对象：构建插件版本、recipe artifact 版本、活动 recipe ID。Maven 与 Gradle 插件有不同版本线，不能共用一个版本号。查官方 recipe 当前定义和本地 discover 输出，确认组合配方是否已经包含 Framework/Security/Jackson/Data 等子配方，避免盲目叠加或引用不存在的 ID。

候选 ID（执行前必须在所选 artifact 中确认）：

| 阶段 | 候选 |
|---|---|
| 3.x → 3.5 | `org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5` |
| 3.5 → 4.0 | `org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0` |

Community/Moderne Edition 的坐标、能力、许可与分发方式可能不同。**按精确 artifact 检查可用来源**：先沿用企业允许的已配置镜像/仓库，再核实 Maven Central 是否提供选定坐标；只有所需版本/Edition 确实需要 Code Genome 等来源时，才检查已有授权和凭证。2026-09-09 已确认 Central 的 `rewrite-spring:6.37.1` 和 Maven 插件 `6.46.1` POM 返回 HTTP 200；这是可用性实例，不保证整套传递依赖在每个企业环境可解析，也不固定为未来默认版本。

不要求每次同时尝试两个远端，不绕过企业镜像限制，不因看到认证文档就放弃 Central 已有版本。无法解析时先分类 404/401/代理或网络问题；可用版本还必须通过 discover 确认覆盖。所有合适来源均不可用时只把 OpenRewrite 路径标为 unavailable，继续可行的手工路线，不把 OR 下载失败等同整个升级失败。不得直接写入新仓库/明文凭证或自动采用付费服务。

在批次记录中写精确版本和 recipe 列表。不要照抄文档里的 `RELEASE`、`latest.release` 或版本范围；配方内部也可能把 Boot 升到 `4.0.x` 最新。检查生成补丁是否等于本批锁定版本；不一致时固定相关子配方的目标或在审查后的编辑中对齐到锁定版本，再做解析和全套验证。用户固定较旧补丁时还须核实配方生成的 API 适用于它。

## Maven

优先项目 wrapper：POSIX `./mvnw`，PowerShell `./mvnw.cmd`；没有 wrapper 才用匹配 CI 的 Maven。下面为 **PowerShell 命令模板**，先将尖括号变量替换为核实后的真实值；POSIX 对应使用 shell 变量与参数引用。

### 阶段 A：先到 3.5

这些是分段执行模板，assess 模式只展示不应用。先在当前快照完成基线。将占位精确版本和环境参数填实；使用 `.cmd` 的命令块适用于 PowerShell。

```powershell
$rewritePluginVersion = '<已核实的 Maven 插件精确版本>'
$rewriteSpringVersion = '<已核实的 rewrite-spring 精确版本>'
$activeRecipe = 'org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5'
$rewritePlugin = "org.openrewrite.maven:rewrite-maven-plugin:${rewritePluginVersion}"
$recipeArtifact = "org.openrewrite.recipe:rewrite-spring:${rewriteSpringVersion}"
$rewriteArgs = @("-Drewrite.recipeArtifactCoordinates=$recipeArtifact", "-Drewrite.activeRecipes=$activeRecipe", '-Drewrite.exportDatatables=true')
& ./mvnw.cmd "${rewritePlugin}:discover" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw 'Recipe discovery failed' }
& ./mvnw.cmd "${rewritePlugin}:dryRun" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw 'Inspect dry-run results before continuing' }
```

每个命令后检查 `$LASTEXITCODE`，失败先处理，不直接接着 run。沿用仓库必要的 `-P`、settings 和模块范围。多模块从正确 reactor 根执行；先检查测试夹具、生成源、聚合模块和 Kotlin 的解析覆盖。

读取命令输出给出的 patch 路径，常见为各模块 `target/rewrite/rewrite.patch`；同时检查 data tables 的 source parse/error 信息。补丁位置以实际日志为准。dry-run 后 `git diff` 可能只显示临时插件配置，**不能代替阅读 patch**。

确认补丁在范围内且无解析遗漏后应用同一组版本/配置：

```powershell
& ./mvnw.cmd "${rewritePlugin}:run" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw '3.5 migration failed' }
```

检查实际 diff，完成 3.5 精确版本对齐、源码/配置补充和完整验证，并留存检查点。不要把裸 `verify` 当成每个仓库的完整验收；加实际 CI profile、集成测试和隔离启动/consumer。命令行调用可避免持久插件配置；如必须写 POM，保留原有配置，完成后清除本次临时配置。

### 阶段 B：已有合格 3.5 检查点才应用 4.0

沿用阶段 A 已核实的插件变量、实际 reactor/profile 参数。先按 [证据契约](evidence-contract.md) 填写阶段记录并检查当前代码快照；没有 Python 时按同一条件人工检查并留证，不把复制下列命令当作获得授权。

```powershell
$contractFile = '<已填写的证据契约 JSON 绝对路径>'
$snapshotId = '<当前已核实的代码快照标识>'
$contractChecker = '<Skill绝对路径>/scripts/check_contract.py'
python $contractChecker $contractFile --gate boot4 --snapshot $snapshotId
if ($LASTEXITCODE -ne 0) { throw '3.5 evidence gate not satisfied' }
$activeRecipe = 'org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0'
$rewriteArgs = @("-Drewrite.recipeArtifactCoordinates=$recipeArtifact", "-Drewrite.activeRecipes=$activeRecipe", '-Drewrite.exportDatatables=true')
& ./mvnw.cmd "${rewritePlugin}:discover" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw 'Recipe discovery failed' }
& ./mvnw.cmd "${rewritePlugin}:dryRun" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw 'Inspect dry-run results before continuing' }
```

阅读 patch 与下方审查表后才运行下一段；两段之间发生源码/配置变化须刷新快照及证据，再审查新的 patch。

```powershell
python $contractChecker $contractFile --gate boot4 --snapshot $snapshotId
if ($LASTEXITCODE -ne 0) { throw '3.5 evidence gate not satisfied' }
& ./mvnw.cmd "${rewritePlugin}:run" @rewriteArgs
if ($LASTEXITCODE -ne 0) { throw '4.0 migration failed' }
```

同一 4.x minor 内补丁更新不使用这两段跨 major 模板，直接按 owner 更新精确补丁并验证。dry-run 若因已配置 `failOnDryRunResults` 检测到预期变更而非解析错误返回非零，先归因并记录，再决定后续；不要忽略所有非零退出。

## 配方补丁的允许、需论证和拒绝项

| 类别 | 示例 | 处置 |
|---|---|---|
| 升级必需、目标 API 有证据 | parent/BOM、废弃 starter 替换、已移除 API、对应测试包 | 在锁定版本/模块内应用并验收 |
| 配方附带且不一定必要 | 移除 `@Autowired`、添加 `@DependsOnDatabaseInitialization`、改测试属性、风格重构 | 查触发原因和行为影响；有迁移必要性才保留，否则排除/精确还原本次改动 |
| 越界或破坏契约 | 擅升 JDK、全依赖 latest、关闭鉴权/校验、删除测试、改变业务模型、改未授权模块 | 不应用；缩小 recipe 或改人工路线 |

复合配方可嵌套旧版本迁移与 best practices，不能仅凭顶层名字接受全部修改；但包含旧配方不意味着每个子配方实际都改了代码。记录实际 patch，不把上述清单当作字符串封禁器。

## Gradle（Groovy 与 Kotlin DSL）

优先已有 rewrite 配置；否则依据所选插件的官方运行说明，使用临时 init script 或最小范围的 build 配置。不要对未知 Gradle 结构生成一个宣称通用的 init script：settings/pluginManagement、复合构建、子项目和仓库凭证都影响配置。

**先找 owner，再确定放置位置**：Boot 版本的 catalog/settings/convention/included build 与 rewrite 插件应用位置可能不同。下例只描述选定项目的 DSL 结构，不表示将它粘到根 build；先用 `projects` 和 `:<实际项目>:tasks --all` 确认目标，独立 included build 从自身构建根处理。3.5 阶段通过后才将 `migrationRecipe` 显式切换为 4.0，禁止默认回退到 4.0。

Groovy DSL 最小结构示意（尖括号须替换；与现有 plugins/repositories/dependencies 合并）：

```groovy
plugins {
    id 'org.openrewrite.rewrite' version '<核实后的 Gradle 插件版本>'
}
rewrite {
    activeRecipe(providers.gradleProperty('migrationRecipe').get())
    setExportDatatables(true)
}
dependencies {
    rewrite 'org.openrewrite.recipe:rewrite-spring:<核实后的 recipe 版本>'
}
```

Kotlin DSL 对应结构：

```kotlin
plugins {
    id("org.openrewrite.rewrite") version "<核实后的 Gradle 插件版本>"
}
rewrite {
    activeRecipe(providers.gradleProperty("migrationRecipe").get())
    setExportDatatables(true)
}
dependencies {
    rewrite("org.openrewrite.recipe:rewrite-spring:<核实后的 recipe 版本>")
}
```

依赖仓库沿用已核实配置。Gradle wrapper 在 Windows 用 `./gradlew.bat`，POSIX 用 `./gradlew`。先运行 `tasks --all` 和 `rewriteDiscover` 确认插件已应用到正确项目；再运行 `rewriteDryRun`。查看日志给出的补丁，常见为 `build/reports/rewrite/rewrite.patch`，确认后运行 `rewriteRun`。多项目任务用实际 project path；不要把 Maven 的参数或未经验证的 `-Prewrite.activeRecipe` 直接套到 Gradle。此示例通过 DSL 显式指定 recipe。

选定项目的分阶段调用示意（`:service` 必须替换为实际 task owner；同一 `migrationRecipe` 参数也用于 discover/run）：

```powershell
& ./gradlew.bat :service:rewriteDryRun '-PmigrationRecipe=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_5'
```

审查后以同一属性运行 `:service:rewriteRun`，再按实际任务验证 3.5 并留存检查点。然后才运行阶段 B：

```powershell
python $contractChecker $contractFile --gate boot4 --snapshot $snapshotId
if ($LASTEXITCODE -ne 0) { throw '3.5 evidence gate not satisfied' }
& ./gradlew.bat :service:rewriteDryRun '-PmigrationRecipe=org.openrewrite.java.spring.boot4.UpgradeSpringBoot_4_0'
```

其中三个校验变量的含义同 Maven 阶段 B，需要自行填实。审查后重新核验条件，以同一属性运行 `:service:rewriteRun`；配方属性是上方 DSL 自定义绑定，不是假定插件原生支持它。每条命令检查退出码，失败归因后再推进。

更新实际 Boot 版本 owner（可能是 version catalog/settings/convention plugin），对齐 lockfiles 和已有 dependency verification metadata 时只做有依据的变化，不关闭验证。移除自己添加的临时配置后再完整构建。

## 构建取证命令

以下以 POSIX wrapper 表示，在 Windows 替换文件名。先确认本仓插件绑定无外部写入副作用，再选用。

| 目的 | Maven 示例 | Gradle 示例 |
|---|---|---|
| 工具链 | `./mvnw -version` | `./gradlew --version` |
| 生效配置 | `./mvnw help:effective-pom -Doutput=<证据目录>/effective-pom.xml`（按模块/profile） | 检查 settings/catalog/convention，结合下列实际解析 |
| 生产依赖 | `./mvnw dependency:tree -Dverbose` | `./gradlew :app:dependencies --configuration runtimeClasspath` |
| 测试依赖 | `./mvnw dependency:tree -Dscope=test` | `./gradlew :app:dependencies --configuration testRuntimeClasspath` |
| 特定仲裁 | effective-pom + 依赖树 | `./gradlew :app:dependencyInsight --dependency spring-core --configuration runtimeClasspath` |
| 完整验证 | `./mvnw verify` 加 CI 的 profiles | `./gradlew build` 加实际集成测试 task |

`:app` 和输出路径是占位，不是默认项目结构。Maven `verify` 未配置 Failsafe 不会凭空执行集成测试；Gradle `build` 也不保证包含自定义 `integrationTest`。记录真实执行任务和测试数。

来源：[Boot 4.0 Community recipe 及用法](https://docs.openrewrite.org/recipes/java/spring/boot4/upgradespringboot_4_0-community-edition)、[OpenRewrite Maven 插件参数与目标](https://docs.openrewrite.org/reference/rewrite-maven-plugin)、[OpenRewrite Gradle 插件参数与任务](https://docs.openrewrite.org/reference/gradle-plugin-configuration)。
