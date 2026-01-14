import type { Metadata } from "next";
import { Inter, Inclusive_Sans, PT_Serif } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const inclusiveSans = Inclusive_Sans({
  weight: "400",
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inclusive",
});

const ptSerif = PT_Serif({
  weight: "700",
  style: "italic",
  subsets: ["latin"],
  display: "swap",
  variable: "--font-pt-serif",
});

export const metadata: Metadata = {
  title: "ECE 350 Assistant",
  description:
    "RAG-powered assistant for ECE 350 Operating Systems lecture material",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${inclusiveSans.variable} ${ptSerif.variable} font-sans antialiased bg-background text-foreground`}
      >
        {children}
      </body>
    </html>
  );
}
