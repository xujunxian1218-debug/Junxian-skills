# knowledge-vault Changelog

## [v1.6.2] - 2026-05-22

### Changed
- SKILL.md Sync 段落：硬编码路径改为通用占位符，cp 命令补充 PowerShell 替代写法
- README.md：安装段落补充 PowerShell 替代写法，新增 Compatibility 段落（Requirements / Tested on / Known Limitations）
- CLAUDE.md：开发工作流补充 PowerShell 替代写法

---

## [v1.6.1] - 2026-05-18

### Fixed
- ingest.py sanitize_filename() 增加中文弯引号移除，修复 Windows Bash shell 路径解析错误
- SKILL.md frontmatter version 与 CHANGELOG 强制同步
- SKILL.md 新增 Sync 段落，支持 Agent 触发同步+版本校验

---

## [v1.6.0] - 2026-05-12

### Added
- 新增 `templates/tpl-purpose.md`（知识库定位模板）和 `templates/tpl-overview.md`（概览模板）
- init_vault.py 初始化时自动创建 purpose.md 和 overview.md
- Digest Step 1 读取 purpose.md 指导分析方向
- Digest Step 2 新增第 6 步自动更新 overview.md
- 新增三级检索深度策略（浅层/中层/深层），Agent 根据用户意图自动选择

### Changed
- 检索入口从 `index → topics → ...` 改为 `overview → index → topics → ...`

---

## [v1.5.1] - 2026-05-11

### Fixed
- digestion-rules.md：摘要板块标题增加"固定标识符"强调 + 短摘要金句占位规则
- digestion-rules.md：概念卡 wikilink 增加 slug 格式强制规则 + Source Path Verification 子章节
- SKILL.md Post-digestion self-check 从 7 项扩展至 9 项

---

## [v1.5.0] - 2026-05-10

### Added
- Digest 流程拆为 Step 1 Analysis（6 维度分析）+ Step 2 Generation
- 新增 Page Merge Strategy（概念卡/主题页智能合并规则）
- audit-rules.md 新增 Source Optimization 和 Orphan Detection 检查项
- Audit 从 7 项扩展至 9 项

---

## [v1.4.0] - 2026-05-09

### Added
- 新增 `scripts/check_undigested.py`（三层递进匹配：精确→日期交叉→模糊前缀）

### Changed
- ingest.py 增加 SKIP_KEYWORDS 过滤元数据文件
- Digest 预检改用脚本去重，取代 AI 手动比对
- SKILL.md self-check 新增第 7 条全量数字校验

---

## [v1.3.2] - 2026-05-03

### Changed
- SKILL.md Digest 流程新增转写文件语境纠错指令

---

## [v1.3.1] - 2026-05-03

### Added
- ingest.py 新增 ASR_CORRECTIONS 词典（15 条高置信度替换）+ correct_asr_text() 函数
- ingest.py transcribe_audio() 加 initial_prompt 领域关键词
- ingest.py 新增 `-转写-` 命名标记区分 ASR 产物和文档转换产物

---

## [v1.3.0] - 2026-05-03

### Added
- 集成 faster-whisper 离线 ASR + ffmpeg 视频音轨提取
- init_vault.py 新增环境检查（区分核心/可选依赖）

### Changed
- 音频路由从 MarkItDown（Azure）切换到 faster-whisper（离线）
- 视频格式支持（mp4/mkv/avi/mov/flv）

---

## [v1.2.2] - 2026-05-02

### Fixed
- ingest.py 音频转换失败引导
- SKILL.md Post-digestion self-check 新增交叉引用有效性检查

---

## [v1.2.1] - 2026-05-02

### Changed
- 正文末尾加回 USE WHEN / Output Format / Examples 独立章节

---

## [v1.2.0] - 2026-04-24

### Changed
- 重写 YAML frontmatter（USE WHEN / EXAMPLES 格式）
- 新增 Phase Router 路由表、Error Recovery 章节
- 新增消化前确认步骤和新概念/主题创建确认点

---

## [v1.1.0] - 2026-04-24

### Changed
- 规范化 SKILL.md 格式和结构
- 移除内嵌 Changelog，改为独立 CHANGELOG.md

---

## [v1.0.0] - 2026-04-16

### Added
- 四阶段知识管理循环：Ingest → Digest → Output → Audit
- 文档转换支持 PDF/DOCX/PPTX/XLSX/HTML/EPUB 等
- 结构化摘要、概念卡、主题页自动生成
- Obsidian 双链兼容
- 完整脚本支撑（init_vault.py, ingest.py, fix_image_paths.py）
