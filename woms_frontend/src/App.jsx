import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';

import Stations from './pages/Stations';
import Observations from './pages/Observations';
import NewObservation from './pages/NewObservation';
import Settings from './pages/Settings';

export default function App() {
  const [currentPage, setCurrentPage] = useState('observations');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'stations':
        return <Stations />;
      case 'observations':
        return <Observations />;
      case 'new-observation':
        return <NewObservation setCurrentPage={setCurrentPage} />;
      case 'settings':
        return <Settings theme={theme} setTheme={setTheme} toggleTheme={toggleTheme} />;

      default:
        return <Observations />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        theme={theme} 
        toggleTheme={toggleTheme} 
      />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}

