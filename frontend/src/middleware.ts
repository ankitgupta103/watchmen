import { NextRequest, NextResponse } from 'next/server';

// import { Organization } from './lib/types/organization';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isLoggedIn =
    request.cookies.get('sessionId') && request.cookies.get('token');
  // const { permissions } = JSON.parse(
  //   request.cookies.get('organization')?.value || '{}',
  // ) as Organization;

  console.log('Middleware is running', pathname);

  if (!isLoggedIn) {
    console.log('Redirecting to logout');
    return NextResponse.redirect(new URL('/auth/logout', request.url));
  }

  // Check if the user has the permission to access the page
  // const routeSegment = pathname.split('/')[1];
  // const hasPermission = permissions.some(
  //   (perm) => perm.includes(routeSegment) || routeSegment.includes(perm),
  // );
  // if (!hasPermission) {
  //   console.log('Redirecting to logout');
  //   return NextResponse.redirect(new URL('/auth/logout', request.url));
  // }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/map-view/:path*',
    '/projects/:path*',
    '/missions/:path*',
    '/devices/:path*',
  ],
};
