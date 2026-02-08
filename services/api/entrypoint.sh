#!/bin/bash
set -e

echo "Running database migrations..."

# Run all migration files in order
for migration in /app/services/api/migrations/*.sql; do
    if [ -f "$migration" ]; then
        echo "Applying: $(basename $migration)"
        python3 -c "
import os
from sqlalchemy import create_engine, text

database_url = os.environ.get('DATABASE_URL', 'sqlite:///./local.db')
# Railway uses postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(database_url)
with open('$migration', 'r') as f:
    sql = f.read()

with engine.begin() as conn:
    # Split by semicolon and execute each statement
    for statement in sql.split(';'):
        statement = statement.strip()
        if statement:
            try:
                conn.execute(text(statement))
            except Exception as e:
                # Ignore 'already exists' errors
                if 'already exists' not in str(e).lower():
                    print(f'Warning: {e}')
print('Migration applied successfully')
"
    fi
done

echo "Migrations complete. Starting API..."

# Start the API
exec uvicorn services.api.src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
