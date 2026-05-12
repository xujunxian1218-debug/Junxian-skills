# Audit Rules

Periodically verify knowledge base health by running these 9 checks.

## Checklist

### 1. Coverage

For each raw file in `raw/` (excluding `raw/images/`), check if a matching
summary exists in `knowledge/summaries/`.

Report:
- Total raw files
- Matched summaries
- Orphaned raw files (no corresponding summary)
- Orphaned summaries (source points to non-existent file)

### 2. Completeness

For each summary, verify frontmatter has all required fields:
`source`, `title`, `date`, `author`, `tags`.

Verify body contains all required sections:
- 一句话摘要
- 核心要点
- 关键概念
- 原文金句

Report any missing fields or sections.

### 3. Consistency

Check concept definitions:
- No two concept cards should define the same concept with conflicting definitions
- Concepts referenced in summaries should match their definition in concept cards

Report any conflicts or contradictions found.

### 4. Link Validity

For each topic page:
- All `[[wikilinks]]` must point to files that actually exist
- `related_summaries` entries must correspond to real files in `summaries/`

For each concept card:
- "相关来源" links must point to real summary files
- "与其他概念的关系" links must point to real concept files

Report broken links with file name and missing target.

### 5. Naming Compliance

Verify filenames follow conventions:
- Summaries: `{title}-摘要-{YYYY-MM-DD}.md`
- Concepts: `{name}-概念.md`
- Topics: `{name}-主题.md`
- No unsafe characters: `\ / : * ? " < > | # % ^ & $ ! \` ' = ~`

Report any non-compliant filenames.

### 6. Index Accuracy

Open `knowledge/index.md` and verify:
- Stated counts match actual files in each directory
- Every concept in the index has a file in `concepts/`
- Every topic in the index has a file in `topics/`
- Every summary in the timeline has a file in `summaries/`
- No files exist in directories but are missing from the index

### 7. Link Format

Check all tables in `index.md`:
- Concept index: every row's "文件" column uses `[[xxx-概念]]` format
- Topic navigation: every row's "文件" column uses `[[xxx-主题]]` format
- Timeline: every row's "摘要文件" column uses `[[xxx-摘要-xxx]]` format

Plain text filenames, markdown links (`[text](path)`), or any other format
are all errors. Only Obsidian `[[wikilinks]]` are valid.

### 8. Source Optimization (optional)

For summaries whose `source` field points to a raw ASR transcript (filename
contains `-转写-` or is in a `raw_transcripts/` directory):

1. Check if a preprocessed version of the same content also exists in `raw/`
   (same date + same source identifier, different format)
2. If found, flag the summary as "source optimization suggested":
   - Current source: `[[raw/.../transcript.md]]`
   - Suggested source: `[[raw/.../preprocessed.md]]`

This is an informational check only — do not auto-fix. Mark as "Minor" severity
in the report.

### 9. Orphan Detection

Identify knowledge pages that have no inbound references from other pages —
they exist in isolation and are invisible to the knowledge network.

**Method:**

1. Build a reference map: for every `.md` file in `knowledge/`, extract all
   `[[wikilinks]]` and record which pages they point to
2. For each concept card in `knowledge/concepts/`:
   - Count how many other files contain a `[[概念名-概念]]` wikilink
   - Exclude self-references (the concept card linking to itself)
3. For each topic page in `knowledge/topics/`:
   - Count how many other files contain a `[[主题名-主题]]` wikilink
   - Exclude self-references

**Report:**
- Pages with **0 inbound links** (true orphans — no other page references them)
- Pages with **1 inbound link** (weakly connected — at risk of becoming orphans)
- For each orphan, suggest possible causes:
  - Recently created, not yet linked from summaries
  - Concept name doesn't match the wikilink syntax used in summaries
  - Genuinely disconnected topic

**Severity:**
- Multiple orphans → "Warning" (knowledge network has gaps)
- 1-2 orphans → "Minor" (normal for growing wikis)
- No orphans → not mentioned in report

---

## Output Format

Save the report to `knowledge/audit-report-YYYY-MM-DD.md`:

```markdown
---
date: YYYY-MM-DD
type: audit-report
status: Healthy | Warning | Critical
---

# 知识库巡检报告 YYYY-MM-DD

## 总体状态

(overall health: Healthy / Warning / Critical)

## 详细检查结果

### 1. 覆盖率
(coverage stats)

### 2. 完整性
(completeness issues)

### 3. 一致性
(consistency issues)

### 4. 链接有效性
(broken links)

### 5. 命名规范
(naming issues)

### 6. 索引准确性
(index accuracy)

### 7. 链接格式
(link format issues)

### 8. Source 优化建议
(source optimization suggestions, if any)

### 9. 孤儿页面
(orphaned pages with no inbound references)

## 问题汇总

### 严重问题 (Critical)
(list, or "无")

### 一般问题 (Warning)
(list, or "无")

### 轻微问题 (Minor)
(list, or "无")

## 建议
(recommended next steps)
```

**Important**: Audit produces a report only. Never automatically modify any files
to fix issues. The user decides what to act on.
