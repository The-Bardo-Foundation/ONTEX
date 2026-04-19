import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { SignIn, useAuth } from '@clerk/clerk-react';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { AllTrialsPage } from './pages/AllTrialsPage';
import { TrialDetailPage } from './pages/TrialDetailPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { setTokenProvider } from './api';

function App() {
  const { getToken } = useAuth();

  // Wire the Clerk session token into the axios instance so protected API
  // calls automatically carry the Bearer header.
  useEffect(() => {
    setTokenProvider(getToken);
  }, [getToken]);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<Layout variant="public"><LandingPage /></Layout>} />
      <Route path="/trials" element={<Layout variant="public"><AllTrialsPage /></Layout>} />
      <Route path="/trials/:nct_id" element={<Layout variant="public"><TrialDetailPage /></Layout>} />
      <Route
        path="/sign-in/*"
        element={
          <div className="flex items-center justify-center min-h-screen bg-gray-50">
            <SignIn routing="path" path="/sign-in" fallbackRedirectUrl="/admin" />
          </div>
        }
      />

      {/* Admin routes (protected) */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <Layout variant="admin"><ReviewQueuePage /></Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/trials"
        element={
          <ProtectedRoute>
            <Layout variant="admin"><AllTrialsPage adminMode /></Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
