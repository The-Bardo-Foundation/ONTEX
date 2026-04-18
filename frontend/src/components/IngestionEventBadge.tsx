import type { IngestionEvent } from '../types';

export function IngestionEventBadge({ event }: { event: IngestionEvent | null }) {
  if (!event) return null;

  const style = event === 'NEW'
    ? 'bg-green-100 text-green-700'
    : 'bg-amber-100 text-amber-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {event}
    </span>
  );
}
