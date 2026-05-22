# Knowledge Vault

一个基于 Coding Agent 的个人知识管理 Skill。把你的文件（PDF、Word、PPT、网页等）丢进去，自动转换为结构化的知识库——摘要、概念卡、主题页，全部通过 Obsidian 双链互相关联。

**你不需要写代码。** 告诉你的 Agent 你要做什么，它来执行。

## 快速上手（3 分钟）

```bash
# 1. 复制 Skill 到你的项目
cp -r knowledge-vault  <你的项目路径>/.claude/skills/

# 2. 安装 Python 依赖（处理 PDF/DOCX 等格式需要）
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```
```powershell
# PowerShell 替代写法
Copy-Item -Recurse knowledge-vault <你的项目路径>\.claude\skills\
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```

然后在你的 Coding Agent 中，依次说：

> 1. `初始化知识库` → 创建目录和模板
> 2. `把这些文件摄取到知识库` → 转换为 Markdown
> 3. `消化知识库的新内容` → 生成摘要、概念卡、主题页
> 4. 之后直接提问即可消费知识

---

## 工作原理

四阶段循环：**摄取 → 消化 → 输出 → 巡检**

```
你的文件（PDF/DOCX/PPTX/...）
        ↓ 摄取
raw/ 目录下的 Markdown 文件
        ↓ 消化（Agent 自动执行）
摘要 + 概念卡 + 主题页 + 索引更新
        ↓
    ┌─── 输出（知识消费）───┐
    │                      │
问答  探索  分析  路径  缺口  生成
    │                      │
    └──────────────────────┘
        ↓ 巡检（定期健康检查）
覆盖率、完整性、一致性、链接、命名、索引
```

---

## 安装

### 前置条件

- 一个 Coding Agent（如 Claude Code、Cursor、Windsurf 等）已安装并可用
- Python 3.10+（用于文件转换脚本）

### 1. 安装 Skill

将整个 `knowledge-vault` 文件夹复制到你的 Coding Agent 的 skills 目录：

```bash
# 项目级安装（只对当前项目生效）
cp -r knowledge-vault  <你的项目>/.claude/skills/

# 全局安装（对所有项目生效）
cp -r knowledge-vault  ~/.claude/skills/
```
```powershell
# PowerShell 替代写法
# 项目级安装
Copy-Item -Recurse knowledge-vault <你的项目>\.claude\skills\
# 全局安装
Copy-Item -Recurse knowledge-vault "$env:USERPROFILE\.claude\skills\"
```

### 2. 安装 Python 依赖

```bash
pip install "markitdown[all]>=0.1.5" "marker-pdf>=1.10.0"
```

| 包 | 用途 | 是否必须 |
|---|------|---------|
| `markitdown` | Word、PPT、Excel、HTML 等 | 处理 Office/网页文件需要 |
| `marker-pdf` | PDF（保留结构、提取图片） | 处理 PDF 需要，首次下载 OCR 模型约 200MB |
| `faster-whisper` | 音视频转写 | 可选（仅处理音视频时需要） |

如果只处理 Markdown 文件，不需要安装这些依赖。

**音视频转写**（可选）：

```bash
pip install "faster-whisper>=1.0.0"
# 还需要安装 ffmpeg: https://ffmpeg.org/download.html
# Windows: choco install ffmpeg
```

### 3. 安装 Obsidian 插件（可选但推荐）

在 Obsidian 中安装以下插件获得最佳体验：
- **Dataview**：动态查询面板（dashboard.md 依赖此插件）
- **Templater**：模板变量支持

---

## 使用方法

### 第一步：初始化

> 初始化知识库到 `/path/to/my-vault`

Agent 会创建目录结构、复制模板、生成索引文件。

```
my-vault/
├── raw/                    ← 放你的原始文件（按日期组织）
│   └── images/             ← 自动提取的图片
├── knowledge/
│   ├── summaries/          ← 摘要（Agent 自动生成）
│   ├── concepts/           ← 概念卡（Agent 自动生成）
│   ├── topics/             ← 主题页（Agent 自动生成）
│   ├── index.md            ← 总索引
│   └── dashboard.md        ← Obsidian 面板
├── notes/                  ← 你的个人笔记（Agent 不会碰）
├── templates/              ← Obsidian 模板
└── outputs/                ← 高价值输出
```

### 第二步：摄取文件

> 把 `/path/to/downloads` 里的 PDF 和 DOCX 摄取到知识库，vault 路径是 `/path/to/my-vault`

#### 已验证格式

| 格式 | 说明 |
|------|------|
| `.pdf` | 保留结构、表格，自动提取图片 |
| `.docx` `.doc` `.pptx` `.ppt` `.xlsx` `.xls` | Office 文档 |
| `.html` `.htm` `.csv` `.json` `.xml` `.txt` `.md` | 文本格式 |
| `.epub` | 电子书 |

#### 实验性格式

| 格式 | 说明 | 备注 |
|------|------|------|
| `.zip` | 压缩包 | 解压后处理内部文件 |

#### 音视频格式（需 faster-whisper + ffmpeg）

| 格式 | 说明 | 备注 |
|------|------|------|
| `.wav` `.mp3` `.m4a` | 音频转写 | 需安装 faster-whisper |
| `.mp4` `.mkv` `.avi` `.mov` `.flv` | 视频转写 | 需安装 faster-whisper + ffmpeg |

转写产物会自动进行规则纠错（修正常见同音错别字），输出文件名带 `-转写-` 标记以区分普通文档转换。

如果文件已经是 Markdown，直接复制到 `raw/YYYY-MM-DD/` 即可。

### 第三步：消化知识

> 消化知识库的新内容，vault 路径是 `/path/to/my-vault`

Agent 会自动完成：

1. **去重检查**：跳过已有摘要的文件，只处理新文件
2. **生成摘要**：提炼为一句话摘要、核心要点、关键概念、金句
3. **抽取概念**：识别跨文章的通用概念，创建或更新概念卡
4. **更新主题页**：按主题整合多篇文章的观点
5. **更新总索引**：刷新统计数字、时间线、链接
6. **自动自检**：确保所有链接格式正确、统计数字一致、交叉引用有效

### 第四步：消费知识（6 种场景）

知识库不只是存东西，更重要的是**用起来**。

#### 知识问答（最常用）

直接提问，不需要指定路径：

> XX 概念是什么？
> A 和 B 有什么区别？

Agent 从知识库检索并回答，标注来源。知识库覆盖不到的部分会明确标注。

#### 主题探索

> 帮我梳理一下 XX 主题的完整脉络

综合该主题下所有内容，按逻辑组织成深度分析，保存到 `outputs/`。

#### 跨领域交叉分析

> A 领域和 B 领域有什么共通之处？

分别检索两个领域，寻找概念层面的映射和交叉点。

#### 学习路径规划

> 帮我规划学习 XX 的路径

按依赖排序（基础 → 进阶 → 综合），每步标注推荐内容，指出缺口。

#### 知识缺口检测

> 知识库在哪些方面还有空白？

分析各主题覆盖数量、概念关联密度，输出按优先级排序的缺口清单。

#### 内容生成

> 基于知识库写一篇关于 XX 的文章
> 把 XX 主题整理成一份大纲

检索相关内容，按目标格式组织，引用来源。输出到 `outputs/` 子目录：

```
outputs/
├── articles/    ← 长文
├── memos/       ← 研究备忘录
├── outlines/    ← 大纲
└── qa/          ← 高价值问答存档
```

### 健康巡检

> 巡检一下知识库，vault 路径是 `/path/to/my-vault`

检查 7 项指标（覆盖率、完整性、一致性、链接有效性、命名规范、索引准确性、链接格式），生成巡检报告。**巡检只出报告，不会自动修改你的文件。**

---

## 在 Obsidian 中使用

用 Obsidian 打开你的 vault 目录：

1. **打开 `knowledge/dashboard.md`**：切换阅读视图（Ctrl+E），查看动态面板
2. **浏览 `knowledge/index.md`**：通过双链跳转到摘要、概念卡、主题页
3. **在 `notes/` 下写个人笔记**：用 `[[双链]]` 关联到概念卡和主题页

---

## 常用指令速查

| 你想做什么 | 怎么告诉你的 Agent |
|-----------|----------------|
| 初始化 | `初始化知识库到 <路径>` |
| 摄取文件 | `把这些文件摄取到知识库：<文件路径>，vault 路径是 <路径>` |
| 消化 | `消化知识库的新内容，vault 路径是 <路径>` |
| 问答 | 直接提问 |
| 探索 | `帮我梳理 <主题> 的脉络` |
| 交叉分析 | `<领域A> 和 <领域B> 有什么共通之处？` |
| 学习路径 | `帮我规划学习 <领域> 的路径` |
| 缺口检测 | `知识库在哪些方面还有空白？` |
| 生成内容 | `基于知识库写一篇关于 <主题> 的文章` |
| 巡检 | `巡检一下知识库，vault 路径是 <路径>` |

---

## Compatibility

**Requirements:**
- Python 3.10+
- Coding Agent（Claude Code、Cursor、Windsurf 等）
- 可选：ffmpeg（音视频转写）

**Tested on:**
- Windows 11

**Not fully tested on:**
- macOS
- Linux

**Known Limitations:**
- 脚本中的 shebang 行（`#!/usr/bin/env python3`）在 Windows 上无效，需直接用 `python scripts/xxx.py` 调用
- 路径参数在 Windows 下支持 `/` 和 `\` 两种分隔符（脚本内部使用 `pathlib`）

---

## 注意事项

- `notes/` 是你的个人空间，Agent 不会修改
- `raw/` 的原始文件不会被删除或覆盖
- 巡检只出报告，不自动修改
- 修改概念卡核心定义前会跟你确认
- 每次消化只处理新文件，已消化的自动跳过

## 文件说明

| 文件 | 作用 |
|------|------|
| `SKILL.md` | Skill 核心指令 |
| `scripts/init_vault.py` | 初始化脚本 |
| `scripts/ingest.py` | 文件摄取脚本 |
| `scripts/check_undigested.py` | 未消化文件检测脚本（三层匹配：精确→日期交叉→模糊） |
| `scripts/fix_image_paths.py` | 图片路径修正脚本 |
| `templates/tpl-*.md` | 5 个模板文件（摘要、概念、主题、笔记、阅读笔记） |
| `references/digestion-rules.md` | 消化规则 |
| `references/output-rules.md` | 消费规则（6 种场景、检索策略） |
| `references/audit-rules.md` | 巡检规则 |

## 版本

当前版本：v1.6.2 — 详见 CHANGELOG.md

> README 随 Skill 版本同步更新。如果你的 Skill 版本与 README 描述不符，请以 SKILL.md 为准。
