// Locale routing: "/" goes to /en or /hi (browser language). Every other request carries its
// locale in a header so the root layout can set <html lang> correctly for Hindi fonts and screen readers.
import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const first = req.nextUrl.pathname.split("/")[1];
  if (req.nextUrl.pathname === "/") {
    const lang = req.headers.get("accept-language") ?? "";
    const locale = /^hi\b|,\s*hi\b/i.test(lang) ? "hi" : "en";
    return NextResponse.redirect(new URL(`/${locale}${req.nextUrl.search}`, req.url));
  }
  const headers = new Headers(req.headers);
  headers.set("x-hb-locale", first === "hi" ? "hi" : "en");
  return NextResponse.next({ request: { headers } });
}

export const config = { matcher: ["/((?!_next|favicon|icon|.*\\.).*)"] };
