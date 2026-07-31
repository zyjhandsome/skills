# Java 依赖升级影响分析 — 小白使用导览

> 受众：第一次接触本 Skill 的同学。  
> 基准：`java-dependency-upgrade-impact-analysis/SKILL.md` + `references/*`。  
> 语言：正文简体中文；术语、枚举、GAV、路径、命令保持英文原文。

---

## 0. 动态一张图（先看图）

> 蓝 = Agent 自动做；黄 = 要你拍板；绿 = 本技能终点；红 = 技能外 / 停住 / 实施另授权。  
> 打开 SVG 后会有分阶段淡入与箭头流动动画（浏览器或支持 CSS 动画的预览器）。

![Java 依赖升级影响分析工作流](./assets/java-dependency-upgrade-workflow.svg)

源文件：[`docs/assets/java-dependency-upgrade-workflow.svg`](./assets/java-dependency-upgrade-workflow.svg)

**读图顺序（10 步）：**

0. **心智** — 它是参谋，不是施工队：只出决策包，不改 pom  
1. **开口** — 精确表（from→to）或整仓巡检（先候选、再选批）  
2. **体检** — JDK / 构建工具 / Python；exit 5 停、exit 6 问你选 Maven 还是 Gradle  
3. **落盘路径** — 路径没定清前可读不可写；不乱建目录  
4. **证据** — 有效版本 → 目标是否存在 → 是否在用  
5. **处置阶梯** — 直接：删→升→换；传递：排→升上层→钉→换上层；再谈 Owner  
6. **草稿** — 六层影响 + 十章报告；草稿 ≠ 做完  
7. **当场确认** — 每个 ready/pending 单元单独答；禁止「全部 proceed」  
8. **定稿三轴** — 证据齐了吗 / 人拍板了吗 / 能不能去实施  
9. **速记五句** — 背完就能跟 Agent 协作

---

## 1. 一句话心智模型

这个 Skill **只做证据驱动的决策包**，不做实施。

Agent 体检环境 → 锁定有效版本与目标可达性 → 按处置阶梯 + Owner 阶梯推荐路径 → **当场**按确认队列问你 → 写入决策并重生成 → `analysis_status=complete`（终点）。  
**只有** `batch_implementation_gate=ready` **且**另有实施授权时，才可以改依赖——那一步不在本 Skill 内。

| 轴 | 问题 | 典型取值 |
|---|---|---|
| `analysis_status` | 证据齐了吗？ | `partial` / `blocked` / `complete` |
| `decision_status` | 人拍板了吗？ | `needs_choice` / `not_needed` / `decided` |
| `batch_implementation_gate` | 整批能否去实施？ | `frozen` / `ready`（信息性；本 Skill 从不实施） |

---

## 2. 最短上手提示词

**精确表：**

```text
用 java-dependency-upgrade-impact-analysis 分析下面依赖（只出决策包，不改代码）。
项目：<仓库路径>

<粘贴升级表>
```

**整仓巡检：**

```text
用 java-dependency-upgrade-impact-analysis 对 <仓库路径> 做依赖升级巡检，
先给候选清单并问我选批，再对选定批出决策包（不改代码）。
```

与 delivery 联用时，见 [`java-dependency-upgrade-delivery-usage.md`](./java-dependency-upgrade-delivery-usage.md)（本 Skill 与 delivery-* 解耦，可单独使用）。

---

## 3. 你需要回答的常见问题

| 场景 | 你怎么答 |
|---|---|
| 队列 `ready` | 逐单元：`proceed:g:a:v` / `remove` / `exclude` / `replace:…` / `defer` / `other` |
| 队列 `pending`（可行·待补证） | 先恢复 Maven/同意分期 tree（`other`）或 `defer`；基线证实后再答 `proceed` |
| 队列 `blocked`（目标 404） | 重述一个可达的 GA 目标，或 `other` 放弃/改写；不要直接 `defer` |
| 双构建 exit 6 | 明确选 Maven 或 Gradle |
| 无 `openspec/changes` | 给 `--change-dir` 或 `--output-dir` |
| 开放目标 / CVE 无 `to` | Agent 会推荐 GA 并附 URL，仍须你逐单元选定 |

---

## 4. 相关路径

- Skill：`java-dependency-upgrade-impact-analysis/SKILL.md`  
- 动态导览图：`docs/assets/java-dependency-upgrade-workflow.svg`  
- Delivery 挂载说明：`docs/java-dependency-upgrade-delivery-usage.md`  
- 校验：`python java-dependency-upgrade-impact-analysis/scripts/validate_report.py <report.md>`  
