import React, { useEffect, useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import { DashboardPage } from './pages/DashboardPage';
import { PlannerPage } from './pages/PlannerPage';
import { AdvisorPage } from './pages/AdvisorPage';
import { TransportPage } from './pages/TransportPage';
import { ImpactPage } from './pages/ImpactPage';
import { AssistantPage } from './pages/AssistantPage';
import { fetchHealthCheck } from './services/api';
import { NavigationPage, BackendHealthResponse } from './types';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<NavigationPage>('dashboard');
  const [health, setHealth] = useState<BackendHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [selectedStationId, setSelectedStationId] = useState<string>('');

  useEffect(() => {
    let isMounted = true;

    async function checkHealth() {
      try {
        setHealthLoading(true);
        const data = await fetchHealthCheck();
        if (isMounted) {
          setHealth(data);
          setHealthError(null);
        }
      } catch (err) {
        if (isMounted) {
          setHealthError(err instanceof Error ? err.message : 'Failed to connect to backend');
        }
      } finally {
        if (isMounted) {
          setHealthLoading(false);
        }
      }
    }

    checkHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <DashboardPage
            health={health}
            selectedStationId={selectedStationId}
            onSelectStation={setSelectedStationId}
          />
        );
      case 'planner':
        return <PlannerPage selectedStationId={selectedStationId} />;
      case 'advisor':
        return <AdvisorPage selectedStationId={selectedStationId} />;
      case 'transport':
        return (
          <TransportPage
            selectedStationId={selectedStationId}
            onNavigateToImpact={() => setCurrentPage('impact')}
          />
        );
      case 'impact':
        return <ImpactPage />;
      case 'assistant':
        return <AssistantPage health={health} />;
      default:
        return (
          <DashboardPage
            health={health}
            selectedStationId={selectedStationId}
            onSelectStation={setSelectedStationId}
          />
        );
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <Navbar
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
      />
      
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {renderCurrentPage()}
      </main>

      <Footer />
    </div>
  );
};

export default App;
