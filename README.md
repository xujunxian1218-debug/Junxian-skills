# Junxian Skills

本开源项目为 Junxian 精心打磨的 Agent Skill 合集，每个 Skill 经过实际项目验证，拿来即用。

## Skills

### [Knowledge Vault](skills/knowledge-vault/)

基于 Coding Agent 的个人知识管理系统。把文件（PDF、Word、PPT、音视频等）丢进去，自动生成结构化知识库——摘要、概念卡、主题页，全部通过 Obsidian 双链互相关联。

**核心能力**：
- 支持 15+ 种文件格式自动转换为 Markdown（PDF、DOCX、PPTX、XLSX、HTML、EPUB、MP4、MP3...）
- 两步消化流程：先分析内容与已有知识的关联，再生成摘要、概念卡、主题页
- 6 种知识消费场景：问答、主题探索、跨域分析、学习路径、缺口检测、内容生成
- 9 项健康巡检：覆盖率、一致性、链接有效性、孤儿检测...（`audit.py` 脚本化自动检查，self-check D7 调用 `--check-cross-refs`）
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

### [skill-teardown · 庖丁解 Skill](skills/skill-teardown/)

把一个 Agent Skill 拆解成一张可学习、可复用、可溯源的九段分析卡——拆的不是「好不好」，而是「它凭什么有效、哪些判断值得学走」。

**核心能力**：
- 九段分析卡：元信息 / 总体 / 道（顶层判断）/ 法（流程骨架 Mermaid 图）/ 术（可拿走复用的资产）/ 例（正反例证）/ 戒（边界与风险）/ 洞察 / 版本记录
- 三档深度：快扫（值不值得深究，约 1/3 篇幅）/ 标准（九段全产出）/ 深度（含同类对照）
- 溯源纪律：原文观点必须可回链材料，推断三态标注（[原文明示] / [约束推导] / [分析补充]），材料不足写明不硬编
- 反偷懒内置：道段禁空话（「注重质量」类判失败）、戒段无问题下限（三类各至少 2 条具体发现）
- 协议型零脚本：纯提示词 Skill，无任何运行依赖，任何 Agent 都能跑

**快速上手**（3 分钟）：

```bash
# 1. 复制到你的 Agent Skill 目录
cp -r skills/skill-teardown ~/.agents/skills/

# 2. 对你的 Agent 说：
#    帮我拆解 ~/skills/xxx 这个 skill，出一张分析卡
```
```powershell
# PowerShell
Copy-Item -Recurse skills\skill-teardown "$env:USERPROFILE\.agents\skills\"
```

分析卡产出到 `./analysis-cards/{skill名}.md`。示例产出见[示例分析卡](skills/skill-teardown/examples/brainstorming-superpowers.md)（拆解 obra/superpowers 的 brainstorming，MIT）与[可视化说明页](skills/skill-teardown/visual-guide.html)。

详见 [skill-teardown README](skills/skill-teardown/README.md)。

---

## 如何使用这些 Skills

### 安装方法

将 Skill 文件夹复制到你的 Coding Agent 的 skills 目录。不同 Agent 的目录约定不同，按你使用的 runtime 选择：

```bash
# Claude Code — 项目级（只对当前项目生效）
cp -r skills/<skill-name>  <你的项目>/.claude/skills/
# Claude Code — 全局（对所有项目生效）
cp -r skills/<skill-name>  ~/.claude/skills/

# Codex / 其他使用 AGENTS.md 约定的 Agent — 项目级
cp -r skills/<skill-name>  <你的项目>/.agents/skills/
```
```powershell
# PowerShell — Claude Code 项目级
Copy-Item -Recurse skills/<skill-name> <你的项目>\.claude\skills\
# PowerShell — Claude Code 全局
Copy-Item -Recurse skills/<skill-name> "$env:USERPROFILE\.claude\skills\"
# PowerShell — .agents 约定项目级
Copy-Item -Recurse skills/<skill-name> <你的项目>\.agents\skills\
```

### 兼容性

这些 Skill 主要为 Claude Code 开发和测试，但原理上兼容所有支持 SKILL.md 规范的 Coding Agent（Cursor、Windsurf、OpenCode、OpenClaw 等）。

## 贡献

欢迎提交 Issue 和 Pull Request。

## License

MIT License — 自由使用、修改、分发。部分 Skill 目录自带更严格的目录级许可证（见该目录内 `LICENSE` / `NOTICE`，如 skill-teardown 为 GPL-3.0-or-later），以目录级声明为准。

## 联系方式

扫码加作者微信，交流与反馈：

<p align="center"><img src="assets/wechat-qr.png" alt="作者微信二维码" width="200"></p>
