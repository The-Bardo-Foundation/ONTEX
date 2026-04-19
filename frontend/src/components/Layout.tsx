import type { ReactNode } from 'react';
import { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { SignInButton, UserButton, useAuth } from '@clerk/clerk-react';
import { IngestionProgressModal } from './IngestionProgressModal';

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
      isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
    }`;

  // ── Public layout ───────────────────────────────────────────────────────────
  if (variant === 'public') {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <nav className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
          <Link to="/" className="flex items-center gap-2">
            <img src="/bardo-logo.png" alt="Bardo" className="h-8 w-auto" />
          </Link>
          <div className="flex items-center gap-6">
            <NavLink
              to="/trials"
              className={({ isActive }) =>
                `text-sm font-medium ${isActive ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'}`
              }
            >
              Search Trials
            </NavLink>
            {isSignedIn ? (
              <NavLink
                to="/admin"
                className="text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                Admin Dashboard
              </NavLink>
            ) : (
              <SignInButton mode="redirect" forceRedirectUrl="/admin">
                <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  Admin Login
                </button>
              </SignInButton>
            )}
          </div>
        </nav>
        <main className="flex-1">{children}</main>
      </div>
    );
  }

  // ── Admin layout ────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-gray-50">
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
            className="w-full px-3 py-2 text-xs font-medium rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
          >
            Run Ingestion
          </button>
        </div>
      </nav>

      <main className="flex-1 overflow-hidden">{children}</main>

      {showIngestion && (
        <IngestionProgressModal onClose={() => setShowIngestion(false)} />
      )}
    </div>
  );
}
