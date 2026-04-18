import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AllTrialsPage } from './pages/AllTrialsPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { TrialDetailPage } from './pages/TrialDetailPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ReviewQueuePage />} />
        <Route path="/trials" element={<AllTrialsPage />} />
        <Route path="/trials/:nct_id" element={<TrialDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;
