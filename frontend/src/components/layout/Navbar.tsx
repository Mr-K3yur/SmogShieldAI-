import React, { useState } from 'react';
import { 
  ShieldAlert, 
  LayoutDashboard, 
  CalendarClock, 
  Home, 
  Leaf, 
  Calculator, 
  Bot, 
  Menu, 
  X,
  Activity
} from 'lucide-react';
import { NavigationPage, BackendHealthResponse } from '../../types';

interface NavbarProps {
  currentPage: NavigationPage;
  onPageChange: (page: NavigationPage) => void;
  health: BackendHealthResponse | null;
  healthLoading: boolean;
  healthError: string | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentPage,
  onPageChange,
  health,
  healthLoading,
  healthError
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: { id: NavigationPage; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'dashboard', label: 'AQI Dashboard', icon: LayoutDashboard },
    { id: 'planner', label: 'Daily Planner', icon: CalendarClock },
    { id: 'advisor', label: 'Indoor Advisor', icon: Home },
    { id: 'transport', label: 'Green Alternatives', icon: Leaf },
    { id: 'impact', label: 'Impact Tracker', icon: Calculator },
    { id: 'assistant', label: 'AI Assistant', icon: Bot },
  ];

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Identity */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onPageChange('dashboard')}>
            <div className="bg-emerald-600 p-2 rounded-lg text-white shadow-sm flex items-center justify-center">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                SmogShield <span className="text-emerald-400 text-xs px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/30">AI</span>
              </span>
              <p className="text-xs text-slate-400 hidden sm:block">Urban Family Air Defense</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-1" aria-label="Main Navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onPageChange(item.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Backend Connectivity Status Indicator */}
          <div className="hidden lg:flex items-center text-xs space-x-2 bg-slate-800/80 border border-slate-700/60 rounded-full px-3 py-1.5">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">API:</span>
            {healthLoading ? (
              <span className="text-amber-400 flex items-center gap-1">Connecting...</span>
            ) : health ? (
              <span className="text-emerald-400 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                v{health.version} ({health.gemini_model_configured})
              </span>
            ) : (
              <span className="text-rose-400 flex items-center gap-1.5" title={healthError || 'Failed to connect'}>
                <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                Offline
              </span>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 focus:outline-none"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-slate-900 px-2 pt-2 pb-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onPageChange(item.id);
                  setMobileMenuOpen(false);
                }}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-base font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </button>
            );
          })}
          
          <div className="pt-2 px-3 pb-1 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>FastAPI Backend:</span>
            {health ? (
              <span className="text-emerald-400 font-medium">Online ({health.gemini_model_configured})</span>
            ) : (
              <span className="text-rose-400">Disconnected</span>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
