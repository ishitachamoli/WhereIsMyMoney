import { cn } from '@/lib/utils';

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse bg-zinc-800 rounded-xl p-6', className)}>
      <div className="h-4 bg-zinc-700 rounded w-1/3 mb-4" />
      <div className="h-8 bg-zinc-700 rounded w-2/3 mb-2" />
      <div className="h-3 bg-zinc-700 rounded w-1/4" />
    </div>
  );
}

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse bg-zinc-800 rounded-xl p-6', className)}>
      <div className="h-5 bg-zinc-700 rounded w-1/4 mb-6" />
      <div className="h-64 bg-zinc-700 rounded" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse bg-zinc-800 rounded-xl p-6">
      <div className="h-5 bg-zinc-700 rounded w-1/4 mb-6" />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="h-4 bg-zinc-700 rounded w-20" />
            <div className="h-4 bg-zinc-700 rounded flex-1" />
            <div className="h-4 bg-zinc-700 rounded w-24" />
            <div className="h-4 bg-zinc-700 rounded w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <TableSkeleton />
    </div>
  );
}
