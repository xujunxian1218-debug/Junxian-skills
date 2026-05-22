# Junxian Skills

本开源项目为 Junxian 精心打磨的 Agent Skill 合集，每个 Skill 经过实际项目验证，拿来即用。

## Skills

### [Knowledge Vault](skills/knowledge-vault/)

基于 Coding Agent 的个人知识管理系统。把文件（PDF、Word、PPT、音视频等）丢进去，自动生成结构化知识库——摘要、概念卡、主题页，全部通过 Obsidian 双链互相关联。

**核心能力**：
- 支持 15+ 种文件格式自动转换为 Markdown（PDF、DOCX、PPTX、XLSX、HTML、EPUB、MP4、MP3...）
- 两步消化流程：先分析内容与已有知识的关联，再生成摘要、概念卡、主题页
- 6 种知识消费场景：问答、主题探索、跨域分析、学习路径、缺口检测、内容生成
- 9 项健康巡检：覆盖率、一致性、链接有效性、孤儿检测...
- 与 Obsidian 深度集成（双链、Dataview 面板、模板）

**快速上手**（3 分钟）：

```bash
# 1. 复制到你的项目
cp -r skills/knowledge-vault  <你的项目>/.claude/skills/

# 2. 安装依赖
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```
```powershell
# PowerShell
Copy-Item -Recurse skills/knowledge-vault <你的项目>\.claude\skills\
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```

然后告诉你的 Agent：

> 1. `初始化知识库` → 创建目录和模板
> 2. `把这些文件摄取到知识库` → 转换为 Markdown
> 3. `消化知识库的新内容` → 生成摘要、概念卡、主题页
> 4. 之后直接提问即可消费知识

详见 [Knowledge Vault README](skills/knowledge-vault/README.md)。

---

## 如何使用这些 Skills

### 安装方法

将 Skill 文件夹复制到你的 Coding Agent 的 skills 目录：

```bash
# 项目级（只对当前项目生效）
cp -r skills/<skill-name>  <你的项目>/.claude/skills/

# 全局（对所有项目生效）
cp -r skills/<skill-name>  ~/.claude/skills/
```
```powershell
# PowerShell — 项目级
Copy-Item -Recurse skills/<skill-name> <你的项目>\.claude\skills\
# PowerShell — 全局
Copy-Item -Recurse skills/<skill-name> "$env:USERPROFILE\.claude\skills\"
```

### 兼容性

这些 Skill 主要为 Claude Code 开发和测试，但原理上兼容所有支持 SKILL.md 规范的 Coding Agent（Cursor、Windsurf、OpenCode、OpenClaw 等）。

## 贡献

欢迎提交 Issue 和 Pull Request。

## License

MIT License — 自由使用、修改、分发。
