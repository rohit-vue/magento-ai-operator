// src/app/layout.js
import './globals.css';

export const metadata = {
  title: "Magento AI Operator",
  description: "Admin panel for Magento AI Operator",
};

export default function RootLayout({ children }) {
  return (
    // By adding suppressHydrationWarning here, we tell React to ignore
    // mismatches caused by browser extensions on this element and its children (like <body>).
    <html lang="en" suppressHydrationWarning={true}>
      <body>{children}</body>
    </html>
  );
}