import { useEffect } from 'react';

const SITE_NAME = 'Osteosarcoma Now';

/**
 * Sets `document.title` to `"<title> — Osteosarcoma Now"` while the calling
 * component is mounted.
 *
 * Pass `null` to leave the title untouched — for pages whose title depends on
 * data that has not arrived yet, so the tab doesn't flash a placeholder.
 *
 * There is no restore-on-unmount: every route sets its own title, so the last
 * writer always wins. If you add a route, give it a title here too, otherwise
 * it inherits whichever title the previous route left behind.
 */
export function useDocumentTitle(title: string | null) {
  useEffect(() => {
    if (title === null) return;
    document.title = `${title} — ${SITE_NAME}`;
  }, [title]);
}
