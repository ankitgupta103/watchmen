import { FetchOptions } from './fetcher';

/**
 * Makes an HTTP request to the specified URL using the Fetch API on the client side.
 *
 * @template TResponse - The expected response type.
 * @template TRequest - The request body type (if any).
 * @param {string} url - The endpoint URL to send the request to.
 * @param {string} token - The authentication token to include in the Authorization header.
 * @param {FetchOptions<TRequest>} [options] - Optional fetch options including method, body, and headers.
 * @returns {Promise<TResponse>} - A promise that resolves to the response data of type TResponse.
 * @throws {Error} - Throws an error if the fetch fails or the response is not ok.
 *
 * @example
 * // Example usage:
 * const data = await fetcherClient<MyResponseType, MyRequestType>(
 *   '/api/data',
 *   'my-auth-token',
 *   { method: 'POST', body: { foo: 'bar' } }
 * );
 */
export async function fetcherClient<TResponse = unknown, TRequest = unknown>(
  url: string,
  token: string,
  options?: FetchOptions<TRequest>,
): Promise<TResponse | undefined> {
  const { method = 'GET', body, headers, signal } = options || {};

  try {
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Token ${token}`,
        ...(headers || {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });

    if (res.ok) {
      return res.json() as Promise<TResponse>;
    } else {
      const errorText = await res.text();
      throw new Error(
        `HTTP ${res.status}: ${res.statusText}${errorText ? ` - ${errorText}` : ''}`,
      );
    }
  } catch (error: unknown) {
    if (error instanceof Error) {
      console.error('Error fetching data:', error.message);
    } else {
      console.error('Error fetching data:', error);
    }
    throw error;
  }
}
