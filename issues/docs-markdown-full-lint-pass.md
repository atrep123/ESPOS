# Docs: Full Markdown Lint Pass

Owner: Codex/Docs
Labels: docs, lint, quality, good-first-issue

## Summary
Perform a repository-wide Markdown lint cleanup to satisfy common rules (spacing around headings/lists/fences, code fence languages, and bare URLs). This complements the partial fixes already pushed to branch `docs/markdown-lint-fixes` and aims to bring remaining docs to a consistent, clean state.

## Why
- Pre-commit/CI hooks flag recurring Markdown violations.
- Consistent docs improve readability and reduce noise in unrelated commits.

## Scope
Focus on these rules (based on current findings):
- MD022: Headings should be surrounded by blank lines.
- MD031: Fenced code blocks should be surrounded by blank lines.
- MD032: Lists should be surrounded by blank lines.
- MD034: No bare URLs (wrap in <...> or convert to links).
- MD040: Fenced code blocks should have a language.
- MD036: No emphasis as headings (use real headings).

## Known files (examples)
The initial pass fixed many items across:
- `COLLABORATIVE_WEB_DESIGNER.md`
- `INSTALLER_GUIDE.md`
- `ISSUE_10_IMPLEMENTATION.md`
- `NATIVE_TESTS_WINDOWS.md`
- `TEST_ISSUES_SUMMARY.md`
- `WEB_DESIGNER_README.md`
- `docs/TEMPLATE_MANAGER_GUIDE.md`
- `SIMULATOR_README.md` (already cleaned + new headless section)

Additional files likely need spacing/bare-URL adjustments; run a linter to enumerate all.

## Non-goals
- Do not change technical content or commands.
- Do not rename files or re-organize the docs structure.

## How
1. Run markdownlint (or the repo's pre-commit hook) to list violations.
2. Apply minimal whitespace/link fixes; add code fence languages where missing (prefer ```bash for shell, ```json, ```python, ```ini, etc.).
3. Convert emphasis headings to proper `####` or appropriate level.
4. Wrap bare URLs in `<...>` or convert to `[text](url)`.
5. Re-run linter; iterate until clean.

## Acceptance Criteria
- No MD022/MD031/MD032/MD034/MD036/MD040 violations in the repository.
- CI/pre-commit passes without Markdown-related failures.
- No changes to technical meaning, only formatting/structure.

## Notes
- A partial fix exists in branch `docs/markdown-lint-fixes`; continue there or open a new branch if preferred.
- Keep changes minimal and focused; avoid reflowing paragraphs unless required by the rules.
