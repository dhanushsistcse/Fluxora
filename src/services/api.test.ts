import { describe, expect, it } from 'vitest'
import { api, BackendContractUnavailableError } from './api'

describe('API boundary', () => {
  it('fails closed until the documented backend contract is available', async () => {
    await expect(api.createConversionJob({ files: [], targetFormat: 'PDF', quality: 'Balanced' }))
      .rejects.toBeInstanceOf(BackendContractUnavailableError)
  })
})
