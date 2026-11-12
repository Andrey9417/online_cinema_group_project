# Online Cinema

FastAPI + async SQLAlchemy + Alembic + PostgreSQL, run in Docker, dependencies managed with Poetry.

## 1. Local setup (for the IDE, so there are no import errors)

Requires Python 3.14 and Docker Desktop.

```bash
# 1. clone repo from develop branch (https://github.com/Andrey9417/online_cinema_group_project/tree/develop)
git clone <repo-url>
cd online_cinema_group_project

# 2. add venv
python -m venv .venv
```

Activate the venv:
- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Linux / macOS: `source .venv/bin/activate`

```bash
pip install poetry
poetry install
```

## 2. Create `.env`

Copy `.env.example` to `.env` (fill in values if needed):


## 3. Run the project

```bash
docker compose up --build
```

Migrations are applied automatically on start. The app is available at http://localhost:8000/docs.

Useful commands:
- `docker compose logs -f web` - app logs
- `docker compose down` - stop everything
- `docker compose down -v` - stop everything and delete the database

After adding a dependency (`poetry add ...`), run `docker compose up  --build` again.

## 4. Add a new migration

1. Change or add models in `src/database/models/`. A new model must be imported in `src/database/models/__init__.py`. (to be seen by alembic)
2. Make sure the containers are running, then generate the migration:
   ```bash
   docker compose exec web alembic revision --autogenerate -m "short description"
   ```
3. Check the new file in `src/migrations/versions/`.
4. Apply it by restarting docker or upgrading head:

Pull the latest changes before creating a migration. Two people creating migrations from the same base cause a "multiple heads" error.

## 5. Connect to the database in PyCharm

The containers must be running.

1. Database tool window, `+`, Data Source, PostgreSQL.
2. Fill in:
   - Host: `localhost` (not `postgres_db`)
   - Port: `5432`
   - User, Password, Database: values from `.env`
3. Test Connection, then OK.


## 6. Project structure

```
.
├── docker-compose.yml
├── Dockerfile
├── alembic.ini                  # Alembic config (script_location = src/migrations)
├── pyproject.toml / poetry.lock # dependencies
├── .env / .env.example
└── src/
    ├── main.py                  # FastAPI app
    ├── config/settings.py       # settings read from environment variables
    ├── database/
    │   ├── base.py              # declarative Base shared by all models
    │   ├── session.py           # async engine, session factory, get_db_session dependency
    │   └── models/              # SQLAlchemy models
    ├── migrations/              # Alembic (env.py, versions/)
    ├── routes/                  # API routers
    ├── schemas/                 # Pydantic schemas
    └── crud/                    # database operations
```
