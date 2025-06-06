import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';

import './globals.css';

import { Toaster } from '@/components/ui/sonner';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'VyomOS Netrajaal',
  icons: {
    icon: '/assets/png/vyomos-logo-filled.png',
  },
  description: 'Stupidly smart fleet management',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} relative antialiased`}
        cz-shortcut-listen="true"
      >
        <main className="bg-accent h-screen w-full">{children}</main>
        <Toaster />
      </body>
    </html>
  );
}
