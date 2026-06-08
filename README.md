# skills

个人 Cursor / Codex Agent Skills 集合。每个子目录是一个可独立安装的技能包。

## 技能列表

| 技能 | 版本 | 说明 |
|------|------|------|
| [content-structuring](./content-structuring/) | v5.22 | 将视频字幕、播客、长文等素材整理为可替代原内容的中文 Markdown 深度文章 |

## 安装方式

### Cursor（项目级）

```bash
# 在目标项目根目录
git clone https://github.com/zyjhandsome/skills.git .tmp-skills
cp -r .tmp-skills/content-structuring .cursor/skills/
cp .tmp-skills/content-structuring/rules/cursor-content-structuring.mdc .cursor/rules/content-structuring.mdc
rm -rf .tmp-skills
```

Windows PowerShell 示例：

```powershell
git clone https://github.com/zyjhandsome/skills.git .tmp-skills
Copy-Item -Recurse .tmp-skills\content-structuring .cursor\skills\content-structuring
Copy-Item .tmp-skills\content-structuring\rules\cursor-content-structuring.mdc .cursor\rules\content-structuring.mdc
Remove-Item -Recurse -Force .tmp-skills
```

### Codex（项目级）

```bash
cp -r content-structuring/.codex/skills/content-structuring .codex/skills/
cp content-structuring/rules/codex-content-structuring.mdc .codex/rules/content-structuring.mdc
```

（路径以本仓库 `content-structuring/` 下实际文件为准。）

### 个人全局（Cursor）

将 `content-structuring/` 复制到 `~/.cursor/skills/content-structuring/`，即可在所有项目中通过 `@content-structuring` 或手动附加调用。

## 维护

- **单一事实来源**：`content-structuring/references/spec.md`
- **版本同步**：`SKILL.md` frontmatter 的 `version` 与四处镜像（spec、SKILL、Cursor rule、Codex rule）须一致
- **主开发仓库**：本仓库为技能的 canonical 发布源；下游项目（如 [ai-lecture-series](https://github.com/zyjhandsome/ai-lecture-series)）可按需同步副本

## 许可

各技能内容版权归作者所有；使用时请保留 `SKILL.md` 中的版本与维护说明。
