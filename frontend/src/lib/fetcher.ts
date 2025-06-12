import { getToken } from './auth/getToken';

/**
 * HTTP methods supported by the fetcher utility.
 */
export type FetchMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

/**
 * Options for configuring the fetcher utility.
 *
 * @template T - The type of the request body.
 * @property {FetchMethod} [method] - The HTTP method to use (default is 'GET').
 * @property {T} [body] - The request payload to send (for POST/PUT requests).
 * @property {HeadersInit} [headers] - Additional headers to include in the request.
 */
export interface FetchOptions<T = unknown> {
  method?: FetchMethod;
  body?: T;
  headers?: HeadersInit;
}

/**
 * A generic fetch utility that handles authentication and JSON serialization.
 *
 * @template TResponse - The expected response type.
 * @template TRequest - The request body type.
 * @param {string} url - The endpoint URL to fetch.
 * @param {FetchOptions<TRequest>} [options] - Optional fetch configuration.
 * @returns {Promise<TResponse>} - The parsed JSON response.
 * @throws {Error} - Throws if the fetch fails or the response is not ok.
 */
export async function fetcher<TResponse = unknown, TRequest = unknown>(
  url: string,
  options?: FetchOptions<TRequest>,
): Promise<TResponse> {
  const token = await getToken();
  const { method = 'GET', body, headers } = options || {};

  try {
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Token ${token}`,
        ...(headers || {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.ok) {
      return res.json() as Promise<TResponse>;
    }

    return {
      status: res.status,
      data: null,
    } as TResponse
  } catch (error: unknown) {
    if (error instanceof Error) {
      console.error('Error fetching data:', error.message);
    } else {
      console.error('Error fetching data:', error);
    }

    return {
      status: 500,
      data: null,
    } as TResponse;
  }
}
