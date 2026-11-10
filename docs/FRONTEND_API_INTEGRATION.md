# Frontend API integration

## Status: contract available; adapter not yet wired

The contract is present at `docs/BACKEND_API_CONTRACT.md` on the Agent 1 branch. The current UI adapter in `src/services/api.ts` still rejects requests with `BackendContractUnavailableError`; it does not send files or generate a conversion result. This is intentionally not presented as completed backend integration.

## Contract capabilities and limitations

The documented v1 API includes bearer-token authentication, health and format/engine discovery, uploads capped at 50 MiB by default, conversion submission, job inspection/cancellation, owned file inspection/download, and a set of synchronous PDF operations. Current conversion support is limited to Pillow still-image conversion pairs advertised by `/api/v1/formats`.

The contract does not document job listing/history, retry, workflow persistence/validation/execution, batch conversion, DOCX editing/merge/split, PDF rendering, OCR, DOCX-to-PDF, or media transcoding beyond supported still images. Do not expose those as working features. Authentication is a configured single bearer token in the current starter; protected APIs fail closed when no token is configured.

## Integration principles

Implement a typed adapter and verify every request and response against the contract. Use real server capability responses for supported-format discovery. Do not display fake progress; use documented job states/status only. Preserve authorization on file inspection and downloads. Surface API errors clearly. Do not log file contents, credentials, or tokens. Keep operation controls disabled until the corresponding operation is wired and verified. Do not claim expiry, retries, or history support without a documented API.
