# skill-teardown Changelog

## [v0.2.1] - 2026-08-29

### Added
- 示例分析卡 `examples/brainstorming-superpowers.md`：用本 Skill 拆解 obra/superpowers 的 brainstorming（MIT），标准深度九段全产出；`examples/README.md` 记录选材溯源与引用幅度声明
- `LICENSE`（GPL-3.0 全文）与 `NOTICE`（来源类型：原创；含 visual-guide 范本与示例引文的 attribution）
- `visual-guide.html` 可视化说明页：单文件自包含，覆盖定位、五步流程、三边界、九段交互地图、质量红线

### Changed
- README 重写为宣传版：bash + PowerShell 双写法安装、多 runtime 安装路径（`.agents/skills/` 与 `.claude/skills/`）、Known Limitations 更新为批量实战口径、新增联系方式节
- 发布前通过 12 维设计审计（overall 8.0，无阻塞项）；SKILL.md 正文与 v0.2.0 一致，仅版本号变更

## [v0.2.0] - 2026-08-29

### Added
- 逐段产出时的段级硬上限中检：每段落笔前重申该段上限，超限拦在段内，不留给终检兜底
- 「运行时能力探测」角度的命中判别正反例：探测环境能力（命令 / 脚本可用性）才算命中，静态文档发现不算
- 「所属生态」条件字段拆分引用式（主动）/ 被编排（被动）两形态：被动命中记录编排方与调用契约，契约漂移计入一致性风险
- 「无 gate 空标」官方条款：被拆 Skill 未设任何质量 gate 时如实标注并说明影响，不自创分类格式
- 「历史卡对照」条件块：对照注记 ≤200 字统一计数口径、旧卡断链补齐核验、回审建议三档标准写法（条目级 / 章节级 / 整体级）

## [v0.1.0] - 2026-08-26

### Added
- 初版：五步流程（材料准入 / 定深度 / 通读三判别 / 逐段产出 / 终检）+ 三边界（不写摘要 / 不打分 / 不改造）+ 七条质量红线
- references 三件：`card-template.md`（九段填写规范）、`mermaid-guide.md`（流程形态 5 型判别 + 六要素）、`analysis-angles.md`（条件触发总表）
- 九段分析卡结构：元信息 / 总体 / 道 / 法 / 术 / 例 / 戒 / 洞察 / 版本记录
