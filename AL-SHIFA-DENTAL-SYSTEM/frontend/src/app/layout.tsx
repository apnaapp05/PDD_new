

import "./globals.css";





export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="app-root">
      <div className="app-body">
        {children}
      </div>
    </div>
  );
}
