import React from 'react';
import { Radio, FileText, PlusCircle, CloudSun, Settings, Sun, Moon } from 'lucide-react';

export default function Sidebar({ currentPage, setCurrentPage, theme, toggleTheme }) {
  const menuItems = [
    { id: 'stations', label: 'Stations', icon: Radio },
    { id: 'observations', label: 'Observations', icon: FileText },
    { id: 'new-observation', label: 'New Observation', icon: PlusCircle },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <CloudSun size={28} />
        <span className="sidebar-logo-text">WOMS Portal</span>
      </div>
      <nav style={{ flex: 1 }}>
        <ul className="sidebar-menu">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            return (
              <li key={item.id}>
                <a
                  className={`sidebar-item ${isActive ? 'active' : ''}`}
                  onClick={() => setCurrentPage(item.id)}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </nav>

      <div style={{ padding: '0 0.5rem' }}>
        <button 
          className="theme-toggle-btn" 
          onClick={toggleTheme}
          title="Switch Theme (Dark / Light)"
        >
          {theme === 'dark' ? <Sun size={18} style={{ color: '#f59e0b' }} /> : <Moon size={18} style={{ color: '#0284c7' }} />}
          <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
        </button>

        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          <p>V1.0.0 • Connected to DB</p>
        </div>
      </div>
    </aside>
  );
}

