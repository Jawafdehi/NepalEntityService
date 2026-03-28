# Migration Maintainer Guide

This guide is for maintainers who review migration pull requests and execute migrations to update the Nepal Entity Service database. You'll learn how to review migrations, execute them safely, and troubleshoot common issues.

## Table of Contents

1. [Introduction](#introduction)
2. [Maintainer Responsibilities](#maintainer-responsibilities)
3. [Reviewing Migration Pull Requests](#reviewing-migration-pull-requests)
4. [Executing Migrations](#executing-migrations)
5. [CI/CD Workflows](#cicd-workflows)
6. [Troubleshooting](#troubleshooting)
7. [Database Repository Management](#database-repository-management)
8. [Best Practices](#best-practices)

---

## Introduction

### What is a Maintainer?

Maintainers are trusted individuals who:
- Review migration pull requests for quality and correctness
- Execute approved migrations to update the database
- Manage the Database Repository
- Ensure data integrity and quality
- Monitor CI/CD workflows

### Two-Repository Architecture

The system operates across two repositories:

1. **Service API Repository** (NepalEntityService)
   - Contains application code and migration scripts
   - Contributors submit PRs here
   - Lightweight (~10MB)

2. **Database Repository** (nes-db)
   - Contains entity/relationship JSON files (100k-1M files)
   - Managed as a separate Git repository at `nes-db/`
   - Large repository (~1GB+)
   - Modified by migration execution

**Key Concept**: Contributors submit migration code to the Service API Repository. Maintainers review and merge the code, then execute migrations locally which modify files in the Database Repository.

---

## Maintainer Responsibilities

### Code Review

- Review migration scripts for correctness and safety
- Verify data sources are cited and credible
- Check for proper error handling
- Ensure migrations follow conventions
- Test migrations locally before merging

### Data Quality

- Verify data accuracy against sources
- Check for duplicates and conflicts
- Ensure multilingual data (English + Nepali)
- Validate entity relationships
- Maintain data consistency

### Execution

- Execute approved migrations
- Monitor migration progress
- Handle failures gracefully
- Commit changes to Database Repository

### Documentation

- Ensure migrations are well-documented
- Update guides as needed
- Document troubleshooting solutions
- Maintain migration history

---

## Reviewing Migration Pull Requests

### Step 1: Initial Review

When a migration PR is submitted, check:

**PR Structure**:
- [ ] Migration folder follows naming convention (NNN-descriptive-name)
- [ ] Contains migrate.py with required metadata
- [ ] Contains README.md with documentation
- [ ] Data files are included if needed

**Code Quality**:
- [ ] Migration script has AUTHOR, DATE, DESCRIPTION metadata
- [ ] Implements async `migrate(context)` function
- [ ] Includes error handling
- [ ] Uses appropriate author ID
- [ ] Logs progress messages

**Documentation**:
- [ ] README.md explains purpose clearly
- [ ] Data sources are cited with URLs
- [ ] Changes are documented
- [ ] Dependencies are noted

### Step 2: Data Source Verification

Verify the data sources:

```markdown
## Checklist for Data Sources

- [ ] Sources are credible (government, official records, reputable organizations)
- [ ] URLs are accessible and valid
- [ ] Data matches the source (spot check)
- [ ] Date of data collection is noted
- [ ] Licensing allows use (public domain, open data, etc.)
```

### Step 3: Code Review

Review the migration script:

**Safety Checks**:
```python
# ✓ Good: Checks if entity exists before creating
entity = await context.search.find_entity_by_name(name, type)
if not entity:
    await context.publication.create_entity(...)

# ✗ Bad: Creates without checking (may cause duplicates)
await context.publication.create_entity(...)
```

**Error Handling**:
```python
# ✓ Good: Handles errors gracefully
try:
    await context.publication.create_entity(...)
except Exception as e:
    context.log(f"Failed: {e}")
    # Continue processing

# ✗ Bad: No error handling (migration crashes on first error)
await context.publication.create_entity(...)
```

**Data Quality**:
```python
# ✓ Good: Validates data before processing
if not row.get("name_en") or not row.get("name_ne"):
    context.log(f"Skipping row with missing names: {row}")
    continue

# ✗ Bad: No validation (may create incomplete entities)
entity_data = {"names": [{"en": {"full": row["name_en"]}}]}
```

### Step 4: Local Testing

Test the migration locally before merging:

```bash
# Pull the PR branch
git fetch origin pull/123/head:pr-123
git checkout pr-123

# Ensure database repository is present and up to date
cd nes-db && git pull origin main && cd ..

# Run migration
nes migration run NNN-migration-name

# Review output for errors or warnings
```

**What to Check**:
- Migration executes without errors
- Entities are created correctly
- Relationships are valid
- No duplicate entities
- Logs are informative

### Step 5: Request Changes or Approve

**If changes are needed**:
```markdown
Thanks for the contribution! A few items to address:

1. **Data Source**: Please add a URL to the official government source
2. **Error Handling**: Add try/except around entity creation (line 45)
3. **Validation**: Check for empty names before creating entities
4. **Documentation**: Add the date when data was collected

Let me know if you have questions!
```

**If approved**:
```markdown
Looks great! The migration is well-structured and data sources are verified.

I'll merge this and execute the migration.
```

### Step 6: Merge the PR

Once approved:

```bash
# Merge via GitHub UI or command line
git checkout main
git merge pr-123
git push origin main
```

---

## Executing Migrations

### Step 1: Check Pending Migrations

```bash
# See all pending migrations
nes migration list --pending

# Output:
# Pending migrations:
#   005-add-cabinet-ministers
#   006-update-party-leadership
```

### Step 2: Execute Single Migration

```bash
# Run specific migration
nes migration run 005-add-cabinet-ministers

# Output:
# Running migration: 005-add-cabinet-ministers
# [Migration] Processing 25 entities...
# [Migration] Created 25 entities
# [Migration] Migration completed
# ✓ Migration completed in 12.3s
# ✓ Committed to database repository
# ✓ Pushed to remote
```

**What Happens**:
1. Migration script executes
2. Entities/relationships are created in `nes-db/v2/`
3. Changes are committed to Database Repository with metadata
4. Commit is pushed to remote

### Step 3: Execute All Pending Migrations

```bash
# Run all pending migrations in order
nes migration run --all

# Output:
# Running 2 pending migrations...
# 
# [1/2] Running: 005-add-cabinet-ministers
# ✓ Completed in 12.3s
# 
# [2/2] Running: 006-update-party-leadership
# ✓ Completed in 8.7s
# 
# All migrations completed successfully
```

### Step 4: Verify Results

```bash
# Check database repository
cd nes-db
git log -3

# Output:
# commit abc123...
# Author: Migration System
# Date: 2024-03-15
# 
#     Migration: 005-add-cabinet-ministers
#     
#     Import current cabinet ministers from official records
#     
#     Author: contributor@example.com
#     Date: 2024-03-15
#     Entities created: 25
#     Relationships created: 25
#     Duration: 12.3s

# Check created files
ls v2/entity/person/ | tail -5
```

### Step 5: (Skip) Update Service API Repository

*(Historically, this step involved updating the git submodule reference. Since the database is now decoupled, this step is no longer necessary.)*

---

## CI/CD Workflows

The migration system includes two GitHub Actions workflows:

### Migration Preview Workflow

**Trigger**: Pull request to `migrations/` directory

**Purpose**: Preview migration results before merging

**What it does**:
1. Checks out PR branch
2. Runs migrations in isolated environment
3. Generates statistics (entities/relationships created)
4. Posts comment on PR with results

**Example Comment**:
```markdown
## Migration Preview: 005-add-cabinet-ministers

✓ Migration executed successfully

### Statistics
- Entities created: 25
- Relationships created: 25
- Duration: 12.3s

### Logs
[View full logs](https://github.com/.../actions/runs/123)
```

### Migration Persistence Workflow

**Triggers**:
- PR merge to main branch (if migrations/ changed)
- Daily schedule (2 AM UTC)

**Purpose**: Automatically execute pending migrations

**What it does**:
1. Checks for pending migrations
2. Executes pending migrations
3. Commits to Database Repository
4. Pushes to remote

**Monitoring**:
```bash
# Check workflow status on GitHub
# https://github.com/Jawafdehi/NepalEntityService/actions

# View workflow logs for details
```

**Manual Trigger**:
```bash
# Trigger workflow manually via GitHub UI
# Actions → Migration Persistence → Run workflow
```

---

## Troubleshooting

### Issue 1: Migration Fails with Validation Error

**Symptom**:
```
ValueError: Entity must have at least one name with kind='PRIMARY'
```

**Solution**:
1. Review migration script for data validation
2. Check input data files for missing fields
3. Add validation before entity creation:

```python
if not row.get("name_en"):
    context.log(f"Skipping row with missing name: {row}")
    continue
```

### Issue 2: Duplicate Entity Error

**Symptom**:
```
ValueError: Entity with slug 'ram-sharma' already exists
```

**Solution**:
1. Check if entity exists before creating:

```python
from nes.core.identifiers import build_entity_id

entity_id = build_entity_id("person", None, "ram-sharma")
existing = await context.db.get_entity(entity_id)

if existing:
    # Update instead of create
    await context.publication.update_entity(...)
else:
    await context.publication.create_entity(...)
```

### Issue 3: Migration Already Applied

**Symptom**:
```
Migration already applied, skipping
```

**Explanation**: The migration was already executed and committed to the Database Repository. The system detects the persisted snapshot and skips re-execution.

**Solution**:
- This is expected behavior (ensures determinism)
- To re-run, delete the migration log first: `rm -rf nes-db/v2/migration-logs/NNN-name/`
- For production, create a new migration instead

### Issue 4: Large Commit Performance

**Symptom**: Migration creates 10,000+ files and Git commit is slow

**Solution**: The system automatically batches commits:

```python
# Automatic batching (no action needed)
# Commits are split into batches of 1000 files each
# Each batch gets its own commit with metadata
```

**Manual Optimization**:
```bash
# Configure Git for large repositories
cd nes-db
git config core.preloadindex true
git config core.fscache true
git config gc.auto 256
```

### Issue 5: Relationship Target Not Found

**Symptom**:
```
ValueError: Target entity 'entity:organization/...' does not exist
```

**Solution**:
1. Verify target entity exists:

```python
target = await context.db.get_entity(target_id)
if not target:
    context.log(f"Target entity not found: {target_id}")
    continue
```

2. Check migration dependencies in README.md
3. Ensure prerequisite migrations are executed first

### Issue 6: Git Push Fails

**Symptom**:
```
error: failed to push some refs to 'https://github.com/...'
```

**Solution**:
1. Pull latest changes:

```bash
cd nes-db
git pull origin main
```

2. Resolve conflicts if any
3. Push again:

```bash
git push origin main
```

### Issue 7: Database Repository Out of Sync

**Symptom**: Local database repository is missing recent migrations.

**Solution**:
```bash
# Update repository to latest
cd nes-db
git pull origin main
cd ..
```

---

## Database Repository Management

### Cloning for Maintainers

**Full Clone** (for migration execution):
```bash
# Clone the codebase
git clone https://github.com/Jawafdehi/NepalEntityService.git
cd NepalEntityService

# Clone the database (~1GB+)
git clone https://github.com/Jawafdehi/NepalEntityService-database.git ./nes-db
```

**Shallow Clone** (for development):
```bash
# Clone with limited history
git clone --depth 1 https://github.com/Jawafdehi/NepalEntityService-database.git ./nes-db
```

### Database Repository Optimization

**For Large Repositories**:
```bash
cd nes-db

# Configure Git for performance
git config core.preloadindex true
git config core.fscache true
git config gc.auto 256
git config pack.threads 4

# Periodic maintenance
git gc --aggressive
```

### Backup Strategy

**Automated Backups**:
- GitHub provides automatic backups
- Git history serves as complete backup
- All changes are versioned and recoverable

**Manual Backup**:
```bash
# Clone database repository
git clone https://github.com/Jawafdehi/NepalEntityService-database.git backup-$(date +%Y%m%d)

# Or create archive
cd nes-db
git archive --format=tar.gz --output=../backup-$(date +%Y%m%d).tar.gz HEAD
```

### Rollback Procedure

**Rollback Single Migration**:
```bash
cd nes-db

# Find migration commit
git log --grep="Migration: 005-add-cabinet-ministers"

# Revert the commit
git revert <commit-sha>

# Push revert
git push origin main
```

**Rollback Multiple Migrations**:
```bash
# Revert last 3 migrations
git revert HEAD~2..HEAD

# Or reset to specific commit (destructive)
git reset --hard <commit-sha>
git push --force origin main  # Use with caution!
```

---

## Best Practices

### 1. Review Before Merging

Never merge a migration PR without:
- Local testing
- Data source verification
- Code review
- Documentation check

### 2. Execute Migrations Promptly

- Execute migrations within 24-48 hours of merging
- Don't let pending migrations accumulate
- Monitor CI/CD workflows for automatic execution

### 3. Monitor Database Size

```bash
# Check database size
cd nes-db
du -sh .

# Check entity counts
find v2/entity -type f | wc -l
find v2/relationship -type f | wc -l
```

### 4. Communicate with Contributors

- Provide clear feedback on PRs
- Explain rejection reasons
- Acknowledge good contributions
- Help improve migration quality

### 5. Document Issues

When encountering issues:
- Document the problem and solution
- Update this guide if needed
- Share knowledge with other maintainers

### 6. Regular Maintenance

**Weekly**:
- Review pending migrations
- Check CI/CD workflow status
- Monitor database repository size

**Monthly**:
- Review migration history
- Audit data quality
- Update documentation
- Optimize database repository

### 7. Security Considerations

- Review migration scripts for malicious code
- Verify data sources are legitimate
- Check for sensitive information in data files
- Ensure proper attribution

### 8. Coordinate with Other Maintainers

- Communicate before executing large migrations
- Avoid concurrent migration execution
- Share knowledge and best practices
- Document decisions

---

## Migration Execution Checklist

Use this checklist when executing migrations:

```markdown
## Pre-Execution

- [ ] Migration PR is approved and merged
- [ ] Local repository is up to date
- [ ] Database repository is up to date (run `cd nes-db && git pull && cd ..`)
- [ ] No pending changes in database repository

## Execution

- [ ] Run `nes migration list --pending` to see pending migrations
- [ ] Run `nes migration run <name>` or `--all`
- [ ] Monitor output for errors
- [ ] Verify entities/relationships/versions created
- [ ] Review migration log in `nes-db/v2/migration-logs/`

## Post-Execution

- [ ] Check database repository commit
- [ ] Verify commit message includes metadata
- [ ] Confirm push to remote succeeded
- [ ] Verify CI/CD workflow completed (if applicable)
- [ ] Spot-check created entities for quality

## Documentation

- [ ] Update migration status in tracking system (if any)
- [ ] Document any issues encountered
- [ ] Communicate completion to contributor
```

---

## Additional Resources

- **Contributor Guide**: See [Migration Contributor Guide](/contributors/migration-contributor-guide) for contributor workflow
- **Architecture**: See [Migration Architecture](/contributors/migration-architecture) for system design
- **API Reference**: See [OpenAPI documentation](/docs) for complete API documentation
- **Data Maintainer Guide**: See [Data Maintainer Guide](/contributors/data-maintainer-guide) for Publication Service usage

---

## Support

For maintainer questions or issues:

1. Check this guide and other documentation
2. Review existing migrations for examples
3. Consult with other maintainers
4. Open an issue for bugs or unclear documentation

---

**Last Updated:** 2024
**Version:** 2.0
