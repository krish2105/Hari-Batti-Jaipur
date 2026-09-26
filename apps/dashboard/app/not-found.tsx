// 404 page in the dashboard's own colours.
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center p-6 text-center">
      <div>
        <p className="led text-6xl text-[#ffb020]">404</p>
        <p className="muted mt-3">This page does not exist. · यह पेज मौजूद नहीं है।</p>
        <Link href="/" className="btn mt-5">Signal Command</Link>
      </div>
    </main>
  );
}
