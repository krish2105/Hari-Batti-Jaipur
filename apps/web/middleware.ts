// Send "/" to /en or /hi (browser language), so every page has a real locale in its URL.
import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const lang = req.headers.get("accept-language") ?? "";
  const locale = /^hi\b|,\s*hi\b/i.test(lang) ? "hi" : "en";
  return NextResponse.redirect(new URL(`/${locale}${req.nextUrl.search}`, req.url));
}

export const config = { matcher: ["/"], runtime: "nodejs" };
