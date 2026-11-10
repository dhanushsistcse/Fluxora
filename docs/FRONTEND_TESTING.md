# Frontend testing

## Commands

- `npm test` — run Vitest component and service tests.
- `npm run build` — type-check and create the Vite production build.

## Current coverage

- Dashboard and primary module navigation render.
- A local file can be selected and appears in the converter.
- Conversion is disabled before file selection and fails closed because the API adapter is not yet wired.
- Job history shows a real empty state rather than invented jobs.
- Theme toggle exposes an accessible name and updates the theme.
- Mobile navigation opens from its labelled control.
- API boundary rejects until backend integration is implemented.

## Follow-up coverage after API integration

Add service-level request/response tests for upload, progress/status, cancel, retry, discovery, and authorized downloads; upload limit and validation tests; job-state transition tests; workflow validation/execution tests; responsive viewport checks; axe accessibility checks; and end-to-end flows against an isolated test backend. Never assert simulated conversion results as backend integration.
