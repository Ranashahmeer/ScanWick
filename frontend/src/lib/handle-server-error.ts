import { AxiosError } from 'axios'
import { toast } from 'sonner'

export function handleServerError(error: unknown) {
  // Log only safe, non-sensitive fields — never the full error object, which
  // for an AxiosError includes `config.headers.Authorization: Bearer <token>`.
  // eslint-disable-next-line no-console
  console.error('Request failed', {
    message: error instanceof Error ? error.message : String(error),
    status: error instanceof AxiosError ? error.response?.status : undefined,
    url: error instanceof AxiosError ? error.config?.url : undefined,
  })

  let errMsg = 'Something went wrong!'

  if (error instanceof AxiosError) {
    if (!error.response) {
      // No response at all means the request never completed — offline,
      // DNS failure, CORS rejection, or the backend being down — as opposed
      // to a server error response with a body.
      errMsg = 'Network error — please check your connection.'
    } else {
      const detail = error.response.data?.detail
      if (typeof detail === 'string' && detail.length > 0) {
        errMsg = detail
      }
    }
  }

  toast.error(errMsg)
}
