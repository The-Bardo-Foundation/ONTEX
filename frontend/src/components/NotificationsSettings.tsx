import { useState } from 'react';
import { useUser } from '@clerk/clerk-react';

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

export function NotificationsSettings() {
  const { user, isLoaded } = useUser();
  const [saveState, setSaveState] = useState<SaveState>('idle');

  if (!isLoaded || !user) {
    return (
      <div className="text-sm text-gray-500">Loading notification settings…</div>
    );
  }

  // Default OFF: only an explicit `true` counts as opted-in.
  const enabled = user.unsafeMetadata?.emailIngestionSummary === true;

  async function toggle() {
    if (!user) return;
    const next = !enabled;
    setSaveState('saving');
    try {
      await user.update({
        unsafeMetadata: {
          ...user.unsafeMetadata,
          emailIngestionSummary: next,
        },
      });
      setSaveState('saved');
      window.setTimeout(() => setSaveState('idle'), 1500);
    } catch (err) {
      console.error('Failed to update notification preference', err);
      setSaveState('error');
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-lg font-semibold text-gray-900">Email notifications</h1>
      <p className="mt-1 text-sm text-gray-500">
        Admins do not receive any emails by default. Enable the toggle below to
        receive a short daily summary of new trials ingested by ONTEX.
      </p>

      <label className="mt-6 flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          checked={enabled}
          disabled={saveState === 'saving'}
          onChange={toggle}
        />
        <span className="text-sm">
          <span className="font-medium text-gray-900">
            Email me when new trials appear
          </span>
          <span className="block text-xs text-gray-500 mt-0.5">
            One email per day, sent after the daily ingestion run finishes.
          </span>
        </span>
      </label>

      <div className="mt-3 h-4 text-xs">
        {saveState === 'saving' && <span className="text-gray-500">Saving…</span>}
        {saveState === 'saved' && <span className="text-green-600">Saved</span>}
        {saveState === 'error' && (
          <span className="text-red-600">Could not save — please try again.</span>
        )}
      </div>
    </div>
  );
}
