# skill-teardown · 庖丁解 Skill

一句话定位：把一个 Agent Skill 拆解成一张可学习、可复用、可溯源的分析卡——拆的不是「好不好」，而是「它凭什么有效、哪些判断值得学走」。

> 想先直观了解它长什么样？看[可视化说明页](visual-guide.html)，或直接读[示例分析卡](examples/brainstorming-superpowers.md)（用本 Skill 拆解社区知名 Skill brainstorming 的完整九段产出）。

## 解决什么问题

你装过、收藏过不少社区 Skill，但大多数只停留在「能跑」：为什么它这样设计？哪些机制值得搬到自己的 Skill 里？它没明说的隐含判断是什么？什么时候会坑你？

摘要工具回答不了这些（复述功能清单没有知识增量），评分工具回答的是另一件事（好不好）。skill-teardown 用一套经过 42 个真实 Skill、15 个场景域、7 轮评审收敛验证的九段框架做深度拆解；当前版本又在一个 30+ Skill 的批量拆解中连续实战使用。产出一张「道法术例戒」分析卡。

## 核心能力

- **九段分析卡**：元信息 / 总体 / 道（顶层判断）/ 法（流程骨架 Mermaid 图）/ 术（可拿走复用的资产）/ 例（正反例证）/ 戒（边界与风险）/ 洞察（与原文严格区分的分析者判断）/ 版本记录
- **三档深度**：快扫（值不值得深究，约 1/3 篇幅）/ 标准（九段全产出）/ 深度（含同类对照）
- **溯源纪律**：原文观点必须可回链材料，推断必须标注（[原文明示] / [约束推导] / [分析补充]），材料不足写明不硬编
- **反偷懒内置**：道段禁空话（「注重质量」类判失败）、戒段无问题下限（三类各至少 2 条具体发现或说明为何无）
- **协议型零脚本**：纯提示词 Skill，无任何运行依赖，任何 Agent 都能跑

## 快速上手

1. 安装（任选一种 shell）：

```bash
# bash
git clone https://github.com/xujunxian1218-debug/Junxian-skills.git
cp -r Junxian-skills/skills/skill-teardown ~/.agents/skills/
```

```powershell
# PowerShell
git clone https://github.com/xujunxian1218-debug/Junxian-skills.git
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
Copy-Item -Recurse Junxian-skills\skills\skill-teardown "$HOME\.agents\skills\"
```

2. 对你的 Agent 说：

```
帮我拆解 ~/skills/xxx 这个 skill，出一张分析卡
```

3. 分析卡默认产出到 `./analysis-cards/{skill名}.md`，一卡一 Skill，不覆盖旧卡。

## 安装位置（按你的 Agent runtime）

| runtime | Skill 目录 |
|---|---|
| 通用 / ZCode 等 | `~/.agents/skills/skill-teardown/` |
| Claude Code | `~/.claude/skills/skill-teardown/` |

也可以不安装，把 SKILL.md 与 references/ 作为参考资料直接读进 Agent 上下文使用。

## 输入要求

- 最低要求：被分析 Skill 的 SKILL.md 全文
- 建议提供：references/、scripts/、prompts/、CHANGELOG 等配套文件——配套越全，「术」（可复用资产）和「戒」（依赖与风险）两段越有料

## Known Limitations

- 全部质量门为 AI 自评（材料溯源抽查、空话扫描、无问题下限都是提示词纪律而非机器脚本）——分析质量依赖模型的判断力与遵循度，框架提供的是纪律而非保证
- 不做质量评分、不产出改进建议清单、不修改被分析对象（这是刻意的边界，不是能力缺失）
- 分析卡是时点快照：Skill 上游演进后按卡内「版本记录」段的重析触发条件判断是否需要重拆

## 许可

本 Skill 以 GPL-3.0-or-later 发布（目录内 [LICENSE](LICENSE) / [NOTICE](NOTICE)）；使用、复制、修改或分发时保留版权与许可声明，分发修改版须按同一许可证开源。来源类型：原创。示例分析卡中的被拆对象引文见 NOTICE 中的来源与许可标注。

## 联系方式

扫码加作者微信，交流与反馈：

<p align="center"><img src="../../assets/wechat-qr.png" alt="作者微信二维码" width="200"></p>
