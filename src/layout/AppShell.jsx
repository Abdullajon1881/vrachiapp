import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header/Header';
import Sidebar from '../components/Sidebar/Sidebar';
import Footer from '../components/Footer/Footer';
import MobileNav from '../components/MobileNav/MobileNav';
import { useAuth } from '../shared/AuthContext.jsx';

function AppShell({ isDarkTheme, toggleTheme }) {
  const { user, isAuthenticated, logout, validateAuth } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="app">
      <Header
        isAuthenticated={isAuthenticated}
        userData={user}
        onLogout={handleLogout}
        onAuthSuccess={validateAuth}
        isDarkTheme={isDarkTheme}
        toggleTheme={toggleTheme}
      />
      <Sidebar
        toggleTheme={toggleTheme}
        isDarkTheme={isDarkTheme}
        isAuthenticated={isAuthenticated}
        userData={user}
      />
      <main className="main">
        <Outlet />
      </main>
      <Footer />
      <MobileNav
        isAuthenticated={isAuthenticated}
        userData={user}
        isDarkTheme={isDarkTheme}
        toggleTheme={toggleTheme}
      />
    </div>
  );
}

export default AppShell;

