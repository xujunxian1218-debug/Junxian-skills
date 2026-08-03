# Digestion — Deduplication & Source Rules

> v1.12.0 切片（从 digestion-rules.md 拆出）。Digest 预检阶段读取。
> 其他切片：[generation.md](generation.md) / [review.md](review.md)

---

## Deduplication Logic

Before digesting, determine which raw files actually need processing by running
the automated check script:

```bash
python <skill-path>/scripts/check_undigested.py --vault <vault-path>
```

The script uses a three-layer matching strategy:

### Layer 1: Exact match

Normalize filenames (strip special chars, lowercase) and compare raw file names
against all summary `source` fields. A direct match means the file is already
digested.

### Layer 2: Date + source cross-match

For multi-format content (e.g., preprocessed summaries + raw ASR transcripts
from the same episode):
1. Extract dates and source identifiers from filenames
2. Build a set of all `(date, source_id)` pairs from existing summaries
3. If a raw file's `(date, source_id)` pair is in this set, mark as `DUPE`

This handles cases like:
- `科技前哨_2026-04-27_AI繁荣...md` (preprocessed)
- `2026-04-27_keji_qianshao_raw.md` (raw transcript)
Both share date `2026-04-27` and source `keji-qianshao`, so if either has been
digested, both are marked as covered.

### Layer 3: Fuzzy prefix match

Compare the first 20 characters of normalized filenames. If they match, the file
is likely covered. Falls through to `MANUAL` category if no match is found at
any layer.

### Output categories

| Category | Meaning | Action |
|----------|---------|--------|
| `NEW` | Genuinely undigested content | Digest these files |
| `UPDATED` | Previously digested but file content changed (SHA256 differs) | Show in Review; re-digesting overwrites existing summary |
| `DUPE` | Already covered by another format | Skip |
| `SKIP` | Metadata/manifest/non-content files | Skip |
| `MANUAL` | Cannot auto-determine | Ask user |

The script detects `UPDATED` files by comparing SHA256 hashes stored in
`.llm-wiki-cache/hashes.json`. A file is marked `UPDATED` when its normalized
name matches an existing summary (Layer 1) but its hash differs from the cache.

### File exclusion rules

The script automatically skips files whose names contain: `manifest`, `metadata`,
`index`, `.git`, `__pycache__`. These are metadata files, not knowledge content.

---

## Source Field Priority

When a single piece of content exists in multiple formats (e.g., preprocessed
summary + raw ASR transcript), follow this priority for the summary's `source`
field:

1. **Preprocessed summary** (e.g., `科技前哨_2026-04-27_AI繁荣...md`) — preferred
   because it's more readable and structured
2. **Raw ASR transcript** (e.g., `2026-04-27_keji_qianshao_raw.md`) — use only
   when no preprocessed version exists

Rationale: clicking `source` in Obsidian should lead to the most readable version
of the original content, not a raw transcript full of homophone errors.

When an existing summary's `source` points to a raw transcript but a preprocessed
version also exists, the Audit phase can flag this as "source optimization suggested"
(but never auto-fix — Audit only reports).

### Source Path Verification

填写 `source` 字段时，必须通过 Glob 工具验证 raw 目录下的实际文件名，
不能凭记忆或猜测填写。步骤：
1. 从源文件路径提取文件名关键词
2. 用 Glob 搜索 `raw/**/{关键词}*` 确认实际路径
3. 使用 Glob 返回的精确文件名填入 source 字段

这确保中文弯引号、特殊破折号等字符与实际文件名完全一致。
