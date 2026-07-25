# 依赖类别核查表

## 目录

1. UI 组件库
2. 请求客户端
3. 框架与路由
4. 状态管理
5. 构建工具
6. TypeScript、测试与样式
7. DOM/旧式运行时（jQuery 等）

只读取与目标包相关的类别，不要把整张清单机械写入报告。

## 1. UI 组件库

核查 props/events/slots、表单校验、Table 分页/排序/筛选、Modal/Drawer 生命周期、Upload 文件对象与回调、日期对象/时区、locale、主题 token、CSS reset、z-index 和视觉基线。

测试至少覆盖新增/编辑/校验、列表分页、弹层开关、上传成功/失败和关键页面视觉。`visible → open` 应归入 Modal/Drawer 等弹层组件，不要误写成 Form API。

## 2. 请求客户端

核查实例创建、请求/响应拦截器、headers/token、错误类型、取消请求、timeout、retry、params/body 序列化、FormData、Blob/stream、凭证与代理。

测试覆盖成功、业务错误、401、403、500、超时、取消、重复提交、上传和下载。

## 3. 框架与路由

框架：入口、渲染 API、生命周期、状态批处理、SSR/hydration、事件和第三方 peer。

路由：创建 API、守卫、redirect、params/query、嵌套、lazy load、深链、刷新、404 和 history。

## 4. 状态管理

核查 store 初始化、模块注册、selector/computed、subscription、异步 action、中间件、持久化、跨页同步、账号切换和退出清理。

## 5. 构建工具

核查 Node/包管理器 engine、插件 peer、模块格式、alias、env、CSS pipeline、静态资源、动态 import、tree shaking、chunk、sourcemap、dev/prod parity 和包体积。

## 6. TypeScript、测试与样式

- TypeScript/types：严格性、JSX、ambient types、module/target、生成类型和 CI。
- 测试：runner、environment、transform、mock/setup、coverage 与快照噪声。
- 样式：Sass/Less/PostCSS 语法、CSS Modules、前缀、Tailwind 扫描、主题、响应式和暗色模式。

## 7. DOM/旧式运行时（jQuery 等）

核查选择器与事件委托、Ajax/Deferred、DOM/data 状态、插件扩展点、全局 `$`/`jQuery`、多版本共存、浏览器兼容范围和 jQuery Migrate 警告。跨主版本不得只比较首尾版本；按官方 Upgrade Guide 逐段评估并使用对应 Migrate 版本，例如旧 1.x/2.x → 最新 3.x → 4.x。

测试覆盖事件触发/解绑、表单与序列化、Ajax 成功失败、第三方插件、全局加载顺序、旧浏览器边界和 Migrate 控制台警告。GitHub Release 只有博客 URL 时必须跟随正文；历史版本只有 tag 时，应从官方 changelog/博客索引补齐，不能把 tag 当成 release 正文。
