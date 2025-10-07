// src/app/layout.js
import { Inter } from 'next/font/google';
import './globals.css';

// Configure the Inter font
const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: "Magento AI Operator",
  description: "Admin panel for Magento AI Operator",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      {/* Apply the font class to the body */}
      <body className={inter.className}>{children}</body>
    </html>
  );
}