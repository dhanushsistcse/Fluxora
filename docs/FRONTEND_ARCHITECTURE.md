# Frontend architecture

## Current state

This repository was empty at inspection. The frontend is a React + TypeScript SPA scaffolded for Vite. No prior routing, design system, API integration, state management, tests, or responsive behavior existed to preserve. Navigation is currently an accessible client-side section switcher; a routing library can be added if deep links become part of the product requirements.

## Structure

- `src/App.tsx` — shell, navigation, converter interaction, and section views.
- `src/styles.css` — responsive design tokens, component styles, light/dark themes, and reduced-motion handling.
- `src/services/api.ts` — contract-first API boundary; it intentionally fails closed until wired to the backend contract.
- `src/test/` — test setup; component and API-boundary tests live beside source.
- `docs/` — frontend API, component, and testing notes.

## State and data

UI navigation, theme, selected local files, target format, and quality preference are held in React component state. Selected `File` values remain in browser memory until a future API adapter is implemented. No job list, progress, conversion result, authentication state, or server capability is fabricated.

## Design and accessibility

The layout supports desktop and mobile breakpoints, keyboard navigation for file drop/pick, labelled form controls, visible focus states, reduced motion, and a user-controlled light/dark theme. The theme toggle is local and is not persisted. No editor library has been selected because the backend's document editing capabilities and supported formats are unknown.

## Required next step

Wire the API adapter to `docs/BACKEND_API_CONTRACT.md`, then implement supported-format discovery, authentication configuration, upload limits, conversion/job lifecycle, file downloads, and only the documented PDF operations. Job history, retries, workflow persistence/execution, DOCX editing, OCR, DOCX-to-PDF, and broad media/archive operations remain unavailable according to the contract.
