# Database Migrations Guide

## Overview

This project uses **Alembic** to version control database schema changes. This ensures your local database, staging, and production databases all have the same schema.

## How It Works

1. **Migration files** are stored in `alembic/versions/`
2. **Migrations are run automatically** when the backend starts (`app/main.py`)
3. **Both local and production databases** run the same migrations
4. **Schema is tracked in Git** - everyone has the same schema

## Local Development

### Start with a fresh database
```powershell
# Start PostgreSQL
docker-compose up

# Backend will automatically run migrations on startup
uvicorn app.main:app --reload --port 8000
```

### Check migration status
```powershell
# From project root
alembic current              # Show current revision
alembic heads               # Show latest migration
alembic history             # Show all migrations
```

## Creating a New Migration

When you change your database models in `app/db/models.py`:

### 1. Auto-generate migration
```powershell
alembic revision --autogenerate -m "description of changes"
```

For example:
```powershell
alembic revision --autogenerate -m "Add status_reason column to clinical_trials"
```

This creates a new file in `alembic/versions/` like `002_add_status_reason_column.py`

### 2. Review the generated migration
Always **inspect** the generated migration file to ensure it looks correct:
- Check the `upgrade()` function
- Check the `downgrade()` function (for rollbacks)

### 3. Test locally
```powershell
# Start fresh database
docker-compose down -v
docker-compose up
uvicorn app.main:app --reload --port 8000

# Backend will run the new migration automatically
```

### 4. Commit to Git
```powershell
git add alembic/versions/002_add_status_reason_column.py
git commit -m "Add migration: add status_reason column to clinical_trials"
```

## Manual Migrations (Advanced)

If auto-generate doesn't work perfectly, you can write migrations manually:

```powershell
alembic revision -m "Add new_column to trials"
```

This creates a template you can edit manually with custom SQL.

## Production Deployments

**On Railway:**
1. Code is deployed with migration files
2. Backend starts and automatically runs migrations
3. Database schema updates without manual intervention
4. No downtime (migrations happen on boot)

## Rollback (Emergency)

If a migration causes issues:

```powershell
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 001_initial_schema
```

**Note:** Only use rollbacks in emergencies - always test migrations locally first!

## Best Practices

✅ **DO:**
- Test migrations locally before pushing
- Review auto-generated migrations carefully
- Keep migrations focused (one change per migration)
- Write meaningful migration messages
- Include both `upgrade()` and `downgrade()` functions

❌ **DON'T:**
- Modify old migration files (create new ones instead)
- Skip testing migrations locally
- Deploy without testing on production-like environment
- Use raw `Base.metadata.create_all()` (use migrations instead)

## Common Issues

### "Database not initialized"
- Start PostgreSQL: `docker-compose up`
- Migrations run automatically on backend start

### Migration file not found
- Check file is in `alembic/versions/`
- Ensure revision ID is correct
- Run `alembic history` to debug

### "Can't locate revision"
- Ensure DATABASE_URL is correct in `.env.local`
- Check PostgreSQL is running

## Example Migration

Here's what a typical migration looks like:

```python
"""Add email field to users

Revision ID: 003_add_user_email
Revises: 002_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_user_email'
down_revision = '002_initial_schema'

def upgrade() -> None:
    op.add_column('users', sa.Column('email', sa.String(255), unique=True))

def downgrade() -> None:
    op.drop_column('users', 'email')
```

## Need Help?

- Check status: `alembic current`
- View history: `alembic history`
- View SQL: `alembic upgrade head --sql`
