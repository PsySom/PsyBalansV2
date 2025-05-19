# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run server: `uvicorn app.main:app --reload` (Windows: `run.bat`, Linux: `run.sh`)
- Database health check: `GET /api/status` endpoint
- Lint code: `flake8 app/`
- Type check: `mypy app/`
- Run tests: `pytest` or `pytest -v` for verbose output
- Run single test: `pytest app/tests/test_file.py::test_function`
- Apply migrations: `./migrations.py upgrade` or `alembic upgrade head`
- Create migration: `./migrations.py create --name "description" --autogenerate`
- Check migrations: `./migrations.py history` or `./migrations.py current`
- Preview migrations: `./migrations.py check`
- Create indexes: `./migrations.py create_indexes`

## Code Style Guidelines
- **Imports**: Group imports by standard library, third-party, and local imports with blank lines in between
- **Formatting**: Use 4-space indentation, 88 character line limit
- **Types**: Use type annotations for function parameters and return values
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Error Handling**: Use custom exceptions or FastAPI HTTPException with appropriate status codes
- **Documentation**: Use docstrings for functions and classes (Russian comments are used in some files)
- **Async**: Use async/await for database operations and API endpoints
- **Modules**: Organize code into modules with models, schemas, services, and routes
- **Tests**: Write unit tests for models and services, use fixtures for test data

## Architecture
- **Database**: Polyglot persistence using PostgreSQL (SQLAlchemy), MongoDB, and Redis
- **API**: FastAPI with prefix "/api" for all routes
- **Structure**: Layered architecture with API, service, repository, and model layers
- **Auth**: JWT authentication with password hashing via passlib/bcrypt
- **Async**: Asynchronous processing throughout the application
- **Resilience**: Circuit breaker pattern, retry mechanism with exponential backoff
- **Logging**: Comprehensive context-based logging system using JSON format