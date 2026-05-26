# Delete Rules — 级联删除

> 当用户要求从知识库中删除一个 raw 源文件时，需要级联清理所有依赖它的知识库产物。
> **Read this before executing any delete operation.**

---

## Core Principle

Agent 给出完整删除计划，用户确认后执行。所有操作为真删除（不进 _archive/，不设回收站）。

---

## Cascade Rules

| 操作对象 | 条件 | 动作 |
|---------|------|------|
| raw 文件 | 用户请求删除 | 删除 |
| summary | source 字段指向被删 raw | 删除 |
| 概念卡 | 被删 summary 是唯一来源 | 级联删除 |
| 概念卡 | 被删 summary 是多个来源之一 | 只移除该来源引用 |
| 主题页 | 删除后无剩余摘要 | 级联删除 |
| 主题页 | 删除后仍有剩余摘要 | 只移除该摘要引用 |
| index.md | 包含被删产物的条目 | 移除条目 + 更新统计 |
| overview.md | 覆盖范围受影响 | 追加删除说明（不重写） |
| 其他概念卡/主题页 | 引用了被级联删除的文件 | 修复断链 |

---

## Delete Flow

```
用户请求删除 raw 文件
        ↓
  Step 1: 定位影响范围（只读扫描）
        ↓
  Step 2: 生成删除计划，展示给用户
        ↓
  Step 3: 用户确认
        ↓
  Step 4: 执行删除（按依赖顺序）
        ↓
  Step 5: 修复断链 + 更新索引
        ↓
  Step 6: 输出删除报告
```

---

## Step 1: Locate Impact (read-only scan)

Given a raw file path, scan the knowledge base to find all affected files.

### 1.1 Find the corresponding summary

Scan all summaries' frontmatter `source` field in `knowledge/summaries/`.
Match: source field contains the raw file's filename (without path).

Output: matched summary path (0 or 1).

### 1.2 Find concept cards referencing that summary

Scan all concept cards in `knowledge/concepts/`.
Match: "相关来源" section contains a wikilink to the summary.

Output for each affected concept card:
- Total source count (determines if it will be cascade-deleted)
- Reference text to remove

### 1.3 Find topic pages referencing that summary

Scan all topic pages in `knowledge/topics/`.
Match: frontmatter `related_summaries` contains the summary filename,
or body contains a wikilink to the summary.

Output for each affected topic page:
- Total summary count after deletion (determines if it will be cascade-deleted)
- Reference text to remove

### 1.4 Check index.md entries

Scan `knowledge/index.md` for timeline entries referencing the summary.

Output: rows to remove from index.md.

---

## Step 2: Generate Delete Plan

Present the scan results as a structured plan to the user.

### Plan format

```markdown
## 删除计划

### 将删除的文件
- `raw/YYYY-MM-DD/xxx.md` ← 源文件
- `knowledge/summaries/xxx-摘要-YYYY-MM-DD.md` ← 对应摘要

### 将修改的概念卡
- `上下文工程-概念.md` — 移除来源引用（剩余 3 个来源，保留）
- `AI 编程-概念.md` — 移除来源引用后无剩余来源 → **将删除**

### 将修改的主题页
- `AI编程-主题.md` — 移除摘要引用（剩余 2 篇摘要，保留）
- `测试主题-主题.md` — 移除后无剩余摘要 → **将删除**

### 将修改的索引
- `knowledge/index.md` — 移除时间线条目 + 更新统计数字

### 将修复的断链
- `xxx-概念.md` 中引用了将被删除的 `AI 编程-概念.md` → 移除断链

### 影响统计
- 删除文件：2（raw + summary）
- 级联删除：1 概念卡 + 1 主题页
- 修改文件：1 概念卡 + 1 主题页 + index.md

确认执行？
```

### Key rules

1. **Show the complete plan** — user must see every affected file and operation type
2. **Mark cascade deletions** — clearly indicate which files are cascade-deleted due to empty sources
3. **Mark broken link fixes** — indicate broken links caused by cascade deletions
4. **Execute nothing** — all operations are "planned" at this stage, awaiting confirmation

---

## Step 3: User Confirmation

Wait for explicit user confirmation ("确认"/"y"/"执行") before proceeding.
If user replies "取消"/"n", abort — no operations executed.

### Confirmation granularity

Default: confirm the entire plan at once. No per-file confirmation.

User can override on confirmation:
- "删除 raw 和摘要，但保留概念卡" → skip concept card cascade
- "只删除 raw 和摘要" → skip all cascade operations

---

## Step 4: Execute Deletion

Execute in dependency order, ensuring each step succeeds before continuing.

### Execution order

```
1. Delete summary file
2. Modify multi-source concept cards (remove source reference)
3. Delete single-source concept cards
4. Modify non-empty topic pages (remove summary reference)
5. Delete empty topic pages
6. Delete raw file (last)
```

### Error handling

- If any step fails (file not found, permission error), stop and report completed operations
- Deleted files are NOT rolled back (true delete)
- Incomplete steps are marked in the report

---

## Step 5: Fix Broken Links + Update Index

### 5.1 Broken link repair

After cascade-deleting concept cards or topic pages, scan all remaining concept
cards and topic pages:
- Find wikilinks referencing deleted files
- Remove broken wikilinks
- If the "与其他概念的关系" section contains only broken links, clear it and
  add placeholder text

### 5.2 Update index.md

- Remove timeline entries for deleted summaries
- Remove concept index rows for deleted concept cards
- Remove/update topic navigation rows for deleted topic pages
- Update statistics (recount actual files)

### 5.3 Update overview.md

If deleted content affects the topic coverage described in overview.md, append:

```markdown
> {date} 删除了 {N} 篇内容，涉及 {主题列表}。
```

Do NOT rewrite overview entirely — deletion is a minor operation.

---

## Step 6: Delete Report

After execution, output a report.

### Report format

```markdown
## 删除报告 — {YYYY-MM-DD}

### 已删除
- `raw/YYYY-MM-DD/xxx.md`
- `knowledge/summaries/xxx-摘要-YYYY-MM-DD.md`
- `knowledge/concepts/AI编程-概念.md`（级联：来源清空）
- `knowledge/topics/测试主题-主题.md`（级联：摘要清空）

### 已修改
- `上下文工程-概念.md` — 移除了 1 条来源引用
- `AI编程-主题.md` — 移除了 1 条摘要引用
- `knowledge/index.md` — 更新统计和时间线

### 断链修复
- `yyy-概念.md` — 移除了对已删除 `AI编程-概念.md` 的引用

### 统计变化
| 指标 | 删除前 | 删除后 |
|------|--------|--------|
| Raw 文件 | N | N-1 |
| 摘要 | M | M-1 |
| 概念卡 | C | C-1 |
| 主题页 | T | T-1 |
```

---

## Edge Cases

| Scenario | Action |
|----------|--------|
| Raw file has no corresponding summary | Delete raw only, no cascade |
| Concept card has 2+ sources, one deleted | Remove source reference, keep card |
| Concept card has 1 source, deleted | Cascade-delete concept card |
| Topic page has 3+ summaries, one deleted | Remove summary reference, keep page |
| Topic page has 1 summary, deleted | Cascade-delete topic page |
| Concept card links to deleted concept | Remove broken wikilink |
| Deleted concept/topic referenced in index.md | Remove from index table |
| User requests deleting multiple raw files | Scan each, merge into one delete plan |
| Raw file path does not exist | Report error, do not execute |
| Summary exists but source field unmatchable | List as "待人工确认", do not auto-delete |
