import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Incident Triage",
  description: "Modular incident triage agent pipeline",
};

function Footer() {
  const sha = process.env.NEXT_PUBLIC_COMMIT_SHA || 'dev';
  const message = process.env.NEXT_PUBLIC_COMMIT_MESSAGE || 'local';
  const shortSha = sha.slice(0, 7);

  return (
    <footer style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      padding: '8px 16px',
      fontSize: '11px',
      color: '#666',
      backgroundColor: '#f5f5f5',
      borderTop: '1px solid #e0e0e0',
      fontFamily: 'monospace',
    }}>
      <code>{shortSha}</code>: {message.slice(0, 80)}{message.length > 80 ? '...' : ''}
    </footer>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ paddingBottom: '40px' }}>
        {children}
        <Footer />
      </body>
    </html>
  );
}
