# 可执行证据契约

本辅助程序只读 JSON 与指定证据文件，不执行命令或改业务仓库。v2 增加实际依赖树解析，v1 不再直接通过。输出 `consistent=true` 表示记录和所读解析结果一致；不能证明日志真实、制品与外置容器加载一致、测试覆盖充分、源码未变或阻止 Agent 越权执行命令。实际阶段条件仍以 SKILL.md 和 verification 为准。

用 [evidence-contract.json](../assets/evidence-contract.json) 开始记录，null/空值故意不能通过校验。不要为了通过校验填入伪造的 passed。已有等价证据系统可继续使用，无需重复造文件。

## 数据约定

- 顶层：`mode`、精确 `source_boot`/`target_boot`，`scope.included` 写模块、profile、JDK/runtime、数据库/功能范围；`excluded` 为 `{item, reason}` 数组。默认必需检查为 resolution/build/tests/runtime/contracts，可追加 security、postgres 等实际范围内的项，不能删除基本项。库模块 runtime 使用 consumer 证据。
- `baseline35` 与 `final`：各包含 `resolved_boot`、`snapshot`、`checks`。快照应覆盖 HEAD **和未提交/未跟踪源码、生成配置、外部测试配置版本**；由执行者/CI 核实并通过 `--snapshot` 提供，不能仅用固定字符串“current”。临时输出目录不属于源码快照。
- `checks` 用检查名索引；每项包含 `status: passed`、`exit_code: 0`、`snapshot`、真实 `command`、`cwd`、`environment`，以及 `artifacts: [{path, sha256}]`。路径相对契约文件或绝对路径，SHA256 对原始字节计算。checks 是已执行记录，不是 shell 调度配置。
- tests 另含非负整数 `executed`（实际执行数量，不含 skipped）、`failures`、`errors`、`skipped`；有跳过写 `skip_coverage_reason`。真实测试报告应作为 artifact，不要仅提供自己写的总结。
- final 另含布尔值 `properties_migrator_present`、`temporary_rewrite_present`（必须 false），`bridges` 数组。空桥允许 verified；保留桥的记录需 component/reason/exit_condition，用 verified-with-bridges。合法的第三方 Jackson 2 依赖不自动计为 Boot 兼容桥。
- `scope.resolution_units` 列出必须验证的应用/consumer 模块、profile/classpath 单元 ID，例如 `app@local:all`；不能用聚合 POM 替代应用。`baseline35` 和 `final` 的 `resolution.units` 须逐单元提供 `id`、`module`、`format`、`tree: {path, sha256}`、`core_artifacts`。后者以完整 GA 为键，记录 spring-boot 和 spring-boot-autoconfigure 版本；校验器从 tree 独立读取并交叉核对，不能只填两个字符串。所有 Boot 模块必须对齐该阶段精确版本。

Maven 使用 `format=maven-json`，module 是 tree 根的 `groupId:artifactId`。从实际应用根、CI 对应 profiles 导出完整非 verbose JSON，不加 includes/excludes/scope 过滤，不复用上次输出；同时保存命令及退出码到 resolution 检查项。使用核实可用的 Maven Dependency Plugin 3.7+ 精确版本，例如：

```text
./mvnw org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree -DoutputType=json -Dverbose=false -DoutputFile=<本模块证据目录>/dependency-tree.json
```

`3.8.1` 是示例版本，执行前检查可解析性；多模块每应用单独路径，防止同一文件被覆盖。校验器检查 selected nodes，不接受带 omitted 标记的 verbose 输出。人工审查仍需确认 profile、未过滤范围和打包后的实际 classpath。[官方 JSON 格式](https://maven.apache.org/plugins/maven-dependency-plugin/examples/tree-mojo.html)

Gradle 支持 `format=gradle-text`，另写 `configuration` 为 compileClasspath/runtimeClasspath/testRuntimeClasspath；每个实际应用的这三个配置分别登记 resolution unit，使用 `:<实际模块>:dependencies --configuration <配置> --console=plain` 原始输出。校验器读取 `->` 后的选中版本，不把 `(c)` 约束当依赖，拒绝 FAILED/(n)。其他自定义配置、复合构建和无法识别的输出须按相同条件人工审查，不把未支持格式或仅手填的 core 摘要判成程序通过。特殊应用没有 autoconfigure 时走有依据的人工验证；程序不提供“跳过 core”开关。

## 调用

以下位置都是使用者填写的参数。Python 3.10+，只用标准库，无需安装库。

```text
python <skill>/scripts/check_contract.py <report.json> --gate boot4 --snapshot <当前核实快照>
python <skill>/scripts/check_contract.py <report.json> --gate verified --snapshot <最终核实快照>
python <skill>/scripts/check_contract.py <report.json> --gate verified-with-bridges --snapshot <最终核实快照>
```

退出码 0 表示结构一致，1 表示缺记录/失败/快照或文件哈希不匹配。boot4 检查当前 3.5 检查点，拒绝 assess、2.x 和 4.x 补丁误用。最终检查只检查最终快照，历史 3.5 检查点保留不同快照是正常的；阶段顺序仍需工作日志核实，程序不从最终报告倒推“历史肯定执行过”。

本契约不依靠“禁止命令字符串”防护：`test -DskipTests`、Gradle `-x test` 或绕过 shell 的工具均可能骗过黑名单。要求实际执行数、必需检查和证据文件；人工审查仍要禁止用跳测试、关闭鉴权、空补丁、单一 health 来满足验收。

## 维护回归

离线运行：

```text
python -m unittest discover -s <skill>/tests -p test_*.py -v
```

回归使用临时合成证据验证拒绝/通过分支，不代表真实 Java 迁移。另有 [Maven MVC 3.4 夹具](../tests/fixtures/maven-mvc-3.4/pom.xml)，复制整个夹具到独立目录后用于 Agent 实跑；不要在 Skill 原目录升级夹具。它覆盖 GET/404、JSON null/日期与 POST validation。已有 Maven 或单独生成的 wrapper 可用 `mvn verify`；仓库实际无 wrapper 时不能假定存在。完整人工前向情景见 [scenarios.md](../tests/scenarios.md)。

[企业 parent 夹具](../tests/fixtures/managed-parent/app/pom.xml) 用于复现版本管理规则：复制 managed-parent 整目录后，从 app 执行 help:effective-pom/tree。默认应看到 core/autoconfigure 3.5.14 与 webmvc starter 4.0.7；`-Pexplicit-management` 应把两个 core 管理项改到 4.0.7。这仅证明覆盖规则和解析检查，不是可运行服务或建议所有项目逐坐标覆盖。夹具未含任何私有厂商组件。
