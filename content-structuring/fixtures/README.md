# content-structuring fixtures

迷你金样，用于结构/闸门回归。**不是**生产级深度文。

| 文件 | 用途 |
|------|------|
| `dialogue-three-layer.md` | 对谈三层 + 合法首现括注 + Skill 专名 |
| `adversarial-interview.md` | 争辩型访谈 + 核心冲突 + 原声先于解释 |
| `longform-generic.md` | 通用模板，三个读者向 H2（含篇末关键语录节及其前置结构 `---`） |
| `multisource-conflict.md` | 多源口径冲突 + 编者注 |
| `stock-english-mix.md` | 存量夹写（应被 4c-1 扫出裸词） |

```bash
python scripts/selfcheck.py fixtures/dialogue-three-layer.md
python scripts/check_4c.py fixtures/dialogue-three-layer.md   # expect 4c-1 OK
python scripts/check_4c.py fixtures/stock-english-mix.md      # expect 4c-1 hits
python scripts/normalize_spacing.py fixtures/dialogue-three-layer.md --check
python scripts/tests/test_gates.py
python scripts/tests/test_bracket_integrity.py
```

每个 fixture 都必须通过 `selfcheck.py` 的全部机检行（含 4e）；`stock-english-mix.md` 例外，它的用途就是被 4c-1 扫出裸词。

下游技能 `md2wechat` 的 `scripts/tests/test_upstream_contract.py` 会直接读取本目录做转换回归（噪音节不漏进正文、HTML lint、运营规范扫描、全链路校验）。改动 fixture 的 H2 结构后，也跑一下那边的测试；`longform-generic.md` 需保持 ≥3 个读者向 H2，否则下游 editorial 结构 lint 会报 `WEAK`。

4c 词库单源：`references/lexicon.txt`。4c-2 开集连扫内置于 `check_4c.py`。
