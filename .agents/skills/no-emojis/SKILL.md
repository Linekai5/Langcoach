---
name: no-emojis
description: >-
  Enforces a strict zero-emoji policy across all code, markdown files, commit messages,
  repository documentation, and agent responses unless the user explicitly requests emojis.
  Activate whenever writing code, documentation, git messages, or responding in any session.
---

# Strict Zero-Emoji Policy

This skill enforces a strict, permanent rule: **never use emojis in any repositories, code, comments, documentation, or chat responses**, unless the user explicitly asks for them.

## Core Rules

1. **Code & Comments:**
   - Do not include emojis in code, docstrings, variable names, log statements, or comments.
   - Use clean, standard ASCII or plain UTF-8 text symbols only when strictly necessary.

2. **Repository Files & Documentation:**
   - Never add emojis to `README.md`, changelogs, configuration files, or license files.
   - Remove emojis from headings, lists, badges, and status indicators. Use plain text labels (e.g., "[WIP]", "[Done]", "[Warning]").

3. **Git Commits & Pull Requests:**
   - Never use Gitmoji or any emoji in git commit messages, branch names, PR titles, or descriptions.
   - Use standard conventional commits (e.g., `feat:`, `fix:`, `docs:`, `chore:`).

4. **Agent Chat Responses:**
   - Do not use emojis in assistant responses, summaries, or tool actions.
   - Keep communications crisp, technical, professional, and emoji-free.

5. **Exception:**
   - Only use emojis if the user explicitly requests them in their prompt.
