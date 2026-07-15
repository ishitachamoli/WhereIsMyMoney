'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useSession } from '@/components/SessionProvider';
import { ThemeToggle } from '@/components/ThemeToggle';
import { CurrencySelector } from '@/components/CurrencySelector';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: '📊' },
  { name: 'Transactions', href: '/transactions', icon: '💳' },
  { name: 'Add Cash', href: '/add-transaction', icon: '➕' },
  { name: 'Budgets', href: '/budgets', icon: '💰' },
  { name: 'Subscriptions', href: '/subscriptions', icon: '🔄' },
  { name: 'Upload', href: '/upload', icon: '📤' },
  { name: 'Analytics', href: '/analytics', icon: '📈' },
  { name: 'AI Summary', href: '/ai-summary', icon: '🤖' },
];

function UserSection() {
  const { user, isReady, isRegistered, logout } = useSession();

  if (!isReady) {
    return (
      <div className="flex items-center gap-3 px-3 py-2">
        <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
        <span className="text-xs text-zinc-500">Connecting...</span>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 px-3 py-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-zinc-300 truncate">
            {isRegistered ? user.email || user.name : 'Guest'}
          </p>
          {!isRegistered && (
            <p className="text-[10px] text-zinc-500">Session user</p>
          )}
        </div>
      </div>

      {!isRegistered && (
        <Link
          href="/register"
          className="flex items-center gap-2 px-3 py-2 text-xs text-amber-400 hover:text-amber-300 hover:bg-zinc-800/50 rounded-lg transition-colors"
        >
          <span>🔒</span>
          <span>Create Account</span>
        </Link>
      )}

      <button
        onClick={logout}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-zinc-400 hover:text-red-400 hover:bg-zinc-800/50 rounded-lg transition-colors text-left"
      >
        <span>🚪</span>
        <span>Logout</span>
      </button>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:flex-col md:w-64 bg-zinc-900 border-r border-zinc-800">
      <div className="flex items-center h-16 px-6 border-b border-zinc-800">
        <span className="text-xl font-bold text-white">💰 WIMM</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-zinc-800 text-white'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
              )}
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-zinc-800 space-y-2">
        <ThemeToggle />
        <CurrencySelector />
        <div className="border-t border-zinc-800 pt-2">
          <UserSection />
        </div>
      </div>
    </aside>
  );
}

export function MobileDrawer() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    close();
  }, [pathname, close]);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  return (
    <div className="md:hidden">
      {/* Hamburger button + app title fixed header */}
      <button
        className="fixed top-4 left-4 z-50 flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800/90 backdrop-blur-sm border border-zinc-700 text-white shadow-lg"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
      >
        <span className="text-xl leading-none">☰</span>
        <span className="text-sm font-bold">💰 WIMM</span>
      </button>

      {/* Overlay */}
      <div
        className={cn(
          'fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity duration-300',
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
        onClick={close}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        className={cn(
          'fixed left-0 top-0 h-full w-72 bg-zinc-900 border-r border-zinc-800 z-50 flex flex-col transition-transform duration-300 ease-in-out shadow-2xl',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Drawer header */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-zinc-800">
          <span className="text-xl font-bold text-white">💰 WIMM</span>
          <button
            onClick={close}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            aria-label="Close menu"
          >
            <span className="text-xl leading-none">✕</span>
          </button>
        </div>

        {/* Nav items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={close}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                )}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer: theme toggle, currency, user info, logout */}
        <div className="p-4 border-t border-zinc-800 space-y-2">
          <ThemeToggle />
          <CurrencySelector />
          <div className="border-t border-zinc-800 pt-2">
            <UserSection />
          </div>
        </div>
      </div>
    </div>
  );
}
