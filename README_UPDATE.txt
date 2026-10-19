OCP Personnel Portal update

1. Run supabase_migration_new_fields.sql in Supabase SQL Editor before deploying.
2. Replace deployed app.py with this updated file.
3. Existing staff records and project/status filters are retained.
4. Main table: Name, Position, Sector, Experience, Evaluation.
5. Evaluation choices: Exceptional (formerly Excellent), Exceed Requirements.
6. Evaluation guide and Type of Engagement UI removed.
7. Excel imports should include Name, Position, Sector, Experience, Evaluation, Status, Project.
8. Existing data without Sector/Experience will show blanks until edited/imported.
9. Supabase secrets are intentionally excluded from this archive. Configure them privately on your host.
