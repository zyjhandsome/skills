"""Curated disposition options and replacement-library knowledge for open-target packages.

This module holds *stable* knowledge only: which packages have a genuine, officially
motivated successor, and which non-package dispositions a human can pick from. Volatile
data (exact versions, publish dates, deprecation flags) is never stored here; the
generator resolves it from the registry at run time.

Inclusion bar for `REPLACEMENT_FAMILIES` — an entry needs at least one of:
  * the source package is officially deprecated, archived, or in maintenance-only mode;
  * the upstream project itself points at the successor;
  * the platform (Node/browser) absorbed the capability.
Download counts, stars, and "popularity" are never grounds for an entry. A package with
no entry does not mean no alternative exists; it means none has been reviewed here.
"""

from __future__ import annotations

from typing import NamedTuple

REPLACEMENT_MAP_REVIEWED = "2026-07-25"


class ReplacementHint(NamedTuple):
    """One reviewed replacement route for a package.

    Exactly one of `package` (an npm replacement) or `native_api` (a platform
    capability that needs no dependency) is set.
    """

    package: str
    native_api: str
    reason: str
    parity_gap: str


def npm(package: str, reason: str, parity_gap: str) -> ReplacementHint:
    return ReplacementHint(package, "", reason, parity_gap)


def native(api: str, reason: str, parity_gap: str) -> ReplacementHint:
    return ReplacementHint("", api, reason, parity_gap)


REPLACEMENT_FAMILIES: dict[str, tuple[ReplacementHint, ...]] = {
    "axios": (
        npm("ky", "基于 fetch 的小体积 HTTP 客户端，保留拦截器与重试等常用能力。",
            "拦截器、进度事件、Node 与浏览器行为差异需逐项核对。"),
        npm("ofetch", "同构 fetch 封装，自动解析响应并支持拦截钩子。",
            "错误对象结构与取消语义与 axios 不同。"),
        native("fetch / AbortController",
               "Node 18+ 与现代浏览器已内置 fetch，可去掉该依赖。",
               "需自行实现拦截器、超时、进度、XSRF 与统一错误处理。"),
    ),
    "moment": (
        npm("dayjs", "官方在维护模式中建议迁移；dayjs 保持接近 moment 的 API 与插件体系。",
            "插件需显式注册；时区与本地化行为需逐项核对。"),
        npm("date-fns", "官方建议的不可变函数式日期库，利于 tree-shaking。",
            "无链式 API，调用点需重写。"),
        npm("luxon", "由 moment 团队推荐，内置 IANA 时区与 Intl 支持。",
            "对象模型与格式化 token 与 moment 不同。"),
    ),
    "request": (
        npm("undici", "Node 官方维护的 HTTP/1.1 客户端，也是 Node fetch 的底层实现。",
            "API 与 request 完全不同，需重写调用点。"),
        npm("got", "维护活跃的 Node HTTP 客户端，支持重试与流式处理。",
            "仅 Node 环境；错误与重试语义需核对。"),
        native("fetch", "request 已于 2020 年官方弃用；Node 18+ 内置 fetch。",
               "需自行实现重试、cookie jar 与流式上传。"),
    ),
    "node-sass": (
        npm("sass", "node-sass 已被官方弃用，`sass`（Dart Sass）是官方后继实现。",
            "`@import` 已弃用需迁移到 `@use`/`@forward`；部分函数行为不同。"),
    ),
    "tslint": (
        npm("typescript-eslint", "TSLint 已于 2019 年官方弃用并指向 typescript-eslint。",
            "规则集需重新映射；部分 TSLint 规则无一一对应。"),
    ),
    "protractor": (
        npm("@playwright/test", "Protractor 已官方停止维护；Angular 团队建议迁移到现代 E2E 框架。",
            "选择器策略、等待模型与 Angular 同步机制需重写。"),
        npm("cypress", "同为 Angular 团队建议的迁移目标之一。",
            "同源策略与多标签场景存在能力差异。"),
    ),
    "karma": (
        npm("vitest", "Karma 已官方弃用；Vite 生态下的等价测试运行器。",
            "浏览器真实环境测试需改用 browser mode 或 E2E 补齐。"),
        npm("@playwright/test", "需要真实浏览器矩阵时的官方推荐替代。",
            "断言与测试组织方式不同。"),
    ),
    "enzyme": (
        npm("@testing-library/react", "Enzyme 无 React 18+ 官方适配器，社区与 React 团队均指向 Testing Library。",
            "浅渲染与实例内部状态断言无对应能力，用例需按行为重写。"),
    ),
    "react-scripts": (
        npm("vite", "Create React App 已被 React 官方文档移除推荐；Vite 是主流后继构建工具。",
            "环境变量前缀、public 路径、jest 配置与 SVG 导入方式需迁移。"),
    ),
    "@vue/cli-service": (
        npm("vite", "Vue 官方文档已将 Vite 作为推荐构建工具，vue-cli 进入维护模式。",
            "webpack 专有 loader/插件链需重建。"),
    ),
    "vuex": (
        npm("pinia", "Pinia 是 Vue 官方推荐的状态管理方案。",
            "模块命名空间、mutation 概念被移除，store 需重写。"),
    ),
    "lodash": (
        npm("es-toolkit", "API 高度对齐且体积显著更小的现代实现。",
            "少数边缘行为与 lodash 不一致，需按调用点核对。"),
        native("ES2015+ 内置方法与可选链",
               "多数 lodash 用法已可由语言内置能力覆盖。",
               "深拷贝、防抖节流等仍需自行实现或保留小工具。"),
    ),
    "jquery": (
        native("querySelector / classList / fetch / CustomEvent",
               "现代浏览器已内置 jQuery 的主要能力。",
               "插件生态、动画与 AJAX 封装需逐项替换。"),
    ),
    "classnames": (
        npm("clsx", "API 兼容且体积更小，可近似直接替换。",
            "对象与数组混合的边缘用法仍需回归。"),
    ),
    "uuid": (
        native("crypto.randomUUID()",
               "Node 19+ 与现代浏览器（安全上下文）已内置 UUID v4 生成。",
               "仅覆盖 v4；v1/v3/v5 与非安全上下文仍需依赖。"),
    ),
    "query-string": (
        native("URLSearchParams",
               "平台内置查询串解析与序列化。",
               "嵌套对象、数组格式与自定义分隔符需自行处理。"),
    ),
    "rimraf": (
        native("fs.rm(path, { recursive: true, force: true })",
               "Node 14.14+ 已内置递归删除。",
               "glob 模式匹配需自行实现。"),
    ),
    "mkdirp": (
        native("fs.mkdir(path, { recursive: true })",
               "Node 10+ 已内置递归创建目录。",
               "返回值语义与 mkdirp 略有不同。"),
    ),
    "dotenv": (
        native("node --env-file=.env",
               "Node 20.6+ 已内置 .env 加载。",
               "变量展开、多文件与 encoding 选项覆盖不完整；构建期注入仍可能需要依赖。"),
    ),
    "nodemon": (
        native("node --watch",
               "Node 18.11+ 已内置文件监听重启。",
               "忽略规则、延迟与自定义执行命令的配置能力更弱。"),
    ),
    "babel-polyfill": (
        npm("core-js", "babel-polyfill 已弃用，官方指向直接使用 core-js。",
            "需要配合 browserslist 与 useBuiltIns 配置按需注入。"),
    ),
    "istanbul": (
        npm("nyc", "istanbul CLI 已由 nyc 取代。",
            "配置文件格式与报告器参数不同。"),
        npm("c8", "基于 V8 原生覆盖率，无需插桩。",
            "对经过转译的源码需正确的 source map。"),
    ),
    "bower": (
        npm("pnpm", "Bower 已官方弃用并建议改用 npm 生态包管理器。",
            "组件解析与扁平化策略完全不同，需重建依赖声明。"),
    ),
}

# Every disposition a human can pick for an open-target package. Machine ids are stable;
# the generator renders them for every open target so no route is silently dropped.
# Every route here produces a change: a package that reached this report was already
# identified as needing to go, so "keep it as is", "time-boxed exemption" and
# "same-package upgrade" are deliberately absent — bumping the version inside the same
# package does not resolve whatever put the package on the list.
DISPOSITION_OPTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "remove-dependency", "删除依赖",
        "manifest 已声明，且已建立无业务、运行时、动态、构建期、工具链、peer 与间接使用。",
        "见「删除评估」：覆盖七个维度的证据、移除后验证方案与回滚路径。",
    ),
    (
        "replace-with-alternative", "替换为其他依赖包",
        "本仓库直接使用该包，且存在能力可对齐的替代库。",
        "见「替代库候选」表：能力对齐、迁移范围、维护与 license 证据。",
    ),
    (
        "handle-parent-package", "处置父包或 overrides 钉版本",
        "该包由其他包引入：manifest 未声明，或声明之外还有父包。",
        "见「依赖来源与父包链」：父包链、各父包 range、最低可行 overrides 版本与会被破坏的约束。",
    ),
    (
        "native-platform-capability", "改用运行时/语言原生能力",
        "目标能力已被 Node 或浏览器内置，可直接改用，无需自建实现。",
        "确认最低支持的 Node/浏览器版本覆盖该 API，并补齐依赖曾提供的边缘能力。",
    ),
    (
        "in-house-reimplementation", "自建最小实现并重构调用点",
        "既无合规替代包、也无平台内置能力时的兜底路径。",
        "见「原生重构方向」：需自建的能力清单、按调用点分组的改造范围与分阶段验证。",
    ),
    (
        "isolate-behind-wrapper", "隔离到内部包装层",
        "短期无法完成更换，但需要先收敛调用面为后续替换让路。",
        "识别现有调用点、设计包装层边界，并约定后续替换的触发条件与期限。",
    ),
    (
        "internal-fork", "内部 fork 维护",
        "上游停止维护但功能不可替代，且组织有能力承接维护。",
        "明确维护责任人、安全补丁流程、同步上游策略与退出条件。",
    ),
    (
        "remove-feature", "移除相关功能",
        "该依赖支撑的功能本身已可下线。",
        "确认业务方同意、影响面、数据/路由清理范围与回滚方式。",
    ),
)

# Reproducible ordering for replacement candidates, highest priority first. Only
# machine-checkable signals participate so two runs on the same inputs rank identically.
ALTERNATIVE_RANK_SIGNALS: tuple[str, ...] = (
    "human-reviewed",
    "project-constraint-fit",
    "not-deprecated",
    "recent-release",
    "declared-license",
)

# Screening criteria the Agent must actually verify before a researched candidate may be
# written back through `--analysis-evidence-file`.
RESEARCH_CRITERIA: tuple[str, ...] = (
    "能力对齐：逐条覆盖本包在本仓库的实际用法，不以整体定位近似代替",
    "框架/peer/engine/浏览器/SSR 兼容性与项目约束一致",
    "license 允许本项目使用，且无未处置安全公告",
    "维护活跃度：最近发布时间、未标弃用、issue/PR 响应",
    "bundle 与运行时开销变化",
    "迁移范围、验证范围、回滚难度与长期锁定风险",
    "官方文档、仓库与包元数据 URL 可直达",
)

# Generic staged path used when a package must be replaced by first-party code.
REFACTOR_STAGES: tuple[str, ...] = (
    "冻结新增用法：约定不再新增该依赖的调用点",
    "建立最小适配层：以本仓库需要的能力为边界，先用依赖实现，收敛调用面",
    "按调用点分组迁移：逐组把适配层内部实现换成自建代码或原生能力",
    "移除依赖声明并同步 lock，确认无残留 import/配置/类型引用",
    "按验证范围回归，并保留可回滚的 manifest+lock 组合",
)


def curated_replacements(package: str) -> tuple[ReplacementHint, ...]:
    return REPLACEMENT_FAMILIES.get(package, ())


def curated_replacement_packages(package: str) -> tuple[ReplacementHint, ...]:
    return tuple(hint for hint in curated_replacements(package) if hint.package)


def curated_native_routes(package: str) -> tuple[ReplacementHint, ...]:
    return tuple(hint for hint in curated_replacements(package) if hint.native_api)
