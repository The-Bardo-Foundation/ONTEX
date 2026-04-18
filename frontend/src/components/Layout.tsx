import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { runIngestion } from '../api';
import { useState } from 'react';

export function Layout({ children }: { children: ReactNode }) {
  const [ingesting, setIngesting] = useState(false);

  async function handleRunIngestion() {
    setIngesting(true);
    try {
      await runIngestion();
      alert('Ingestion started.');
    } catch {
      alert('Failed to start ingestion.');
    } finally {
      setIngesting(false);
    }
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-3 py-2 rounded-md text-sm font-medium ${
      isActive
        ? 'bg-blue-50 text-blue-700'
        : 'text-gray-600 hover:bg-gray-100'
    }`;

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar nav */}
      <nav className="w-52 shrink-0 bg-white border-r flex flex-col">
        <div className="px-4 py-4 border-b">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">ONTEX</p>
        </div>
        <div className="flex-1 px-3 py-4 space-y-1">
          <NavLink to="/" end className={navLinkClass}>
            Review Queue
          </NavLink>
          <NavLink to="/trials" className={navLinkClass}>
            All Trials
          </NavLink>
        </div>
        <div className="px-3 py-4 border-t">
          <button
            onClick={handleRunIngestion}
            disabled={ingesting}
            className="w-full px-3 py-2 text-xs font-medium rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            {ingesting ? 'Starting…' : 'Run Ingestion'}
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
