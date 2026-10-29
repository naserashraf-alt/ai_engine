r"""
=============================================================================
scripts/export_to_sqlserver.py - Universal SQLite -> Microsoft SQL Server Exporter
=============================================================================

الغرض (Purpose):
- نقل وتصدير كامل بيانات قاعدة بيانات SQLite (jobs.db) إلى Microsoft SQL Server:
  1. توليد سكربت T-SQL كامل وشامل وجاهز للتشغيل مباشرة في SSMS (SQL Server Management Studio).
  2. تحويل أنواع البيانات آلياً من SQLite إلى Microsoft SQL Server (T-SQL).
  3. نقل جميع الجداول:
     - jobs (3,432 وظيفة تقنية حية مع كافة الحقول)
     - candidates (بيانات وسير المرشحين)
     - reports (تقارير التقييم التنفيذية)
     - report_evaluations (تقييمات الوظائف وخطابات التقديم ولينكد إن)
     - partition_summaries (ملخصات التقسيم الجغرافي)
     - skills & job_skills & scrape_runs
  4. دعم النقل المباشر عبر pyodbc و Windows Authentication بنقرة واحدة.

الاستخدام (Usage):
  1. توليد ملف SQL لتشغيله في SSMS:
     python scripts/export_to_sqlserver.py
  2. النقل المباشر عبر السيرفر:
     python scripts/export_to_sqlserver.py --server localhost
     أو
     python scripts/export_to_sqlserver.py --server .\SQLEXPRESS
=============================================================================
"""

import os
import sys
import sqlite3
import json
import argparse
from datetime import datetime

# Force unbuffered UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)


def escape_tsql_val(val: any) -> str:
    """Escapes a Python/SQLite value for safe T-SQL injection."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (list, dict)):
        val = json.dumps(val, ensure_ascii=False)
    
    s = str(val).replace("'", "''")
    return f"N'{s}'"


def map_sqlite_to_tsql_type(col_name: str, col_type: str, is_pk: bool) -> str:
    """Maps SQLite column type to Microsoft SQL Server T-SQL column type."""
    col_name_lower = col_name.lower()
    col_type_upper = (col_type or "TEXT").upper()

    if is_pk and col_name_lower == "id":
        return "INT IDENTITY(1,1) PRIMARY KEY"

    if "INT" in col_type_upper:
        if col_name_lower in ["is_remote"]:
            return "BIT DEFAULT 0"
        return "INT DEFAULT 0"

    if any(t in col_type_upper for t in ["REAL", "FLOAT", "DOUBLE"]):
        return "FLOAT DEFAULT 0.0"

    # String / Text Types
    short_string_cols = {
        "job_id", "country", "normalized_country", "experience_level",
        "work_mode", "category", "job_type", "source_api", "phone",
        "location", "seniority_level", "primary_domain", "email",
        "candidate_name", "target_domain", "seniority_assessment",
        "source_cv", "source_filename", "name", "name_lower", "source_name",
        "status", "posted_at", "created_at", "updated_at", "run_at"
    }

    medium_string_cols = {"title", "headline", "company", "job_title"}

    if col_name_lower in short_string_cols:
        return "NVARCHAR(255) DEFAULT N''"
    elif col_name_lower in medium_string_cols:
        return "NVARCHAR(500) DEFAULT N''"
    else:
        return "NVARCHAR(MAX) DEFAULT N''"


def generate_sqlserver_script(
    sqlite_db_path: str,
    output_sql_path: str,
    db_name: str = "CareerAI"
) -> str:
    """Dynamically reads all SQLite tables and generates a full T-SQL script for SSMS."""
    if not os.path.exists(sqlite_db_path):
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_db_path}")

    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get non-internal tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'jobs_fts%' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]

    # Reorder tables so dependencies (like reports before report_evaluations) come first
    priority_order = ["candidates", "reports", "skills", "scrape_runs", "jobs", "report_evaluations", "job_skills", "partition_summaries"]
    ordered_tables = [t for t in priority_order if t in tables]
    for t in tables:
        if t not in ordered_tables:
            ordered_tables.append(t)

    lines = []
    lines.append(f"""-- =============================================================================
-- CareerAI Master Microsoft SQL Server Setup & Data Migration Script
-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Ready to run directly in SQL Server Management Studio (SSMS) [Press F5]
-- =============================================================================

USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db_name}')
BEGIN
    CREATE DATABASE [{db_name}];
    PRINT '✅ Database [{db_name}] created successfully.';
END
GO

USE [{db_name}];
GO
""")

    print(f"📦 Extracting tables and schemas from SQLite: {sqlite_db_path}")

    # Build CREATE TABLE statements
    for table in ordered_tables:
        cols_info = cur.execute(f"PRAGMA table_info({table})").fetchall()
        col_defs = []
        has_id_pk = False

        for c in cols_info:
            cid, col_name, col_type, notnull, dflt_val, pk = c
            is_pk = bool(pk)
            if is_pk and col_name.lower() == "id":
                has_id_pk = True
            tsql_type = map_sqlite_to_tsql_type(col_name, col_type, is_pk)
            col_defs.append(f"    [{col_name}] {tsql_type}")

        # Add foreign key constraints if applicable
        if table == "report_evaluations":
            col_defs.append("    CONSTRAINT FK_evaluations_report FOREIGN KEY ([report_id]) REFERENCES dbo.[reports](id) ON DELETE CASCADE")

        create_tbl_sql = (
            f"-- Table: dbo.[{table}]\n"
            f"IF OBJECT_ID(N'dbo.[{table}]', N'U') IS NULL\n"
            f"BEGIN\n"
            f"    CREATE TABLE dbo.[{table}] (\n"
            + ",\n".join(col_defs) +
            f"\n    );\n"
            f"    PRINT '✅ Table dbo.[{table}] created.';\n"
            f"END\nGO\n"
        )
        lines.append(create_tbl_sql)

    # Add useful indexes
    lines.append("""-- Indexes for high-speed querying in SQL Server
IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = N'idx_jobs_country')
    CREATE INDEX idx_jobs_country ON dbo.[jobs](country);
IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = N'idx_jobs_is_remote')
    CREATE INDEX idx_jobs_is_remote ON dbo.[jobs](is_remote);
IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = N'idx_jobs_company')
    CREATE INDEX idx_jobs_company ON dbo.[jobs](company);
IF NOT EXISTS (SELECT name FROM sys.indexes WHERE name = N'idx_eval_match')
    CREATE INDEX idx_eval_match ON dbo.[report_evaluations](agent_match_score);
GO
""")

    # Populate Data Table by Table
    for table in ordered_tables:
        cols_info = cur.execute(f"PRAGMA table_info({table})").fetchall()
        col_names = [c[1] for c in cols_info]
        has_id_pk = any(c[5] and c[1].lower() == "id" for c in cols_info)

        rows = cur.execute(f"SELECT * FROM [{table}]").fetchall()
        if not rows:
            continue

        print(f"📊 Transferring {len(rows):>4} records from table [{table}]...")
        lines.append(f"-- ===========================================================================")
        lines.append(f"-- INSERT DATA: dbo.[{table}] ({len(rows)} rows)")
        lines.append(f"-- ===========================================================================")

        if has_id_pk:
            lines.append(f"SET IDENTITY_INSERT dbo.[{table}] ON;\nGO")

        col_list_str = ", ".join(f"[{c}]" for c in col_names)
        batch_size = 150

        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i + batch_size]
            lines.append(f"INSERT INTO dbo.[{table}] ({col_list_str})\nVALUES")
            chunk_vals = []
            for r in chunk:
                row_vals = ", ".join(escape_tsql_val(r[col]) for col in col_names)
                chunk_vals.append(f"({row_vals})")
            lines.append(",\n".join(chunk_vals) + ";\nGO\n")

        if has_id_pk:
            lines.append(f"SET IDENTITY_INSERT dbo.[{table}] OFF;\nGO\n")

    lines.append("""PRINT '🎉 CONGRATULATIONS! Entire CareerAI database is successfully loaded in Microsoft SQL Server!';
PRINT '💡 Try running: SELECT TOP 10 * FROM dbo.[jobs] ORDER BY id;';
""")

    conn.close()

    # Save to disk
    os.makedirs(os.path.dirname(os.path.abspath(output_sql_path)), exist_ok=True)
    with open(output_sql_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    file_size_mb = round(os.path.getsize(output_sql_path) / (1024 * 1024), 2)
    print(f"\n✅ Standalone T-SQL Script Ready: {output_sql_path} ({file_size_mb} MB)")
    return output_sql_path


def direct_push_to_sqlserver(
    sqlite_db_path: str,
    server: str = "localhost",
    db_name: str = "CareerAI",
    trusted_connection: bool = True,
    username: str = None,
    password: str = None
) -> bool:
    """Connects to SQL Server instance and executes the migration directly."""
    import pyodbc

    print(f"\n🔌 Connecting to Microsoft SQL Server instance on [{server}]...")

    if trusted_connection:
        master_conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes;TrustServerCertificate=yes;"
    else:
        master_conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE=master;UID={username};PWD={password};TrustServerCertificate=yes;"

    try:
        conn_master = pyodbc.connect(master_conn_str, autocommit=True)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Hint: Ensure Microsoft SQL Server service (MSSQLSERVER or SQLEXPRESS) is started.")
        return False

    cur_master = conn_master.cursor()
    cur_master.execute(f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'{db_name}') CREATE DATABASE [{db_name}];")
    cur_master.close()
    conn_master.close()
    print(f"✅ Database [{db_name}] confirmed on SQL Server.")

    if trusted_connection:
        target_conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db_name};Trusted_Connection=yes;TrustServerCertificate=yes;"
    else:
        target_conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={db_name};UID={username};PWD={password};TrustServerCertificate=yes;"

    conn_target = pyodbc.connect(target_conn_str, autocommit=True)
    cur = conn_target.cursor()

    temp_sql = os.path.join(project_root, "data", "database", "CareerAI_SqlServer_Setup.sql")
    generate_sqlserver_script(sqlite_db_path, temp_sql, db_name=db_name)

    print(f"🚀 Streaming batches to Microsoft SQL Server [{server}]...")
    with open(temp_sql, "r", encoding="utf-8") as f:
        batches = f.read().split("GO\n")

    success_count = 0
    for b in batches:
        b_clean = b.strip()
        if not b_clean:
            continue
        if b_clean.startswith("USE ") or b_clean.startswith("CREATE DATABASE") or b_clean.startswith("IF NOT EXISTS (SELECT name FROM sys.databases"):
            continue
        try:
            cur.execute(b_clean)
            success_count += 1
        except Exception as e:
            if "already an object" not in str(e):
                print(f"⚠️ Batch notice: {str(e)[:80]}")

    cur.close()
    conn_target.close()
    print(f"🎉 SUCCESS! Migrated {success_count} batches directly into SQL Server [{server}].[{db_name}]!\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="Export SQLite to Microsoft SQL Server")
    parser.add_argument("--server", type=str, default=None, help="SQL Server instance name (e.g. localhost, .\\SQLEXPRESS)")
    parser.add_argument("--database", type=str, default="CareerAI", help="Target database name (default: CareerAI)")
    parser.add_argument("--output", type=str, default=None, help="Output .sql file path")

    args = parser.parse_args()

    sqlite_db = os.path.join(project_root, "data", "processed", "jobs.db")
    sql_out = args.output or os.path.join(project_root, "data", "database", "CareerAI_SqlServer_Setup.sql")

    if args.server:
        direct_push_to_sqlserver(sqlite_db, server=args.server, db_name=args.database)
    else:
        generate_sqlserver_script(sqlite_db, sql_out, db_name=args.database)
        print(f"\n" + "=" * 75)
        print(f"📁 T-SQL SCRIPT READY TO OPEN IN SSMS:")
        print(f"  Path: {sql_out}")
        print(f"=" * 75)


if __name__ == "__main__":
    main()
