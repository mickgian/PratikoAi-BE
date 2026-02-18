'use client';

import { usePathname, useRouter } from 'next/navigation';
import { CreditCard, Receipt, Star } from 'lucide-react';

const tabs = [
  { name: 'Piano', href: '/account/piano', icon: Star },
  { name: 'Crediti', href: '/account/crediti', icon: CreditCard },
  { name: 'Fatturazione', href: '/account/fatturazione', icon: Receipt },
];

export default function AccountLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#F8F5F1]">
      <header className="bg-white border-b border-[#C4BDB4] px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <button
            onClick={() => router.push('/chat')}
            className="text-[#2A5D67] hover:underline text-sm"
          >
            &larr; Torna alla chat
          </button>
          <h1 className="text-xl font-semibold text-[#1E293B]">
            Il mio Account
          </h1>
          <div className="w-24" />
        </div>
      </header>

      <nav className="bg-white border-b border-[#C4BDB4]">
        <div className="max-w-5xl mx-auto flex gap-1 px-6">
          {tabs.map(tab => {
            const isActive = pathname === tab.href;
            const Icon = tab.icon;
            return (
              <button
                key={tab.href}
                onClick={() => router.push(tab.href)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-[#2A5D67] text-[#2A5D67]'
                    : 'border-transparent text-gray-500 hover:text-[#1E293B] hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.name}
              </button>
            );
          })}
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
