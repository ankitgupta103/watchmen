export const API_PROXY_URL =
  process.env.NEXT_PUBLIC_API_PROXY_URL || 'http://localhost:3000';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_ENVIRONMENT === 'development'
    ? process.env.NEXT_PUBLIC_API_BASE_URL_LOCAL
    : process.env.NEXT_PUBLIC_API_BASE_URL;

export const MAPS_API_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export const TOKEN_KEY = 'token';
