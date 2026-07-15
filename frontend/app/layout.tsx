import type { Metadata } from 'next';
import './globals.css';
import { SessionProvider } from '@/components/SessionProvider';
import { ThemeProvider } from '@/lib/theme';
import { CurrencyProvider } from '@/lib/currency';
import { AppShell } from '@/components/AppShell';

export const metadata: Metadata = {
  title: 'Where Is My Money Going',
  description: 'Personal finance tracker - analyze your bank statements and track spending',
  icons: {
    icon: '/icon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-900 text-white antialiased">
        <ThemeProvider>
          <CurrencyProvider>
            <SessionProvider>
              <AppShell>{children}</AppShell>
            </SessionProvider>
          </CurrencyProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
