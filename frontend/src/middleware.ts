import { NextRequest, NextResponse } from "next/server";

const AUTH_PAGES = ["/login", "/register"];

export function middleware(req: NextRequest) {
  const hasSession = req.cookies.has("access_token");
  const isAuthPage = AUTH_PAGES.includes(req.nextUrl.pathname);

  if (!hasSession && !isAuthPage) {
    return NextResponse.redirect(new URL("/login", req.url));
  }
  if (hasSession && isAuthPage) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico).*)"],
};
