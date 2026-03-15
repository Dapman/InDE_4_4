import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { useAuthStore } from './stores/authStore';
// v4.3: Experience mode context
import { ExperienceProvider } from './context/ExperienceContext';
import { AppShell } from './components/layout/AppShell';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import NewPursuitPage from './pages/NewPursuitPage';
import PursuitPage from './pages/PursuitPage';
import CoachingPage from './pages/CoachingPage';
import ArtifactsPage from './pages/ArtifactsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import EMSPage from './pages/EMSPage';
import { ReviewSession } from './components/ems';
import IKFPage from './pages/IKFPage';
import SettingsPage from './pages/SettingsPage';
import PortfolioPage from './pages/PortfolioPage';
import OrgPortfolioPage from './pages/OrgPortfolioPage';
import WelcomePage from './pages/WelcomePage';
import NotFoundPage from './pages/NotFoundPage';
// v3.14: Diagnostics panel (admin-only)
import DiagnosticsPage from './pages/DiagnosticsPage';
// v3.8: Setup wizard
import SetupWizard from './pages/setup/SetupWizard';
// v3.12: Account trust pages
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import CancelDeletionPage from './pages/CancelDeletionPage';

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ExperienceProvider>
        <BrowserRouter>
        <Routes>
          {/* v3.8: Setup wizard (first-run only) */}
          <Route path="/setup" element={<SetupWizard />} />
          <Route path="/login" element={<LoginPage />} />
          {/* v3.12: Password reset and account deletion cancellation */}
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/cancel-deletion" element={<CancelDeletionPage />} />

          {/* Protected routes inside AppShell (5-zone layout) */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="welcome" element={<WelcomePage />} />
            <Route path="pursuit/new" element={<NewPursuitPage />} />
            <Route path="pursuit/:id" element={<PursuitPage />}>
              <Route index element={<CoachingPage />} />
              <Route path="artifacts" element={<ArtifactsPage />} />
            </Route>
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="portfolio" element={<PortfolioPage />} />
            <Route path="org/portfolio" element={<OrgPortfolioPage />} />
            <Route path="ems" element={<EMSPage />} />
            <Route path="ems/review/:sessionId" element={<ReviewSession />} />
            <Route path="ikf" element={<IKFPage />} />
            <Route path="settings" element={<SettingsPage />} />
            {/* v3.14: Admin-only diagnostics */}
            <Route path="diagnostics" element={<DiagnosticsPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        </BrowserRouter>
      </ExperienceProvider>
    </QueryClientProvider>
  );
}
