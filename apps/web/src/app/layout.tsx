import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Incident Triage",
  description: "Modular incident triage agent pipeline",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
