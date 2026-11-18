/** Custom hook for managing and formatting API errors across the frontend. */

import { useCallback, useState } from 'react';
import { ApiClientError } from '../types/api';

export interface UseApiErrorReturn {
  error: ApiClientError | Error | null;
  errorMessage: string | null;
  errorCode: string | null;
  setError: (_err: unknown) => void;
  clearError: () => void;
}

export function useApiError(): UseApiErrorReturn {
  const [error, setRawError] = useState<ApiClientError | Error | null>(null);

  const setError = useCallback((err: unknown) => {
    if (err instanceof ApiClientError || err instanceof Error) {
      setRawError(err);
    } else if (typeof err === 'string') {
      setRawError(new Error(err));
    } else {
      setRawError(new Error('An unexpected error occurred.'));
    }
  }, []);

  const clearError = useCallback(() => {
    setRawError(null);
  }, []);

  const errorMessage = error ? error.message : null;
  const errorCode = error instanceof ApiClientError ? error.error : null;

  return {
    error,
    errorMessage,
    errorCode,
    setError,
    clearError,
  };
}

export default useApiError;
