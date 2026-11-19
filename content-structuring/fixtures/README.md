# content-structuring fixtures

迷你金样，用于结构/闸门与跨技能转换回归。**不是**生产级深度文。

| 文件 | 用途 |
|------|------|
| `dialogue-three-layer.md` | 对谈三层 + 时间角注 + 合法首现括注 + Skill 专名 + 完整自检证据 |
| `adversarial-interview.md` | 争辩型访谈 + 完整公共元数据外壳 + 核心冲突 + 原声先于解释 |
| `longform-generic.md` | 通用模板，三个读者向 H2（含篇末关键语录节及其前置结构 `---`） |
| `multisource-conflict.md` | 多源口径冲突 + 编者注原子块 |
| `visual-lecture-voice.md` | 单人 Keynote 声口模式 + 远程原图直连与图注 + L2 Mermaid 重构 + 尾声问答归位 + 元数据双副表 |
| `stock-english-mix.md` | 存量夹写负样本（应被 4c-1 扫出裸词并退出 1） |
| `judgment-rubber-stamp.md` | 声纹/覆盖抽样空 ✅ + 争辩型假共识负样本（应被判断行证据拦截并退出 1） |

```bash
python -B scripts/selfcheck.py fixtures/dialogue-three-layer.md
python -B scripts/selfcheck.py fixtures/visual-lecture-voice.md
python -B scripts/check_4c.py fixtures/stock-english-mix.md      # expect 4c-1 hits (exit 1)
python -B scripts/normalize_spacing.py fixtures/dialogue-three-layer.md --check
python -B -m unittest discover -s scripts/tests -p "test_*.py" -v
```

每个正样本 fixture 都必须通过 `selfcheck.py` 的全部机检行（含 4c、4d、4e、4f-3 与判断行证据）。两份负样本例外：`stock-english-mix.md` 应被 4c-1 扫出裸词；`judgment-rubber-stamp.md` 应被判断行证据拦截并退出 1。

下游技能 `md2wechat` 的 `scripts/tests/test_upstream_contract.py` 会直接读取本目录全部含 `## 文章元数据` 的样本做转换回归（噪音节剥离、图文/Mermaid 双模渲染、HTML lint、运营规范扫描、全链路校验）。改动 fixture 的 H2 结构或媒体语法后，须同步运行下游契约测试；`longform-generic.md` 与 `visual-lecture-voice.md` 需保持 ≥3 个读者向 H2。

4c 词库单源：`references/lexicon.txt`。
