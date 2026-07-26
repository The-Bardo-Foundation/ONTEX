import type { ReactNode } from 'react';
import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { IngestionDashboardModal } from './IngestionDashboardModal';
import { FeedbackButton } from './FeedbackButton';

type LayoutVariant = 'public' | 'admin';

export function Layout({
  children,
  variant = 'public',
}: {
  children: ReactNode;
  variant?: LayoutVariant;
}) {
  const [showIngestion, setShowIngestion] = useState(false);
  const { isSignedIn } = useAuth();

  const adminNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-3 py-2 rounded-md text-sm font-medium ${
      isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100'
    }`;

  // ── Public layout ───────────────────────────────────────────────────────────
  if (variant === 'public') {
    return (
      <div className="min-h-screen bg-surface flex flex-col">
        {/*
          The logo is 5.6:1, so at h-10 it plus both links needs ~465px. Below that
          the row wraps instead of forcing the whole document wider than the
          viewport, which used to push every page into horizontal scroll on a phone.
        */}
        <nav className="bg-white border-b border-line px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-3 shrink-0">
          <Link to="/" className="flex items-center gap-2">
            <img
              src="/osn-bardo-logo.png"
              alt="Osteosarcoma Now — managed by Bardo Foundation"
              className="max-h-8 w-auto max-w-full sm:max-h-10"
            />
          </Link>
          <div className="flex items-center gap-4 sm:gap-6">
            <NavLink
              to="/trials"
              className={({ isActive }) =>
                `text-sm font-medium ${isActive ? 'text-brand-600' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              Search Trials
            </NavLink>
            {isSignedIn ? (
              <NavLink
                to="/admin"
                className="text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                Admin Dashboard
              </NavLink>
            ) : (
              <SignInButton mode="redirect" forceRedirectUrl="/admin">
                <button className="text-sm font-medium text-brand-600 hover:text-brand-700">
                  Admin Login
                </button>
              </SignInButton>
            )}
          </div>
        </nav>
        <main className="flex-1">{children}</main>
        <FeedbackButton />
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
          <UserButton afterSignOutUrl="/" />
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
