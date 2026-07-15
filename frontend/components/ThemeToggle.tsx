'use client';

import { useTheme } from '@/lib/theme';
import { useEffect, useState } from 'react';

/**
 * Theme toggle button - switches between light and dark modes.
 * Only renders content after client hydration to prevent SSR mismatch.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="h-10" />;
  }

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors"
      title={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
    >
      <span className="text-lg">{resolvedTheme === 'dark' ? '☀️' : '🌙'}</span>
      <span>{resolvedTheme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
    </button>
  );
}

export { ThemeToggle as ThemeToggleInner };
