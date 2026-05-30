import type { ReactNode } from 'react';
import { useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { IngestionDashboardModal } from './IngestionDashboardModal';
import { FeedbackButton } from './FeedbackButton';
import { NotificationsSettings } from './NotificationsSettings';

const BellIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
    width={16}
    height={16}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
    />
  </svg>
);

type LayoutVariant = 'public' | 'admin';

export function Layout({
  children,
  variant = 'public',
}: {
  children: ReactNode;
  variant?: LayoutVariant;
}) {
  const [showIngestion, setShowIngestion] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { isSignedIn } = useAuth();
  const { pathname } = useLocation();

  const adminNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-3 py-2 rounded-md text-sm font-medium ${
      isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100'
    }`;

  // ── Public layout ───────────────────────────────────────────────────────────
  if (variant === 'public') {
    return (
      // min-h-screen-dynamic, not min-h-screen: on a phone 100vh excludes the
      // browser chrome, which pushes the trials page's pagination bar below the
      // visible area. See the utility's comment in index.css.
      <div className="min-h-screen-dynamic bg-surface flex flex-col">
        {/*
          One row at every width. From `sm` up the links sit inline and keep
          their intrinsic width (shrink-0, no wrapping mid-label) while the logo
          absorbs whatever is left: it is 5.6:1 with height driven by
          max-height, so max-w-full plus min-w-0 on its flex item lets it scale
          down instead of wrapping the row or forcing the document wider than
          the viewport. Below `sm` two labels plus the logo leave the logo
          unreadably small, so the links collapse behind a menu button instead.
        */}
        <nav className="bg-white border-b border-line px-4 sm:px-6 py-3 flex items-center justify-between gap-x-3 sm:gap-x-4 shrink-0">
          <Link to="/" className="flex items-center gap-2 min-w-0">
            <img
              src="/osn-bardo-logo.png"
              alt="Osteosarcoma Now — managed by Bardo Foundation"
              className="max-h-7 w-auto max-w-full sm:max-h-10"
            />
          </Link>
          <div className="hidden sm:flex items-center gap-3 shrink-0 sm:gap-6">
            <NavLink
              to="/trials"
              className={({ isActive }) =>
                `text-xs sm:text-sm font-medium whitespace-nowrap ${isActive ? 'text-brand-600' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              Search Trials
            </NavLink>
            {isSignedIn ? (
              <NavLink
                to="/admin"
                className="text-xs sm:text-sm font-medium whitespace-nowrap text-brand-600 hover:text-brand-700"
              >
                Admin Dashboard
              </NavLink>
            ) : (
              <SignInButton mode="redirect" forceRedirectUrl="/admin">
                <button type="button" className="text-xs sm:text-sm font-medium whitespace-nowrap text-brand-600 hover:text-brand-700">
                  Admin Login
                </button>
              </SignInButton>
            )}
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            className="sm:hidden shrink-0 -mr-1.5 p-1.5 rounded-md text-gray-700 hover:bg-surface-muted"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              {menuOpen ? <path d="M6 18L18 6M6 6l12 12" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </nav>

        {menuOpen && (
          <div className="sm:hidden bg-white border-b border-line px-3 pb-3 pt-1 flex flex-col gap-0.5 shrink-0">
            <NavLink
              to="/trials"
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `px-2 py-2.5 rounded-md text-sm font-medium ${isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-700 hover:bg-surface-muted'}`
              }
            >
              Search Trials
            </NavLink>
            {isSignedIn ? (
              <NavLink
                to="/admin"
                onClick={() => setMenuOpen(false)}
                className="px-2 py-2.5 rounded-md text-sm font-medium text-brand-600 hover:bg-brand-50"
              >
                Admin Dashboard
              </NavLink>
            ) : (
              <SignInButton mode="redirect" forceRedirectUrl="/admin">
                <button
                  type="button"
                  className="px-2 py-2.5 rounded-md text-left text-sm font-medium text-brand-600 hover:bg-brand-50"
                >
                  Admin Login
                </button>
              </SignInButton>
            )}
          </div>
        )}

        <main className="flex-1">{children}</main>
        {pathname === '/' && <FeedbackButton />}
      </div>
    );
  }

  // ── Admin layout ────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-surface">
      <nav className="w-52 shrink-0 bg-white border-r flex flex-col">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <Link to="/">
            <img src="/bardo-logo.png" alt="Bardo" className="h-7 w-auto" />
          </Link>
          <UserButton afterSignOutUrl="/">
            <UserButton.UserProfilePage
              label="Notifications"
              url="notifications"
              labelIcon={<BellIcon />}
            >
              <NotificationsSettings />
            </UserButton.UserProfilePage>
          </UserButton>
        </div>
        <div className="flex-1 px-3 py-4 space-y-1">
          <NavLink to="/admin" end className={adminNavLinkClass}>
            Review Queue
          </NavLink>
          <NavLink to="/admin/trials" className={adminNavLinkClass}>
            All Trials
          </NavLink>
          <NavLink to="/trials" className={adminNavLinkClass}>
            Public View
          </NavLink>
        </div>
        <div className="px-3 py-4 border-t">
          <button
            onClick={() => setShowIngestion(true)}
            className="w-full px-3 py-2 text-xs font-medium rounded border border-gray-300 text-gray-600 hover:bg-surface"
          >
            Ingestion
          </button>
        </div>
      </nav>

      <main className="flex-1 overflow-hidden">{children}</main>

      {showIngestion && (
        <IngestionDashboardModal onClose={() => setShowIngestion(false)} />
      )}
    </div>
  );
}
