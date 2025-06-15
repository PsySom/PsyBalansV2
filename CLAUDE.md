# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Backend Commands
- Run server: `uvicorn app.main:app --reload` (Windows: `run.bat`, Linux: `run.sh`)
- Run tests: `pytest` or `pytest -v` for verbose output
- Run single test: `pytest app/tests/test_file.py::test_function` 
- Run specific test file: `pytest app/tests/test_file.py`
- Run test class: `pytest app/tests/test_file.py::TestClassName`
- Run tests with markers: `pytest -m not slow`
- Apply migrations: `alembic upgrade head` or `python migrations.py upgrade`
- Create migration: `alembic revision --autogenerate -m "description"`
- Seed database: `python seed_*.py` (run in order: types → subtypes → activities → needs → links)
- Type checking: `mypy app/` (install with `pip install mypy`)
- Linting: `flake8 app/` (install with `pip install flake8`)
- Debug: `python -m pdb app/file.py`

## Frontend Commands
- Start development: `cd frontend && npm run dev`
- Build for production: `cd frontend && npm run build`
- Run linting: `cd frontend && npm run lint`
- Run tests: `cd frontend && npm run test` or `npm run test:watch` for watch mode
- Run single test: `cd frontend && npm run test -- filename.test.ts`
- Run test coverage: `cd frontend && npm run coverage`
- Preview build: `cd frontend && npm run preview`
- Type check: `cd frontend && tsc -b`

## Code Style Guidelines
- **Imports**: Group by standard library, third-party, local imports with blank lines between
- **Formatting**: Backend: 4-space indentation, 88 char line limit; Frontend: 2-space indentation
- **Types**: Python type annotations (Pydantic 2.0+) and TypeScript 5.0+ strict mode required
- **Naming**: snake_case (Python), camelCase (JS/TS), PascalCase (React components), ALL_CAPS (constants)
- **Error Handling**: Use custom exceptions from app.core.exceptions or FastAPI HTTPException
- **Documentation**: Docstrings for all functions, classes, and modules (Russian is acceptable)
- **Async**: Use async/await for database operations and API endpoints
- **Testing**: pytest with parametrize for backend; Vitest for frontend
- **Logging**: Always use context logging via `app.core.logging.context_logger.ContextLogger`
- **Git**: Branch naming: feature/, bugfix/, refactor/, docs/; use present tense verbs in commit messages
- **React Components**: Prefer functional components with hooks; avoid class components
- **TypeScript**: Use strict mode with noUnusedLocals, noUnusedParameters, and noUncheckedSideEffectImports

## Architecture
- **Backend**: FastAPI with PostgreSQL (SQLAlchemy 2.0+ ORM), MongoDB, and Redis
- **Frontend**: React 18+ with TypeScript, Vite, Chakra UI, and Zustand for state management
- **UI Components**: Chakra UI with Framer Motion for animations and Swiper for carousels
- **API**: RESTful with prefix "/api" for all routes
- **Database**: Repository pattern with typed models and BaseRepository
- **Auth**: JWT authentication with password hashing via passlib/bcrypt
- **Resilience**: Circuit breaker pattern and retry mechanism for robust error handling
- **Environment**: Use .env files for configuration variables (see .env.example)

## Common Issues & Solutions
- React Router config warnings: Use `future` configuration in router-config.ts
- Keyframes import: Import from `@emotion/react` not `@chakra-ui/react`
- Database seeding: Run seeders in order (types → subtypes → activities → needs → links)
- CSS animations: Use `as` prop with Emotion's keyframes for Chakra UI components
- Repository pattern: Extend from BaseRepository for consistent data access methods
- TypeScript errors: Check tsconfig.app.json for strict configuration settings
- MongoDB repositories: Follow the pattern in app/mongodb/ for document schemas