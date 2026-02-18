import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  weight: ['400', '500', '600', '700', '900'],
});

export const metadata: Metadata = {
  title: "PratikoAI - L'assistente IA per le normative italiane",
  description:
    "L'assistente IA che legge le circolari per te. Risparmia 10+ ore a settimana con risposte istantanee su tasse e normative italiane.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <body className={`${inter.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

// instrument-apiClient.ts (import it once in your client entry)
declare global {
  interface Window {
    __STREAM_REQ_SEQ__?: number;
  }
}

if (typeof window !== 'undefined') {
  try {
    const anyClient: any = (await import('../lib/api')).apiClient;
    if (anyClient && typeof anyClient.sendChatMessageStreaming === 'function') {
      const original = anyClient.sendChatMessageStreaming.bind(anyClient);
      anyClient.sendChatMessageStreaming = async (
        messages: any[],
        onChunk: any,
        onDone: any,
        onError: any
      ) => {
        window.__STREAM_REQ_SEQ__ = (window.__STREAM_REQ_SEQ__ || 0) + 1;
        const reqId = window.__STREAM_REQ_SEQ__;
        const stack =
          new Error().stack?.split('\n').slice(1, 5).join('\n') || '(no stack)';
        console.log(
          `[SSTRM req:${reqId}] BEGIN messages=${messages?.length}\n${stack}`
        );

        let chunkCount = 0;
        const wrappedOnChunk = (c: string) => {
          chunkCount++;
          console.log(
            `[SSTRM req:${reqId}] chunk #${chunkCount} len=${c.length}`
          );
          onChunk(c);
        };
        const wrappedOnDone = () => {
          console.log(`[SSTRM req:${reqId}] DONE (chunks=${chunkCount})`);
          onDone();
        };
        const wrappedOnError = (e: any) => {
          console.log(`[SSTRM req:${reqId}] ERROR`, e);
          onError(e);
        };

        try {
          return await original(
            messages,
            wrappedOnChunk,
            wrappedOnDone,
            wrappedOnError
          );
        } finally {
          console.log(`[SSTRM req:${reqId}] END`);
        }
      };
      console.log('[SSTRM] apiClient.sendChatMessageStreaming instrumented');
    } else {
      console.warn(
        '[SSTRM] apiClient.sendChatMessageStreaming not found to instrument'
      );
    }
  } catch (e) {
    console.warn('[SSTRM] Instrumentation failed (non-fatal):', e);
  }
}
