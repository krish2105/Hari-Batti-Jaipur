// "/" is handled by middleware.ts (redirects to /en or /hi); this is only a fallback.
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/en");
}
