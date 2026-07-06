---
description: Add to, don't replace, when refining any project Markdown document
metadata:
  type: project
---

When a request says "refine", "update", "rewrite", "scrap and reimplement", or otherwise asks to change a Markdown document (`CLAUDE.md`, `docs/*.md`, READMEs, guide files, `.claude/agents/*.md`, `.claude/rules/*.md`, or any other `.md`): preserve the existing file unless the user explicitly says "scrap it" or "start over".

## Core rule

Treat every Markdown file as living documentation. Do not erase and regenerate from scratch. Read the existing file first. Keep working sections, diagrams, examples, tables, and anything that hasn't been proven wrong by this session. Insert, edit, or append new content around what's already there.

## What counts as "proven wrong"

Only remove or replace content that:
- Is factually incorrect (e.g., a command that no longer works, a path that doesn't exist)
- Directly conflicts with new instructions being added
- Was explicitly called out by the user as broken or outdated

Everything else stays, even if it could be worded more elegantly.

## Order of operations

1. Read the current file
2. Identify what's still valid and keep it
3. Identify what's broken or outdated and fix it
4. Insert learning from the current session (new commands, discovered gotchas, resolved confusions) into the appropriate sections
5. If something new doesn't fit an existing section, add a new section rather than reorganizing the whole document
6. Report back on what you kept, what you changed, and what you added

## Why

Scrub-down rewrites lose the track of past decisions, diagrams that took effort to build, and examples that haven't been re-tested. The user has expressed frustration that early sections from the markdowns disappeared after a refinement pass and had to be rebuilt from earlier versions. An additive approach preserves that accumulated knowledge.
