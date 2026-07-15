'use client';

import { Suspense } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { Sidebar, MobileDrawer } from '@/components/Sidebar';
import { useSession } from '@/components/SessionProvider';
import { ClassificationProgressBanner } from '@/components/ClassificationProgressBanner';

const AUTH_PAGES = ['/login', '/register'];

function AppShellInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { isReady } = useSession();

  const isAuthPage = AUTH_PAGES.some((p) => pathname?.startsWith(p));
  const classificationJobId = searchParams?.get('classification_job_id') || null;

  if (!isReady) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-400 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <MobileDrawer />
      <div className="flex-1 flex flex-col overflow-hidden">
        <ClassificationProgressBanner
          jobId={classificationJobId}
          onComplete={() => {
            window.dispatchEvent(new CustomEvent('classification-complete'));
          }}
        />
        <main className="flex-1 overflow-y-auto p-4 pt-16 md:p-6 md:pt-6 lg:p-8 lg:pt-8">
          {children}
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-400 text-sm">Loading...</p>
        </div>
      </div>
    }>
      <AppShellInner>{children}</AppShellInner>
    </Suspense>
  );
}
