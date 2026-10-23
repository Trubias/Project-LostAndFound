import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Findly — Lost & Found, together',
  description: 'A thoughtful campus lost and found. Report missing belongings, browse found items, and reunite with what matters.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
