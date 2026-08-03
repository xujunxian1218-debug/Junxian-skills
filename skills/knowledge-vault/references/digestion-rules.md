# Digestion Rules（索引）

> v1.12.0 起，本文件拆为 3 个按阶段切片，Agent 按阶段只读对应切片以省 token（~30-40%）。
> 全局视角读本索引；具体规则读对应切片。

## 切片

| 切片 | 阶段 | 内容 |
|---|---|---|
| [digestion/dedup.md](digestion/dedup.md) | 预检 | Deduplication Logic + Source Field Priority |
| [digestion/generation.md](digestion/generation.md) | Analysis + Generation | Two-Step Digestion + Page Merge + Image Processing（含 Step 3 识图）+ Naming + Template Fields + Index Update |
| [digestion/review.md](digestion/review.md) | Review（self-check 后）| Review Output Format |

## 按阶段读取

- **预检**（去重/NEW 判定）：读 `dedup.md`
- **Step 1 Analysis + Step 2 Generation**：读 `generation.md`
- **Digest Review**（self-check 后）：读 `review.md`
