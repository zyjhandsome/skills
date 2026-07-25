# 七因素风险模型

## 目录

1. 评分因子
2. 等级
3. 覆盖规则
4. 验证深度

## 1. 评分因子

总分必须由以下七项相加，并在报告中逐项展示。

| 因子 | 0–1 分 | 2–3 分 | 4–5 分 |
|---|---|---|---|
| 版本变化 | same=0，patch=1 | minor/added/unknown=3 | major/removed/replacement=5 |
| 依赖类型 | 普通 dev/runtime=1 | types/style/test/state/DOM runtime=2–4 | framework/router/UI/request/build=5 |
| 使用范围 | 无直接命中=0；单文件=1 | 2–5 文件或局部模块=3 | 公共包装器、共享配置或 >5 文件=5 |
| 业务关键性 | 普通展示=1 | 管理后台主要流程=3 | 登录、权限、支付、订单、上传等核心路径=5 |
| lockfile 变化 | 无变化=0；单一预期版本=1 | 未知、少量间接变化或多版本=3 | baseline mismatch、大范围漂移=5 |
| 测试覆盖缺口 | 关键路径有充分自动化=0 | 部分覆盖或无法关联=2 | 无相关测试/核心失败路径未覆盖=3 |
| peer 兼容性 | 已确认兼容或无 peer=0 | 目标 workspace 精确版本未知/范围无法判定=2 | 已确认不满足目标 peerDependencies=5 |

自动评分是初值。无法由证据确定的因素不能记 0，应使用 unknown 对应分值并写明补证方法。

## 2. 等级

| 总分 | 等级 | 最低策略 |
|---:|---|---|
| 0–5 | Low | 构建、相关单测、冒烟 |
| 6–12 | Medium | 模块回归、核心路径、回滚准备 |
| 13+ | High | 全量相关回归、分阶段发布、监控、回滚演练或等价控制 |

## 3. 覆盖规则

以下任一情况不得低于 High，除非代码事实证明该面完全不受影响：

- auth、permission、payment、privacy、migration、public API/protocol；
- 核心订单或上传链路；
- baseline mismatch 或无法确定目标 workspace；
- 项目 Node 权威约束没有交集，或项目命令只能在未验证的 Node 下执行；
- 目标 peerDependencies 与 workspace 精确版本冲突；
- 框架/UI/路由/请求/构建的大版本且缺少关键上游证据；
- 多个高风险依赖同批升级并共享核心路径。

若人工覆盖自动等级，报告必须同时保留原始分数、覆盖后等级、批准人/依据（存在时）和不可接受的残余风险。

## 4. 验证深度

- UI：Form、Table、Modal/Drawer、Upload、日期、菜单、主题、视觉回归。
- Request：token/header、成功/失败、401/403/500、超时、取消、序列化、上传下载。
- Router：守卫、跳转、参数、嵌套、刷新、深链、404、前进后退。
- State：初始化、订阅、持久化、退出清理、异步 action、权限状态。
- Build：dev/prod parity、插件、env、资源路径、分包、sourcemap、兼容性。
- Type/style/test：typecheck、生成类型、CSS/主题、测试配置和 CI。

High 不等于机械要求“所有项目都灰度”。若环境没有灰度能力，必须记录等价控制，例如可快速切换的旧构建、限定用户组、短观察窗或即时回滚。
