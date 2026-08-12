# knowledge-vault Changelog

## [v1.13.0] - 2026-08-12

### Added
- **链接校验系统性加固**：wikilink 写入硬约束（写入前 Glob 核实 target 真实存在 + 双层字符规范：FS 非法字符 + `%`/`#` URL/wikilink 保留符），一次根因修复覆盖 slug 非法字符、正文引号盲区、trailing `.md` 掩盖断链、路径基准歧义 4 类链接问题
- **远程图片本地化**：ingest 阶段自动下载远程图片到 `raw/images/`（读 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量，md5(url) 幂等去重，失败降级保留原远程链接 + 警告，<100 字节判占位图）
- **图片路径裸文件名补全**：`fix_image_paths` 支持双链 / markdown / 裸文件名三种格式自动补全（如 `_page_X_Figure_Y.jpeg` → `![[raw/images/...]]`），CLI `--bare` 可独立运行
- **消化规则广告跳过显式化**：正文推广块（开班 / 咨询 / 扫码关注 / 阅读原文 / 报名 等模式）+ Type E 图片广告不纳入摘要
- **audit `extract_wikilinks` 跳代码块**：避免代码块内 wikilink 误报（与 `detect_duplicate_sections` 语义统一）
- Digest plan / wikilink 写入 / Delete 关键检查点加 🔴 🛑 视觉标记，降低被忽略风险

### Changed
- `cross_refs` 扫描范围从仅概念卡扩展到所有 `knowledge/` 页面（concepts + topics + summaries），消除摘要/主题正文 wikilink 校验盲区
- trailing `.md` wikilink 同时报格式错 + 断链（不再 `continue` 掩盖断链）
- `lintlib.WIKILINK_UNSAFE_CHARS` 双层化（FS 非法 `\:*?"<>|` + `%#` URL/wikilink 保留符）
- SKILL.md frontmatter 非运行时元数据迁移至 CHANGELOG（降低 Runtime 触发 token）
- self-check 从 10 项合并为 6 项（去冗余）

### Fixed
- `fix_image_paths` CLI `--bare` 无法独立运行的 bug（`main` 无前缀时 `sys.exit` 与 `run_fix` 行为不一致）

### Notes
- 广告策略：ingest 全下载 + Digest 过滤（图床 URL 无广告特征，ingest 强分类误杀知识图）
- 识图能力保持 v1.11.0（`purpose.md` 不开启，待图资产治理后评估）
- 远程图下载不硬编码代理，只读环境变量

---

## [v1.12.2] - 2026-08-12

### Fixed
- `fix_image_paths.py --auto` 检测不到源前缀时的诊断改进：原一律报错退出，无法区分「无任何双链图」vs「前缀均已是目标」。新增 `count_wikilink_images()` 诊断函数分两种情况输出，`exit(1)→exit(0)`（前缀已是目标不是错误）
- `lintlib.CHAR_NORMALIZE_TABLE` 补 3 个全角字符（`。` 全角句号 / `·` 间隔号 / `－` 全角连字符）

### Changed
- README Compatibility 补 Windows `py` launcher 说明（未注册 `python` 命令时用 `py`）+ 脚本入口已内置 `sys.stdout.reconfigure(encoding='utf-8')`（控制台不乱码，无需设 PYTHONUTF8）
- test-prompts.json 从 3 条扩展到 6 条（补 Audit / Delete / 识图 三阶段）
- skill 内部 CLAUDE.md 目录结构刷新；docs/technical-overview.md 顶部标注历史快照（停 v1.8.0，以 CHANGELOG 为准）

### Notes
- 纯 patch：还债止血（同步对齐 + 文档刷新 + 兼容性小修），不引入新功能
- [F] 链接校验系统性加固（slug 即时硬校验 + wikilink 写入约束）+ 远程图本地化 R3 → v1.13.0

---

## [v1.12.1] - 2026-08-04

### Fixed
- `audit.check_related_summaries` 的 `Path(item).stem` 对含多个 `.` 的文件名（如 `GPT5.4`、`1.75`）截断，导致 frontmatter related_summaries 引用被误报断链 → 改为直接传 item（`build_file_index` 同时索引 `f.name` 和 `f.stem`，带不带 `.md` 都能匹配）

### Notes
- 纯 bugfix，仅 audit.py 一处改动，link_validity 及其他检查不受影响

---

## [v1.12.0] - 2026-08-04

### Added
- `scripts/build_manifest.py`：预生成 `.llm-wiki-cache/manifest.json`（concepts name+定义+反引数 + topics），Analysis 读 manifest 替代 index.md 全文（省 token）
- `lintlib.compute_inbound_counts`：从 audit.check_orphan 抽离（DRY，check_orphan + build_manifest 共用）
- `lintlib.detect_definition_overlap`：概念定义 bigram Jaccard 重叠检测（无需分词）
- `audit.check_related_summaries`：校验 topics frontmatter related_summaries 指向真实摘要（逐行解析 YAML 去引号）
- `audit.check_definition_overlap`：概念定义重叠候选对（阈值 0.5，供 Agent 复核）
- `references/digestion/` 三切片：dedup.md + generation.md + review.md（按阶段读省 token）
- SKILL.md 预检 1.5 生成 manifest；Analysis 改 manifest 优先（缺失回退 index.md）

### Changed
- `audit.check_coverage`：调 check_undigested 排除 DUPE/SKIP，消除 orphan 误报（实测 30→0）
- `audit.check_orphan`：改用 lintlib.compute_inbound_counts
- digestion-rules.md 改为索引（指向 3 切片）；SKILL.md 6 处按阶段指向切片
- tpl-topic.md related_summaries 加示例注释

### Notes
- 真实库实测：coverage 30 误报消除、related_summaries 发现 2 真实断链、definition_overlap 无重叠
- manifest token 收益当前 28%（110 概念），随库增长扩大

---

## [v1.11.0] - 2026-08-03

### Added
- digestion-rules 新增 **Step 3 条件性识图校验**：触发三条件（purpose enabled + 策略≠不识图 + 模型支持视觉），A 类 Mermaid 校验 / B 类表格校验 / D 类描述生成；任一不满足降级为 v1.10.0 文本推断
- SKILL.md 预检第4步升级：纯告知 → 告知 + **识图策略选择**（全部识图 A/B/D / 仅 A 类 / 不识图）
- SKILL.md Dependencies 补模型视觉依赖 + 不支持时降级说明
- README Compatibility 补 multimodal/runtime 差异（Claude Code 视觉支持；Cursor/Windsurf 部分配置降级）

### Changed
- tpl-purpose「识图设置」板块：去掉"仅统计不真识图"，改为真识图生效 + 策略 + 需视觉模型
- digestion-rules 免责声明：v1.11.0 起识图已执行则去除"（未启用识图校验）"限定词

### Notes
- 真识图 Step 3 端到端验证通过（A 类架构图→Mermaid 校验；D 类信息图卡片→描述生成）
- 纯规则层改动（无新脚本，count_images 复用 v1.10.0）
- 远程图片下载 R3 推迟到 v1.13.0

---

## [v1.10.0] - 2026-08-03

### Added
- `scripts/count_images.py`：图片引用统计（4步掩码去重管线：本地/远程/格式违规/缺失），供 Digest 预检消耗控制 gate。接口 `--vault` / `--json` / `--scope new|all` / `--files`
- `lintlib.strip_frontmatter`：从 audit `_body_only` 提取为公共函数（audit + count_images 共用）
- SKILL.md 预检第4步：`image_recognition:enabled` 时调 count_images 告知图片规模（消耗控制 gate）
- `templates/tpl-purpose.md` 新增 `image_recognition` 字段（disabled 默认 / enabled）
- digestion-rules 免责声明条件性化（"未启用识图校验"限定词）

### Changed
- audit.py 改用 lintlib.strip_frontmatter（行为不变，DRY）

---

## [v1.9.3] - 2026-07-24

### Fixed
- `build_file_index` 范围盲区：此前只索引 `knowledge/*.md`，不覆盖 `raw/`，导致 link_validity/cross_refs 把所有指向 raw/ 的链接（源 md + 图片）误报断链。改为扫全 vault 所有文件，key 含 `f.name` + `f.stem`
- `validate_wikilink_slug` .md 误判：此前任何含 .md 的 wikilink 都判格式错误，但概念名合法含 .md（如 `AGENTS.md-概念`）。改为只对纯 slug 末尾的 .md 报错（概念名中间 .md、路径 wikilink `raw/foo.md` 合法）

### Changed
- `build_file_index` 的 `subdir` 参数改为可选（默认 None = 全 vault）

---

## [v1.9.2] - 2026-07-24

### Added
- `lintlib.strip_fenced_code(text)`：剥离 ```/~~~ 围栏代码块内容，供 lint 函数共用

### Fixed
- `detect_duplicate_sections` 代码块盲区：正则 `^##\s+` 不区分代码块内外，概念卡在 ```markdown 代码块内展示的模板示例标题（如 AGENTS.md-概念.md 展示的 `## 开发命令`/`## 代码风格`，各 3 次全在代码块内）被误判为文档结构重复。detect 前先调 `strip_fenced_code` 剥离代码块

---

## [v1.9.1] - 2026-07-23

### Added
- `scripts/audit.py` 新增 `check_duplicate_sections` 检查（基于 lintlib.detect_duplicate_sections）：检测同一 .md 内重复的 `##` 板块，注册到全量 audit，亦可单独 `--check-duplicate-sections` 调用
- SKILL.md Digest self-check 新增第 10 项：重复板块检测（拦截消化合并时产生的同名板块重复）

### Changed
- README 工作原理图：四阶段 → 五阶段（补充 Delete 级联删除环节）
- README 巡检说明：7 项 → 9 项（补来源优化、孤儿检测）
- README 模板说明：5 个 → 7 个（补 purpose、overview）
- README 文件说明表补充 audit.py、lintlib.py、delete-rules.md
- SKILL.md frontmatter 脱敏：author → Junxian，移除 source/source_refs/created/updated

### Fixed
- SKILL.md Phase Router 静态版本号 1.8.0 → 1.9.1（此前与 frontmatter 脱节）
- 删除 audit.py 中的 `_stub` 占位死代码（所有检查项均已实现）

---

## [v1.9.0] - 2026-07-14

### Added
- `scripts/audit.py`：8 项确定性巡检检查脚本化（覆盖率/完整性/链接有效性/命名/索引准确性/链接格式/source优化/孤儿检测）+ cross-refs，输出 JSON + 人类可读报告，问题带 severity（minor 格式 / warning 断链）
- `scripts/lintlib.py`：6 个共用 lint 函数（文件名规范化 / wikilink 提取校验 / 文件索引 / 同名小节检测），check_undigested / audit / self-check 三处复用
- self-check D7 脚本化：SKILL.md 交叉引用有效性检查改为调 `audit.py --check-cross-refs`（Agent 侧 token ~64k→~1-2k）

### Changed
- `check_undigested.py`：未匹配 summary 的文件判 NEW（去掉"无日期→MANUAL"逻辑），日期从父目录 fallback；normalize 补全角标点
- SKILL.md 预检规则：MANUAL 类别需人工核验，不能凭 NEW=0 停止
- digestion-rules.md wikilink 规范：禁止 .md 后缀 / 路径敏感字符
- SKILL.md 正文阶段描述统一为五阶段（Ingest→Digest→Output→Audit→Delete）

### Fixed
- check_undigested 对含全角标点/无日期文件名误判 MANUAL
- audit 路径 wikilink 误报（`/` 是 Obsidian 合法路径分隔符）+ frontmatter source 字段 .md 误扫

---

## [v1.8.0] - 2026-05-26

### Added
- 级联删除流程（Phase 6: Delete）：删除 raw 文件时自动级联清理摘要、概念卡、主题页、断链
- `references/delete-rules.md`：级联删除完整规则（6 步流程 + 级联规则 + 边界条件）
- SKILL.md Phase Router 新增 Delete 行、Phase 6: Delete 章节、Prohibitions 更新
- `_dev/` 目录约定：每个 skill 的开发过程文件存放位置（不分发）

### Changed
- Prohibitions 更新删除规则：允许 Phase 6 删除（需用户确认），新增确认要求
- USE WHEN 和 Examples 新增删除相关触发词和示例

---

## [v1.7.0] - 2026-05-26

### Added
- Digest Review 输出：消化完成后输出矛盾、重复、缺失页面、UPDATED 文件、建议，保存到 `knowledge/digest-review-{date}.md`
- SHA256 增量哈希：check_undigested.py 新增 `UPDATED` 分类（5 类输出），检测"文件名相同但内容已更新"
- `references/digestion-rules.md` 新增 Review Output Format 章节
- init_vault.py 新增 `.llm-wiki-cache/` 目录创建

### Changed
- check_undigested.py 输出从 4 类扩展至 5 类（新增 UPDATED）
- Digest 流程新增"Digest Review"段落（self-check 之后执行）

---

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
