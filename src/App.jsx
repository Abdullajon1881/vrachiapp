import React, { useState, useEffect } from 'react';
import './App.scss';
import Sidebar from './components/Sidebar/Sidebar';
import MobileNav from './components/MobileNav/MobileNav';
import Header from './components/Header/Header';
import Hero from './components/Hero/Hero';
import Services from './components/Services/Services';
import ServicesPage from './components/Services/ServicesPage';
import About from './components/About/About';
import Doctors from './components/Doctors/Doctors';
import Profile from './components/Profile/Profile';
import AdminPanel from './components/AdminPanel/AdminPanel';
import AuthModal from './components/AuthModal/AuthModal';
import DoctorApplication from './components/DoctorApplication/DoctorApplication';
import Footer from './components/Footer/Footer';

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
        console.error('Ошибка парсинга данных пользователя:', error);
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

    // Обработка верификации email
    const handleEmailVerification = async () => {
      const currentUrl = window.location.href;
      
      if (currentUrl.includes('verify-email/')) {
        // Извлекаем токен из URL
        const tokenMatch = currentUrl.match(/verify-email\/([^\/\?]+)/);
        if (tokenMatch) {
          const token = tokenMatch[1];
          
          try {
            const response = await fetch(`http://localhost:8000/api/auth/verify-email/${token}/`, {
              method: 'GET',
              credentials: 'include'
            });

            const data = await response.json();

            if (response.ok && data.success) {
              alert('Email успешно подтвержден! Теперь вы можете войти в систему.');
              // Очищаем URL
              window.history.replaceState({}, document.title, window.location.pathname);
            } else {
              alert(`Ошибка подтверждения: ${data.error || 'Неизвестная ошибка'}`);
              // Очищаем URL
              window.history.replaceState({}, document.title, window.location.pathname);
            }
          } catch (err) {
            console.error('Ошибка соединения с сервером:', err);
            alert('Ошибка соединения с сервером. Попробуйте позже.');
            // Очищаем URL
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        }
      }
    };

    handleGoogleAuthReturn();
    handleEmailVerification();
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

  // Обработчик для показа всех услуг
  const handleShowAllServices = () => {
    setCurrentPage('services');
  };

  // Обработчик для показа врачей
  const handleShowDoctors = () => {
    setCurrentPage('doctors');
  };

  const renderContent = () => {
    if (!isAuthenticated) {
      switch (currentPage) {
        case 'about':
          return <About />;
        case 'services':
          return <ServicesPage userData={userData} />;
        case 'home':
        default:
          return (
            <>
              <Hero />
              <Services onShowAllServices={handleShowAllServices} onShowDoctors={handleShowDoctors} userData={userData} />
            </>
          );
      }
    }
    switch (currentPage) {
      case 'profile':
        return <Profile />;
      case 'admin':
        return <AdminPanel />;
      case 'doctor-application':
        return <DoctorApplication updateUserData={updateUserData} />;
      case 'about':
        return <About />;
      case 'services':
        return <ServicesPage userData={userData} />;
      case 'doctors':
        return <Doctors />;
      case 'home':
      default:
        return (
          <>
            <Hero />
            <Services onShowAllServices={handleShowAllServices} onShowDoctors={handleShowDoctors} userData={userData} />
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
      <MobileNav 
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        isAuthenticated={isAuthenticated}
        userData={userData}
      />
    </div>
  );
}

export default App;
