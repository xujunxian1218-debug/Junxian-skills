# Output Rules

Rules for the Output phase — consuming knowledge from the vault.
**Read this file before handling any knowledge consumption request.**

---

## Retrieval Strategy

Core principle: **overview is the map, index is the directory.**

```
Step 0: Check purpose and overview
  → If purpose.md exists: understand scope boundaries
  → If knowledge/overview.md exists: get narrative overview of entire KB
  → This helps determine how deep to go and where to focus

Step 1: Read index.md
  → Locate relevant topics (topic navigation table)
  → Locate relevant concepts (concept index table)
  → Locate relevant summaries (timeline index)

Step 2: Read topic pages
  → Get topic overview and linked summary list
  → Understand the topic's internal logic

Step 3: Read concept cards
  → Get precise definitions and inter-concept relationships
  → Track "相关来源" for provenance

Step 4: Read summaries (as needed)
  → Get specific arguments, quotes, evidence
  → Trace back to raw files if necessary

Step 5: Synthesize
  → Cross-source comparison, synthesis, identify contradictions or gaps
```

Not every request needs all 5 steps. Use the Retrieval Depth Strategy below
to choose the right level.

---

## Retrieval Depth Strategy

Not every question needs the same depth of retrieval. Use the user's intent
to choose the appropriate level:

| Level | Trigger examples | Files to read | Approx. count |
|-------|-----------------|---------------|---------------|
| Shallow | "XX 是什么", "XX 的定义", factual lookup | overview + index + 1-2 concept cards | ~5 |
| Medium | "帮我梳理 XX", "XX 的完整脉络", topic exploration | + topic pages + related concepts + 2-3 summaries | ~10 |
| Deep | "XX 和 YY 的关系", "学习 XX 的路径", cross-domain | + multiple topics + summaries + raw files | ~20 |

**Decision rules:**
- If unsure, start at medium depth. After initial retrieval, decide whether to go deeper.
- Shallow answers that feel incomplete should be escalated to medium.
- Always cite sources and mark knowledge boundaries.

---

## Consumption Scenarios

### Scenario 1: Knowledge Q&A (Stable)

**Trigger**: User asks a direct knowledge question.

> "上下文工程是什么？"
> "Harness Engineering 和 SDD 有什么区别？"

**Workflow**:
1. Search index.md for relevant concept cards and topic pages
2. Read matched concept cards for definitions
3. Trace to related summaries for detailed explanations and evidence
4. Synthesize answer with source citations using `[[wikilinks]]`
5. If the knowledge base cannot fully answer, explicitly mark:
   "**知识库暂无覆盖的部分**: ..." and suggest what to ingest

**Output**: Direct conversation reply (no file). Sources as Obsidian wikilinks.

---

### Scenario 2: Topic Exploration (Stable)

**Trigger**: User wants to understand a topic in depth.

> "帮我梳理一下 Claude Code 生态的完整脉络"
> "AI 编程方法论有哪些流派，各自的优劣势？"

**Workflow**:
1. Locate the target topic page, read full content
2. Trace all linked summaries, read key sections of each
3. Trace linked concept cards to understand core concepts
4. Cross-topic search for related content
5. Synthesize output organized by logic, not by chronology

**Output**: Save to `outputs/` as a Markdown file with standard frontmatter (see Output Standards).

---

### Scenario 3: Cross-domain Analysis (Experimental)

**Trigger**: User wants to see connections between different knowledge domains.

> "知识管理方法论和 AI 记忆系统有什么共通之处？"
> "金融里的不对称风险概念，能用到 AI Agent 设计吗？"

**Workflow**:
1. From index.md, locate topic pages and concept cards in both domains
2. Read content from both sides, extract structured core viewpoints
3. Find concept-level mappings and intersection points
4. Generate analysis: commonalities, differences, transferability

**Output**: Save to `outputs/` as a cross-domain analysis report.

---

### Scenario 4: Learning Path (Experimental)

**Trigger**: User wants to learn a domain systematically.

> "我要学 Claude Code 开发，帮我规划学习路径"
> "从零理解多智能体系统，应该按什么顺序读？"

**Workflow**:
1. Locate relevant topic pages and summaries
2. Assess coverage and depth of the domain in the knowledge base
3. Order by dependency: foundational concepts → advanced practice → comprehensive application
4. Each step lists recommended summaries and concept cards to read
5. Mark gaps: content the knowledge base is missing (needs ingestion)

**Output**: Save to `outputs/` as a staged learning checklist.

---

### Scenario 5: Gap Detection (Experimental)

**Trigger**: User wants to know what the knowledge base is missing.

> "我的知识库在哪些方面还有空白？"
> "AI 编程这个主题，还有哪些重要内容没收录？"

**Workflow**:
1. Count summary coverage per topic
2. Check concept card inter-linking density (isolated concepts = may lack supporting material)
3. Check topic pages for blank "实践要点" sections
4. Output gap list sorted by priority

**Output**: Direct conversation reply, or save to `outputs/` if comprehensive.

---

### Scenario 6: Content Generation (Experimental)

**Trigger**: User wants to generate formatted content from the knowledge base.

> "帮我写一篇关于 AI Agent 设计模式的文章"
> "把金融认知这个主题整理成一份大纲"

**Workflow**:
1. Retrieve relevant topic pages, concept cards, summaries
2. Organize content for the target format
3. Cite sources and distinguish original synthesis vs. direct quotes
4. Save to appropriate outputs/ subdirectory

**Output format**: Organize by scenario:
- `outputs/articles/` — Long-form Markdown articles
- `outputs/memos/` — Research memos
- `outputs/outlines/` — PPT/article outlines
- `outputs/qa/` — High-value Q&A archives

---

## Output Standards

### Source Citation

All answers and output files must cite sources using Obsidian wikilinks:

```markdown
根据 [[上下文工程-概念]]，上下文工程是"动态选择、组织、注入和管理上下文信息"。
具体实践中，[[龙虾进化论 Day3-摘要-2026-03-26]] 指出 SKILL.md 是上下文工程的核心载体。
```

### Knowledge Boundary Marking

When the knowledge base cannot fully answer, explicitly distinguish:

```markdown
**知识库有覆盖的部分**：...
**知识库暂无覆盖，以下为补充推断**：...
**建议补充摄取**：关于 XXX 的内容，当前知识库暂无收录
```

### File Output Frontmatter

All file outputs include this frontmatter:

```yaml
---
type: qa | article | memo | outline | report
topic: linked topic name
sources:
  - "[[summary-filename]]"
  - "[[concept-filename]]"
created: YYYY-MM-DD
---
```

### Maturity Levels

| Level | Meaning |
|-------|---------|
| **Stable** | Works reliably with any knowledge base size. Tested patterns. |
| **Experimental** | Requires a mature knowledge base for good results. Quality scales with coverage and depth. Output may need human review. |
