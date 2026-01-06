# Claude Code Review Instructions

## Project Overview

ALLMS (AI-Powered Learning Management System) is a FastAPI-based web application for legal education. It provides:
- AI-powered tutoring using Anthropic Claude
- Interactive quiz system
- Study guide generation
- Multi-course architecture with Firestore backend
- Document processing and text extraction

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Database**: Google Cloud Firestore
- **AI**: Anthropic Claude API
- **Testing**: pytest (Python), Playwright (frontend)
- **Deployment**: Google Cloud Run, Docker

## Feature Development Workflow

This project follows a structured development workflow to ensure quality, maintainability, and proper documentation.

### 1. Issue Creation
- **Create a comprehensive GitHub issue** for each phase of work
- Include detailed description, tasks, deliverables, and acceptance criteria
- Reference parent issues for multi-phase features
- Use appropriate labels (e.g., `enhancement`, `bug`, `documentation`)

### 2. Development
- Create a feature branch from `main` (e.g., `feature/gamification-phase-3-streaks`)
- Work on the feature, making incremental commits
- **All commit messages must reference the issue** (e.g., `feat: Add streak calculation logic (#124)`)
- Update the GitHub issue with progress as you work
- Follow conventional commit format: `type: description (#issue)`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### 3. Testing
- **Ensure comprehensive test coverage before creating PR**
- Write unit tests for all new functions/methods
- Write integration tests for API endpoints
- Write E2E tests for user-facing features
- All tests must pass before proceeding
- Aim for >80% code coverage on new code

### 4. Pull Request Creation
- Create PR with **comprehensive description** including:
  - Overview of changes
  - Related issues (e.g., `Implements: #124`, `Parent: #121`)
  - What changed (backend, frontend, tests)
  - Testing performed
  - Known limitations or future work
  - Deployment notes (breaking changes, migrations, etc.)
- Link all related issues in the PR description
- Ensure PR title follows format: `Phase X: Feature Name`

### 5. Code Review Process

#### Initial Review
1. **Trigger code review** by commenting `@claude review` on the PR
2. Wait for review comments to be posted
3. Review comments will be categorized by priority:
   - **CRITICAL** - Must fix immediately (security, data loss, breaking changes)
   - **HIGH** - Must fix before merge (bugs, performance issues, missing validation)
   - **MEDIUM** - Should fix before merge (code quality, missing tests, documentation)
   - **LOW** - Nice to have (style, minor refactoring, trivial improvements)

#### Addressing Feedback
1. **Fix all CRITICAL and HIGH priority issues** immediately
2. **Fix all MEDIUM priority issues** unless there's a good reason to defer
3. **For LOW priority issues:**
   - Check if an existing GitHub issue already covers the item
   - If not, create a new issue for future work
   - Reference the new issue in a PR comment
4. Commit fixes with descriptive messages referencing the PR
   - Example: `fix: Address code review feedback - race condition (#134)`
5. Push changes to the PR branch

#### Iterative Review
1. **Re-trigger code review** by commenting `@claude review` again
2. Wait for updated review comments
3. Repeat the addressing feedback process
4. **Continue until no CRITICAL, HIGH, or MEDIUM issues remain**

### 6. Merge and Release

#### Merging
1. Once all important issues are resolved, **merge the PR**
2. Use "Squash and merge" for cleaner history
3. Ensure merge commit message is descriptive
4. Delete the feature branch after merge

#### Release Process
1. **Determine the next version** using semantic versioning:
   - **MAJOR** (v3.0.0) - Breaking changes
   - **MINOR** (v2.10.0) - New features, backward compatible
   - **PATCH** (v2.9.1) - Bug fixes, backward compatible
2. **Create and push a version tag** (e.g., `v2.10.0`)
3. **Create a GitHub release** with:
   - Release notes describing new features and fixes
   - Links to related PRs and issues
   - Any deployment notes or breaking changes
4. **Automated deployment** will trigger via GitHub Actions
5. Monitor deployment status in GitHub Actions tab

### Example Workflow

```bash
# 1. Create feature branch
git checkout -b feature/gamification-phase-4-badges

# 2. Make changes and commit
git add .
git commit -m "feat: Add badge earning logic (#125)"

# 3. Push and create PR
git push origin feature/gamification-phase-4-badges
# Create PR on GitHub with comprehensive description

# 4. Trigger code review
# Comment "@claude review" on the PR

# 5. Address feedback
git add .
git commit -m "fix: Address code review - validation and error handling (#134)"
git push origin feature/gamification-phase-4-badges

# 6. Re-trigger review if needed
# Comment "@claude review" again

# 7. Merge PR (via GitHub UI)

# 8. Create release
git checkout main
git pull origin main
git tag -a v2.10.0 -m "Release v2.10.0: Badge System"
git push origin v2.10.0
# Create GitHub release via UI or API
```

### Best Practices

- **Never skip testing** - untested code should not be merged
- **Keep PRs focused** - one feature/phase per PR
- **Write descriptive commit messages** - explain why, not just what
- **Update documentation** - keep README, API docs, and CLAUDE.md current
- **Check for duplicate issues** - before creating new low-priority issues
- **Monitor CI/CD** - ensure automated tests and deployment succeed
- **Communicate blockers** - if stuck, ask for help in the issue/PR

## Deployment Process

**Automated Production Deployment:**
- Deployment to production is automatically handled by a GitHub Action
- Any commit tagged with a semantic version (e.g., `v2.9.0`, `v1.2.3`) triggers the deployment
- The GitHub Action automatically deploys to Google Cloud Run
- See `.github/` folder for workflow configuration and deployment scripts
- **Do NOT manually deploy to production** - always use version tags to trigger automated deployment

## Code Review Focus Areas

### Security (CRITICAL)
- XSS vulnerabilities in JavaScript (always use `escapeHtml()` for user content)
- SQL/NoSQL injection in database queries
- Input validation on all API endpoints
- Proper authentication/authorization checks
- No secrets or API keys in code

### JavaScript Best Practices
- Use event delegation instead of inline `onclick` handlers (CSP compliance)
- Always validate array indices before access
- Proper error handling with try/catch
- No memory leaks from event listeners

### Python Best Practices
- Type hints on all function signatures
- Proper exception handling with specific exception types
- Use of async/await for I/O operations
- Follow PEP 8 style guidelines

### Testing
- All new features should have corresponding tests
- Mock external services (Firestore, Anthropic API)
- Test error handling paths
- Maintain backward compatibility

## File Structure

```
app/
├── main.py              # FastAPI application entry point
├── routes/              # API route handlers
├── services/            # Business logic services
├── models/              # Pydantic schemas
└── static/              # CSS and JavaScript files
templates/               # Jinja2 HTML templates
tests/                   # pytest test files
e2e/                     # Playwright frontend tests
```

## Review Guidelines

1. **Must Fix**: Security vulnerabilities, data loss risks, breaking changes
2. **Should Fix**: Performance issues, code quality, missing tests
3. **Consider**: Style improvements, documentation, refactoring suggestions

## Common Patterns

### API Response Format
```python
{"status": "success", "data": {...}}
{"status": "error", "message": "..."}
```

### Quiz Data Format
```json
{"quiz": {"questions": [{"question": "...", "options": [...], "correct_index": 0}]}}
```

### Course Context
The application supports multi-course mode with `course_id` parameter for filtering content.

