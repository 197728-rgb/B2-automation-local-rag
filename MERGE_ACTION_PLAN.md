# Open PRs - Merge Action Plan
**Generated**: 2026-08-31 | **Status**: Ready to Review and Merge

---

## 🔴 CRITICAL - Security Issues (Merge First)

### PR #51 - WebSocket Security Fix
- **Created**: June 24, 2026 (67 days old)
- **Title**: Bump ws from 8.20.1 to 8.21.0
- **Issue**: Remote memory exhaustion DoS vulnerability
- **Fix**: Limits retained message parts with `maxBufferedChunks` and `maxFragments` options
- **Status**: ✅ Ready to merge
- **Action**: **MERGE IMMEDIATELY**

### PR #49 - esbuild Security Fixes  
- **Created**: June 13, 2026 (79 days old)
- **Title**: Bump esbuild from 0.28.0 to 0.28.1
- **Issues**:
  - Path traversal vulnerability on Windows (GHSA-g7r4-m6w7-qqqr)
  - Deno API integrity check improvements (GHSA-gv7w-rqvm-qjhr)
  - Module evaluation error handling fixes
- **Status**: ✅ Ready to merge
- **Action**: **MERGE IMMEDIATELY**

---

## 🟡 IMPORTANT - Dependency Updates (Merge Second)

### PR #52 - protobufjs Update
- **Created**: 41 days ago
- **Title**: Bump protobufjs from 7.6.0 to 7.6.5
- **Fixes**: EOF during options parsing bug fix
- **Status**: ✅ Ready to merge
- **Action**: **MERGE AFTER #49 & #51**

---

## 🟢 FEATURE - Knowledge Pack (Review Required)

### PR #53 - KNOWLAGE 1.3 Knowledge Pack
- **Created**: 1 hour ago (FRESH)
- **Title**: Add KNOWLAGE 1.3 repeatable audit knowledge pack
- **Scope**: Documentation-only knowledge for AAR B-2 / QAPE audit reports
- **Size**: 42 files changed, +6795/-10 lines
- **Risk Level**: Low (no source/test/schema changes, only documentation)
- **Status**: ⏳ Waiting for code review
- **Action**: **REVIEW FIRST, then merge**

---

## Recommended Merge Order

```
1. PR #51 (esbuild security)      → MERGE NOW
2. PR #49 (ws security)            → MERGE NOW  
3. PR #52 (protobufjs update)      → MERGE AFTER
4. PR #53 (knowledge pack)         → REVIEW + MERGE
```

---

## Summary

| PR | Priority | Age | Status | Action |
|---|----------|-----|--------|--------|
| #51 | 🔴 CRITICAL | 67d | ✅ Ready | MERGE NOW |
| #49 | 🔴 CRITICAL | 79d | ✅ Ready | MERGE NOW |
| #52 | 🟡 HIGH | 41d | ✅ Ready | MERGE AFTER |
| #53 | 🟢 MEDIUM | 1h | ⏳ Review | REVIEW + MERGE |

**Total Issues Fixed**: 4 PRs to process
**Estimated Time**: 5-10 minutes to merge all
