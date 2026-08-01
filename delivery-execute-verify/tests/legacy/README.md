# Legacy prompt-contrast docs（非现行验收）

本目录存放历史规则级 prompt 对照记录（原 `delivery-family/1.1` 场景集及后续批注）。

**现行验收入口只有：**

```text
node delivery-frame-spec/tests/run_all.mjs
```

勿把本目录文件当作 `delivery-family/1.4` 的行为验收标准。尤其是涉及「能力降级 / `evidence_mode: degraded` / Superpowers 硬停机」的旧期望，已被 1.2–1.4 契约取代（见 `family-contract.md`）。
