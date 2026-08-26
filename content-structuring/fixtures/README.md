# content-structuring fixtures（v5.31）

迷你金样，用于结构/闸门回归。**不是**生产级深度文。

| 文件 | 用途 |
|------|------|
| `dialogue-three-layer.md` | 对谈三层 + 合法首现括注 + Skill 专名 |
| `adversarial-interview.md` | 争辩型访谈 + 核心冲突 + 原声先于解释 |
| `longform-generic.md` | 通用模板（无对谈实录） |
| `multisource-conflict.md` | 多源口径冲突 + 编者注 |
| `stock-english-mix.md` | 存量夹写（应被 4c 扫出裸词） |

```bash
python scripts/normalize_spacing.py fixtures/dialogue-three-layer.md --check
python scripts/normalize_spacing.py fixtures/adversarial-interview.md --check
python scripts/check_4c.py fixtures/dialogue-three-layer.md   # expect OK
python scripts/check_4c.py fixtures/stock-english-mix.md      # expect hits
python scripts/tests/test_gates.py
```
