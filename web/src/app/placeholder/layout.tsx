import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'PratikoAI - Coming Soon',
  description:
    "PratikoAI: l'assistente AI per commercialisti italiani. Prossimamente disponibile.",
};

export default function PlaceholderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
