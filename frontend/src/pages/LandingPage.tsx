import { Link } from 'react-router-dom';

export function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-57px)] px-6 py-16 text-center">
      <div className="flex items-center justify-center gap-10 mb-12">
        <img src="/bardo-logo.png" alt="The Bardo Foundation" className="h-20 w-auto" />
        <div className="w-px h-16 bg-gray-200" />
        <img src="/osteosarcoma-logo.png" alt="Osteosarcoma" className="h-20 w-auto" />
      </div>
      <h1 className="text-3xl font-semibold text-gray-900 mb-4">
        Osteosarcoma Clinical Trial Explorer
      </h1>
      <p className="text-base text-gray-500 max-w-xl mb-10">
        A curated database of active osteosarcoma clinical trials, reviewed and
        summarised for patients, families, and clinicians.
      </p>
      <Link
        to="/trials"
        className="px-6 py-3 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
      >
        Search Clinical Trials
      </Link>
    </div>
  );
}
