# Git & Version Control Standards

## Commit Messages
- **Format:** `<type>: <description>`
- **Length:** <50 characters
- **No emojis** in commits or PR titles
- **No co-author mentions**
- **Types:**
  - `feat:` New feature
  - `fix:` Bug fix
  - `docs:` Documentation only
  - `refactor:` Code restructuring
  - `test:` Adding tests (real tests only)
  - `chore:` Maintenance tasks

## Branch Strategy
- **main**: Production-ready code (stable releases, tagged)
- **develop**: Active development branch (default PR target)
- **Feature branches:** `feature/short-description` (from develop)
- **Bugfix branches:** `fix/issue-description` (from develop)
- **No spaces** in branch names, use hyphens
- **Delete after merge**

## Commit Practice
- **Atomic commits** - One logical change per commit
- **Test before commit** - Ensure code works
- **No broken commits** - Each commit should work independently
- **Commit frequently** - Track progress effectively

## Pull Request Process
1. Create issue first (for significant changes)
2. Branch from develop (NOT main)
3. Make atomic commits
4. Push branch
5. Create PR targeting develop with:
   - Clear, concise title (no issue numbers in title)
   - Description with "Fixes #123" if applicable
   - Test results
   - Use [x] for completed tasks, not emojis

## Versioning
- Use `scripts/bump_version.py` for version bumping
- PRs to develop: `.dev` suffix (e.g., `0.6.8.dev0`)
- PRs to main: `a` (alpha) suffix (e.g., `0.6.8a1`)
- Tags: ONLY push after PR is merged, never from feature branches

---
*Atomic commits, clear messages, clean history. PRs target develop by default.*
