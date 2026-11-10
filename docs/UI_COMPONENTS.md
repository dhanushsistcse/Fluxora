# UI components

The current application uses small, local React views rather than a third-party component framework.

- **Sidebar / top bar** — switch product areas, show the disconnected API state, and toggle theme.
- **Universal converter** — multiple local file selection, keyboard-operable drop zone, browser-side extension/MIME detection, source summary, target and quality controls, and a submit action that fails closed while no contract is available. The target list is a UI selection only, not a claim of backend support.
- **Tool panel** — lists requested PDF, document, media, archive, compression, batch, and workflow operations. Configuration is disabled until documented backend support exists.
- **Job history** — truthful empty state; no synthetic jobs or progress.
- **File inspector** — displays only local browser file name, size, detected extension, and modification date.
- **Security & Privacy** — explicitly marks undocumented service behavior as unknown.

Shared CSS uses CSS variables for colors and includes light and dark states. Icons currently use typographic glyphs; replace with a consistent icon set if one is selected for production. All disabled controls explain that backend integration is required.
