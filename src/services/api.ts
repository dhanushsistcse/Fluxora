export type ConversionRequest = {
  files: File[]
  targetFormat: string
  quality: string
}

export class BackendContractUnavailableError extends Error {
  constructor(message = 'Backend API integration is not configured. No files were uploaded and no conversion was started.') {
    super(message)
    this.name = 'BackendContractUnavailableError'
  }
}

/**
 * Contract-first API boundary. Do not add URLs or infer endpoint shapes here.
 * Replace this adapter only after docs/BACKEND_API_CONTRACT.md is provided.
 */
export const api = {
  async createConversionJob(_request: ConversionRequest): Promise<never> {
    throw new BackendContractUnavailableError()
  },
}
