# Digestion — Review Output

> v1.12.0 切片（从 digestion-rules.md 拆出）。Digest Review 阶段读取（self-check 后）。
> 其他切片：[dedup.md](dedup.md) / [generation.md](generation.md)

---

## Review Output Format

After all files in a Digest session have been processed (Step 2 Generation +
post-digestion self-check + overview update), output a **Digest Review** to
the user and write it to a file.

### When to output

The Review is the **final step** of every Digest session, after self-check.
It applies to all Digest sessions, regardless of how many files were processed.

### Review content

The Review covers these dimensions:

1. **Contradictions** — conflicts found between new and existing wiki content
   during Analysis. Report the specific claim and which pages disagree.
   Severity: `definite` | `possible` | `nuance`.

2. **Duplicates** — near-duplicate information detected across summaries or
   concept cards. Flag the overlapping content and suggest whether to merge.

3. **Missing pages** — concepts or topics mentioned in the source but not
   created because they were peripheral. List them for the user to decide
   if they want to add them later.

4. **UPDATED files** — if `check_undigested.py` reported any `UPDATED` files,
   list them here with a note that re-digesting will overwrite the existing
   summary. The user decides whether to re-digest.

5. **Suggestions** — any actionable improvements to the knowledge base
   structure (e.g., splitting a concept, merging topics, adding cross-references).

If none of the above apply, the Review states "本次消化未发现需要关注的问题。"

### Output format

**Dialog output** — show to user in the conversation immediately.

**File output** — write to `knowledge/digest-review-{YYYY-MM-DD}.md`:

```markdown
---
type: digest-review
date: YYYY-MM-DD
files_processed: N
---

# Digest Review — {YYYY-MM-DD}

## 处理概览

本次消化处理了 {N} 篇文件，生成/更新了 {M} 篇摘要、{C} 张概念卡、{T} 个主题页。

## 矛盾与冲突

> 逐条列出新发现与已有知识之间的矛盾。无矛盾时写"未发现矛盾"。

## 重复内容

> 列出跨摘要的近重复内容。无重复时写"未发现重复"。

## 待补充页面

> 列出源文件中提及但未创建的概念或主题。无遗漏时写"无需补充"。

## 内容变更文件

> 列出 UPDATED 文件。无变更时写"无"。

## 改进建议

> 对知识库结构的改进建议。无建议时写"无"。
```

### Design notes

- The Review file is a **historical record**, not an action queue. Users are
  not expected to resolve every item. Items that remain unresolved will be
  re-detected in the next Digest session's Analysis step.
- The file also serves as input for the next Digest Analysis — the Agent can
  read the most recent review to see what issues were flagged previously.
- Do NOT auto-execute any fixes suggested in the Review.
