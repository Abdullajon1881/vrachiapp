import React, { useState, useEffect } from 'react';
import Header from './components/Header/Header';
import Sidebar from './components/Sidebar/Sidebar';
import Hero from './components/Hero/Hero';
import Services from './components/Services/Services';
import Profile from './components/Profile/Profile';
import DoctorApplication from './components/DoctorApplication/DoctorApplication';
import AdminPanel from './components/AdminPanel/AdminPanel';
import Footer from './components/Footer/Footer';
import MobileNav from './components/MobileNav/MobileNav';
import './App.scss';

function App() {
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    const saved = localStorage.getItem('darkTheme');
    return saved ? JSON.parse(saved) : false;
  });
  
  const [currentPage, setCurrentPage] = useState('home');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);

  // Функция для обновления состояния авторизации
  const updateAuthState = () => {
    const user = localStorage.getItem('user');
    if (user) {
      try {
        const parsedUser = JSON.parse(user);
        setUserData(parsedUser);
        setIsAuthenticated(true);
      } catch (error) {
        localStorage.removeItem('user');
        setIsAuthenticated(false);
        setUserData(null);
      }
    } else {
      setIsAuthenticated(false);
      setUserData(null);
    }
  };

  // Проверяем авторизацию при загрузке
  useEffect(() => {
    updateAuthState();
  }, []);

  useEffect(() => {
    localStorage.setItem('darkTheme', JSON.stringify(isDarkTheme));
    const appElement = document.querySelector('.app');
    if (isDarkTheme) {
      appElement.classList.add('dark-theme');
    } else {
      appElement.classList.remove('dark-theme');
    }
  }, [isDarkTheme]);

  // Обработка возврата от Google OAuth
  useEffect(() => {
    const handleGoogleAuthReturn = async () => {
      const currentUrl = window.location.href;
      
      if (currentUrl.includes('access_token=')) {
        // Извлекаем токен из URL
        const urlParams = new URLSearchParams(currentUrl.split('#')[1]);
        const accessToken = urlParams.get('access_token');
        
        if (accessToken) {
          try {
            // Отправляем токен на сервер
            const response = await fetch('http://localhost:8000/api/auth/google-auth/', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({ access_token: accessToken })
            });

            const data = await response.json();

            if (response.ok) {
              localStorage.setItem('user', JSON.stringify(data.user));
              setUserData(data.user);
              setIsAuthenticated(true);
              // Очищаем URL
              window.history.replaceState({}, document.title, window.location.pathname);
            } else {
              console.error('Ошибка Google OAuth:', data.error);
              window.history.replaceState({}, document.title, window.location.pathname);
            }
          } catch (err) {
            console.error('Ошибка соединения с сервером:', err);
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        }
      }
    };

    handleGoogleAuthReturn();
  }, []);

  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
  };

  // Обработчик выхода из системы
  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
    setUserData(null);
    setCurrentPage('home'); // Возвращаемся на главную страницу
  };

  // Функция для обновления данных пользователя
  const updateUserData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/current-user/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Обновляем данные пользователя:', data);
        
        // Обновляем userData с новыми данными
        setUserData(data);
        localStorage.setItem('user', JSON.stringify(data));
      } else {
        console.error('Ошибка получения данных пользователя');
      }
    } catch (error) {
      console.error('Ошибка обновления данных пользователя:', error);
    }
  };

  const renderContent = () => {
    // Если пользователь не авторизован, показываем только главную страницу
    if (!isAuthenticated) {
      switch (currentPage) {
        case 'home':
        default:
          return (
            <>
              <Hero />
              <Services />
            </>
          );
      }
    }

    // Если пользователь авторизован, показываем соответствующий контент
    switch (currentPage) {
      case 'profile':
        return <Profile userData={userData} />;
      case 'doctor-application':
        return <DoctorApplication />;
      case 'admin-applications':
        return <AdminPanel updateUserData={updateUserData} />;
      case 'home':
      default:
        return (
          <>
            <Hero />
            <Services />
          </>
        );
    }
  };

  return (
    <div className="app">
      <Header 
        onPageChange={setCurrentPage} 
        isAuthenticated={isAuthenticated}
        userData={userData}
        onLogout={handleLogout}
        onAuthSuccess={updateAuthState}
      />
      <Sidebar 
        toggleTheme={toggleTheme} 
        isDarkTheme={isDarkTheme} 
        onPageChange={setCurrentPage} 
        currentPage={currentPage}
        isAuthenticated={isAuthenticated}
        userData={userData}
      />
      <main className="main">
        {renderContent()}
      </main>
      <Footer />
      <MobileNav />
    </div>
  );
}

export default App;
