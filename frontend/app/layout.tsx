import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { Providers } from "@/providers";
import "./globals.css";

/** Interface typeface: precise, compact, excellent tabular figures. */
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

/** Identifiers only (student IDs, receipt numbers, references). */
const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

/** Editorial display face, reserved for marketing headlines. */
const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: {
    template: "%s | Brightway Computer Academy",
    default: "Brightway Computer Academy",
  },
  description:
    "Computer courses with practical lab hours, recognised certificates, and a student portal for fees, receipts and attendance.",
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-white text-ink font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
