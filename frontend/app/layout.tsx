import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MSME PayGuard",
  description: "Every invoice tracked. Every payment protected.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
