# InDE MVP v3.5.X Build Prompt — Template
## For Claude Code Execution

---

## Pre-Build Setup

1. **Load BUILD_CONTEXT.md** (NOT the full codebase)
   ```bash
   python tools/extract_interfaces.py
   # Review BUILD_CONTEXT.md for current state
   ```

2. **Review this build's specification**
   - What modules are being added/modified?
   - What audit findings are being resolved?
   - What new tests are required?

3. **Verify 5 containers healthy**
   ```bash
   docker compose up -d
   docker compose ps  # All should be healthy
   ```

4. **Run baseline tests**
   ```bash
   tools/run_tests.sh
   # All existing tests must pass before modifications
   ```

---

## Build Context Reference

The BUILD_CONTEXT.md contains:

### STABLE Modules (Signatures Only)
- Scaffolding engine and coaching logic
- Intelligence layer and TIM
- RVE and risk assessment
- Portfolio and analytics
- UI components and API endpoints
- Auth, RBAC, and core infrastructure

**DO NOT MODIFY** these modules unless absolutely necessary.
If modification is required, move to EXTEND category first.

### EXTEND Modules (Full Content)
- IKF federation components
- Event system
- GII manager
- Docker Compose

These are the primary targets for v3.5.x builds.

### REWRITE Modules (New Code)
- New modules created in this build
- Add to manifest after creation

---

## Phase Execution Template

### Phase N: [Phase Name]

**Objective:** [Clear statement of what this phase accomplishes]

**Files Modified:**
- `path/to/file1.py` - [What changes]
- `path/to/file2.py` - [What changes]

**New Files Created:**
- `path/to/new_file.py` - [Purpose]

**Verification:**
```bash
# Commands to verify phase completion
python -m pytest tests/test_specific.py -v
```

**Verification Gate:** [Clear pass/fail criteria]

---

## Post-Build Verification

### 1. Full Test Suite
```bash
tools/run_tests.sh
# All tests must pass
```

### 2. Backward Compatibility
- All v3.4 features verified working
- No coaching behavior changes (unless specified)
- API responses unchanged (unless specified)

### 3. Container Health
```bash
docker compose ps  # All 5 healthy
docker compose logs --tail=50 inde-app | grep -i error  # No errors
docker compose logs --tail=50 inde-ikf | grep -i error  # No errors
```

### 4. Performance Metrics
- [Any relevant performance checks]

---

## Build Summary Format

```markdown
# InDE MVP v3.5.X Build Summary

**Build Date:** [Date]
**Build Duration:** [Time]
**Token Count:** [Estimate]

## Changes Made
- [List of changes]

## Audit Findings Resolved
- [List with checkmarks]

## New Tests Added
- [Test file]: [Number of tests]

## Testing Results
- v3.4 Session 1: [X/29 passed]
- v3.4 Session 2: [X/45 passed]
- v3.5.X new tests: [X/Y passed]

## Known Issues
- [Any issues or observations]

## Files Modified
- [List of files with line counts]

## Files Created
- [List of new files]
```

---

## Tips for Efficient Builds

1. **Read BUILD_CONTEXT.md first** - not full files
2. **Only read full files when needed** - EXTEND modules are already included
3. **Update BUILD_MANIFEST.json** when adding new modules
4. **Run tests incrementally** - don't wait until the end
5. **Document deviations** - note any changes from the specification
6. **Keep commits atomic** - one logical change per commit

---

## Common Patterns

### Adding a New Module
1. Create the file in appropriate directory
2. Add to BUILD_MANIFEST.json in appropriate category
3. Add `__init__.py` exports if needed
4. Add tests
5. Run extraction to update BUILD_CONTEXT.md

### Modifying an EXTEND Module
1. Read full file from BUILD_CONTEXT.md
2. Make changes
3. Run affected tests
4. Verify no regressions

### Resolving an Audit Finding
1. Identify affected files
2. Make minimal changes to resolve
3. Add tests for new functionality
4. Document in build summary

---

*Template version 1.0 - Created for v3.5.0 Build Harness*
