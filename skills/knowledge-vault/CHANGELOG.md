# Knowledge Vault Changelog

## [v1.6.1] - 2026-05-18

### Fixed
- 修复 Windows 环境下文件名含中文弯引号（`""`）时 Bash/Read 工具路径解析失败的问题
- 修复 SKILL.md frontmatter `version` 字段与 CHANGELOG 版本长期不同步的问题

### Added
- SKILL.md frontmatter `version` 改为必填字段，每次发版强制与 CHANGELOG 同步更新
- Digest 预检新增第 5 步「文件名安全扫描」：检测 raw/ 文件名中的中文引号等特殊字符并自动重命名
- SKILL.md 新增 `## Sync` 段落：Agent 可通过触发词执行同步+版本校验
- SKILL.md Phase Router 前新增静态版本提示文本

---

## [v1.6.0] - 2026-05-12

### Added
- **Purpose 文件**：新增 `templates/tpl-purpose.md`，初始化时复制到 vault 根目录，定义知识库目标、关键问题和研究范围
- **Overview 全局概览**：新增 `knowledge/overview.md`，Digest 完成后自动更新，提供知识库全貌叙述
- **三级检索深度策略**：浅层（简单问答 ≈ 5 文件）/ 中层（主题探索 ≈ 10 文件）/ 深层（跨域分析 ≈ 20 文件），Agent 根据用户意图自动选择

### Changed
- 检索入口从 `index → topics → ...` 改为 `overview → index → topics → ...`
- Digest Step 1 Analysis 新增优先读取 purpose.md
- Digest Step 2 Generation 新增第 6 步更新 overview.md

---

## [v1.5.1] - 2026-05-11

### Fixed
- 修复摘要板块标题不精确问题（如"一句话总结"→"一句话摘要"），强制匹配模板标题
- 修复概念卡内 wikilink 使用裸概念名而非完整 slug 的问题
- 摘要 source 字段改用 Glob 实时验证，消除引号/特殊字符不匹配

### Changed
- Post-digestion self-check 从 7 项扩展至 9 项（新增板块标题精确性、概念卡 wikilink 格式）

---

## [v1.5.0] - 2026-05-10

### Added
- **两步消化流程**：Digest 拆为 Step 1 Analysis（分析内容与已有知识关联）+ Step 2 Generation（生成 wiki 文件），显著提升生成质量
- **Page Merge Strategy**：概念卡和主题页更新时智能合并，而非简单追加
- **孤儿检测**：巡检新增第 9 项，检测无入链的概念卡和主题页

### Changed
- Audit 巡检从 7 项扩展至 9 项（新增 Source Optimization + Orphan Detection）

---

## [v1.4.0] - 2026-05-09

### Added
- **去重脚本** `check_undigested.py`：三层递进匹配（精确→日期交叉→模糊），输出 NEW/DUPE/SKIP/MANUAL 四类报告
- **Source 优先级规则**：摘要优先指向可读性更好的预处理版本

### Changed
- `ingest.py` 自动排除 manifest/metadata 等元数据文件
- Digest 预检从 AI 手动比对改为脚本自动检测

---

## [v1.3.2] - 2026-05-03

### Changed
- ASR 转写文件在消化阶段由 Agent 基于上下文纠错（不修改 raw 原文），提升转写内容质量

---

## [v1.3.1] - 2026-05-03

### Added
- ASR 规则纠错词典（15 条高置信度同音错别字替换）
- ASR 转写输出文件名标记 `-转写-`，区分普通文档转换
- Whisper `initial_prompt` 注入科技领域关键词，提升专有名词识别

### Changed
- `ingest.py` 音频格式从 MarkItDown（需 Azure）迁移到 faster-whisper（离线、免费）

---

## [v1.3.0] - 2026-05-03

### Added
- **音视频转写**：集成 faster-whisper + ffmpeg，支持 WAV/MP3/M4A/MP4/MKV/AVI/MOV/FLV
- `init_vault.py --check-env` 环境依赖检查

### Changed
- 依赖分为核心（markitdown/marker）和可选（faster-whisper），按需安装

---

## [v1.2.0] - 2026-04-24

### Added
- Phase Router 路由表：用户意图自动匹配对应 Phase
- 消化前确认步骤：列出待消化文件清单，等待用户确认
- 新概念/新主题创建前需用户确认
- Error Recovery 章节：中断恢复、部分完成续跑、损坏文件重处理

### Changed
- 补齐 YAML frontmatter 全部字段
- description 按 USE WHEN / EXAMPLES 格式重写

---

## [v1.1.0] - 2026-04-24

### Added
- 独立章节 USE WHEN / Output Format / Examples

### Changed
- 重构 SKILL.md 格式符合规范
- 中文化关键描述提升触发准确率
- Changelog 从 SKILL.md 内嵌迁移至独立文件

---

## [v1.0.0] - 2026-04-16

### Added
- 四阶段知识管理循环：Ingest → Digest → Output → Audit
- 文档转换支持 PDF/DOCX/PPTX/XLSX/HTML/EPUB 等
- 结构化摘要、概念卡、主题页自动生成
- Obsidian 双链兼容
- 完整脚本支撑（init_vault.py, ingest.py, fix_image_paths.py）
- 参考文档（digestion-rules.md, output-rules.md, audit-rules.md）
