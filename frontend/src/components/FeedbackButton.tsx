import { useEffect, useRef, useState } from 'react';

const GOOGLE_FORM_URL =
  'https://docs.google.com/forms/d/e/1FAIpQLSeY3LQ8rE-uyddr96IefrzM92_DZBiW4VIEbDFul0jVyoQs7w/viewform';
const GITHUB_ISSUES_URL = 'https://github.com/The-Bardo-Foundation/ONTEX/issues';

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false);
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div
      ref={containerRef}
      className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3"
    >
      {open && (
        <div
          role="dialog"
          aria-label="Feedback options"
          className="w-80 rounded-lg border border-gray-200 bg-white p-4 shadow-xl"
        >
          <div className="mb-3">
            <h2 className="text-sm font-semibold text-gray-900">
              Report an issue or give feedback
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              Help us improve ONTEX by letting us know what's broken or what
              could be better.
            </p>
          </div>

          <div className="space-y-2">
            <a
              href={GOOGLE_FORM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-md border border-gray-200 p-3 transition hover:border-blue-400 hover:bg-blue-50"
            >
              <div className="text-sm font-medium text-gray-900">
                General feedback
              </div>
              <div className="mt-0.5 text-xs text-gray-600">
                For all users — share thoughts or issues through a short Google
                Form.
              </div>
            </a>

            <a
              href={GITHUB_ISSUES_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-md border border-gray-200 p-3 transition hover:border-blue-400 hover:bg-blue-50"
            >
              <div className="text-sm font-medium text-gray-900">
                Report on GitHub
              </div>
              <div className="mt-0.5 text-xs text-gray-600">
                For technical users — ONTEX is open source; open an issue on
                GitHub.
              </div>
            </a>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="flex items-center gap-2 rounded-full bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M18 5v8a2 2 0 0 1-2 2h-5l-5 4v-4H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Zm-6 4a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm-3-4a1 1 0 0 0-1 1v3a1 1 0 0 0 2 0V6a1 1 0 0 0-1-1Z"
            clipRule="evenodd"
          />
        </svg>
        Feedback
      </button>
    </div>
  );
}
