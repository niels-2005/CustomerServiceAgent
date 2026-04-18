# GH CLI Best Practices (Practical Solo-Team Workflow)

This guide teaches a production-style GitHub workflow for a solo developer.
The goal is to work like a team: short branches, explicit PRs, clear quality gates, and predictable merges.

## 1. Mental Model: `git` vs `gh`

- `git` manages your local history, branches, commits, and worktrees.
- `gh` manages GitHub objects: pull requests, checks, reviews, and merges.
- In practice, you use both:
  - build and commit locally with `git`
  - open/review/merge on GitHub with `gh`

## 2. Core Concepts (in plain English)

- `branch`: an isolated line of work.
- `pull request (PR)`: proposal to merge one branch into another (usually into `main`).
- `merge blocker`: mandatory condition before merge (for example tests green).
- `checks`: automated quality signals on a PR (tests, lint, type checks, etc.).
- `squash merge`: combines all PR commits into one commit on `main`.
- `trunk-based`: `main` stays healthy, and you merge small, short-lived branches frequently.
- `worktree`: a second working directory from the same repository, often used for parallel tasks.
- `stacked PRs`: split a bigger topic into smaller dependent PRs instead of one giant PR.

Practical sizing rule:
- Prefer `1 branch = 1 feature or fix`.
- Avoid bundling 5 unrelated features into one PR.
- For larger work, split into stacked PRs.

## 3. Daily Feature Flow (Copy/Paste)

### 3.1 Start from up-to-date `main`

```bash
git switch main
git pull
```

### 3.2 Create one branch for one goal

```bash
git switch -c feat/<short-name>
# examples: feat/login-copy, fix/session-timeout, docs/api-examples
```

### 3.3 Commit in small steps

```bash
git status
git add -p
git commit -m "feat: add clearer login guidance"
```

### 3.4 Run merge blockers locally (before PR)

Use the repo quality commands from `README.md`/`AGENTS.md`:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run pytest --collect-only
uv run pytest -m unit
```

If your change is broader, run the wider subset:

```bash
uv run pytest -m "not slow and not network"
```

### 3.5 Push and open PR to `main`

```bash
git push -u origin feat/<short-name>
gh pr create --base main --fill
```

Useful options:

```bash
gh pr create --base main --title "feat: ..." --body "..."
gh pr create --base main --draft
```

### 3.6 Check PR state and checks

```bash
gh pr status
gh pr view --web
gh pr checks
```

### 3.7 Mark ready, then merge

```bash
gh pr ready
gh pr merge --squash --delete-branch
```

Finally sync local `main`:

```bash
git switch main
git pull
```

## 4. Merge-Blocker Policy

A PR is mergeable only when all hard blockers are done.

Hard blockers:
- Scope is single-purpose (one feature/fix).
- Relevant local checks are green.
- PR description explains what changed and how it was verified.
- Self-review completed (diff sanity + behavior sanity).

Nice-to-have (not hard blockers):
- Commit message polishing before squash.
- Extra refactors not required for the change.

## 5. PR Management with `gh`

```bash
gh pr status                 # all your current PR context
gh pr view                   # current PR details
gh pr view --comments        # include discussion thread
gh pr checks                 # check run status
gh pr checkout <pr-number>   # check out someone else's PR locally
gh pr reopen <pr-number>     # reopen closed PR
gh pr close <pr-number>      # close PR without merge
```

## 6. Worktrees (When and Why)

### 6.1 What a worktree is

A worktree gives you another folder with the same repo, but on a different branch.
This avoids constant stashing/branch switching when handling parallel tasks.

### 6.2 Typical use case

- Worktree A: `feat/search-improvements`
- Worktree B: `fix/chat-timeout`

Both can be open at the same time in separate terminals/IDEs.

### 6.3 Commands

Create a new worktree from `main`:

```bash
git switch main
git pull
git worktree add ../customer_bot-fix-timeout -b fix/chat-timeout main
```

List active worktrees:

```bash
git worktree list
```

Remove a finished worktree:

```bash
git worktree remove ../customer_bot-fix-timeout
```

## 7. Large Work: Use Stacked PRs

If a topic is too big for one PR, split it into layers.

Example:
1. `feat/retrieval-refactor-base` -> PR A into `main`
2. `feat/retrieval-reranker` based on branch A -> PR B
3. `feat/retrieval-observability` based on branch B -> PR C

Commands:

```bash
git switch -c feat/retrieval-refactor-base main
# ... commit/push ...
gh pr create --base main --fill

git switch -c feat/retrieval-reranker feat/retrieval-refactor-base
# ... commit/push ...
gh pr create --base feat/retrieval-refactor-base --fill
```

After A merges, rebase B onto `main`, then update PR base.

## 8. Hotfix Flow

For urgent production fixes, keep the process short but strict.

```bash
git switch main
git pull
git switch -c fix/<short-name>
# implement fix
uv run pytest -m unit
git add -A
git commit -m "fix: <short description>"
git push -u origin fix/<short-name>
gh pr create --base main --fill
gh pr checks
gh pr merge --squash --delete-branch
```

## 9. Safe Recovery Basics

Undo last commit but keep changes staged:

```bash
git reset --soft HEAD~1
```

Unstage file but keep file edits:

```bash
git restore --staged <file>
```

Discard local edits in one file (destructive, use carefully):

```bash
git restore <file>
```

Rename local branch:

```bash
git branch -m feat/old-name feat/new-name
```

Update feature branch with latest `main`:

```bash
git switch feat/<short-name>
git fetch origin
git rebase origin/main
```

## 10. Solo-Team PR Checklist

Use this checklist before each merge:

1. One clear purpose in this PR.
2. Relevant quality commands are green.
3. PR description states scope, test evidence, and risk.
4. Self-review pass 1: code diff quality.
5. Self-review pass 2: behavior/regression risk.
6. Merge with `--squash`, then sync local `main`.

## 11. Common Anti-Patterns

- Direct commits to `main` for normal feature work.
- Long-lived branches that drift for days/weeks.
- Giant PRs with mixed concerns.
- Skipping local checks and using PR as a test runner.
- Parallel tasks in one working directory when worktrees would avoid conflicts.

## 12. Quick Command Cheat Sheet

```bash
# branch lifecycle
git switch main && git pull
git switch -c feat/<name>
git add -A && git commit -m "feat: ..."
git push -u origin feat/<name>

# PR lifecycle
gh pr create --base main --fill
gh pr checks
gh pr view --web
gh pr merge --squash --delete-branch

# cleanup
git switch main && git pull
git branch -d feat/<name>

# worktrees
git worktree add ../customer_bot-<task> -b feat/<task> main
git worktree list
git worktree remove ../customer_bot-<task>
```
