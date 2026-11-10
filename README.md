# Fluxora
Fluxora is a powerful, privacy-first universal file processing platform designed to convert, compress, edit, and manage files across multiple formats with speed, security, and seamless workflows.

## Frontend

The React + TypeScript frontend lives at the repository root and is built with Vite. It currently provides the Universal File Studio dashboard, responsive navigation and themes, local file selection/inspection, and truthful unavailable states for backend-dependent operations.

The backend contract is available at `docs/BACKEND_API_CONTRACT.md`, but the frontend API adapter is not yet wired to it. Conversion submission intentionally fails closed; no file upload, job, progress, or result is simulated.

### Frontend commands

- `npm install` — install frontend dependencies.
- `npm run dev` — start the Vite development server.
- `npm test` — run Vitest tests.
- `npm run build` — type-check and create the production build.

### Frontend documentation

- `docs/FRONTEND_ARCHITECTURE.md`
- `docs/UI_COMPONENTS.md`
- `docs/FRONTEND_API_INTEGRATION.md`
- `docs/FRONTEND_TESTING.md`
