import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.scss';
import Sidebar from './components/Sidebar/Sidebar';
import MobileNav from './components/MobileNav/MobileNav';
import Header from './components/Header/Header';
import Hero from './components/Hero/Hero';
import Services from './components/Services/Services';
import ServicesPage from './components/Services/ServicesPage';
import About from './components/About/About';
import Doctors from './components/Doctors/Doctors';
import DoctorProfile from './components/DoctorProfile/DoctorProfile';
import Profile from './components/Profile/Profile';
import AIDiagnosis from './components/AIDiagnosis/AIDiagnosis';
import AdminPanel from './components/AdminPanel/AdminPanel';
import AuthModal from './components/AuthModal/AuthModal';
import DoctorApplication from './components/DoctorApplication/DoctorApplication';
import Consultations from './components/Consultations/Consultations';
import Chat from './components/Chat/Chat';
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

    handleGoogleAuthReturn();
  }, []);

  // Обработка верификации email
  useEffect(() => {
    const handleEmailVerification = async () => {
      const currentUrl = window.location.href;
      
      if (currentUrl.includes('verify-email/')) {
        const token = currentUrl.split('verify-email/')[1];
        
        if (token) {
          try {
            const response = await fetch(`http://localhost:8000/api/auth/verify-email/${token}/`, {
              method: 'GET',
              credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
              // Показываем сообщение об успешной верификации
              alert('Email успешно подтвержден! Теперь вы можете войти в систему.');
            } else {
              alert('Ошибка подтверждения email: ' + (data.error || 'Неизвестная ошибка'));
            }
            
            // Перенаправляем на главную страницу
            window.location.href = '/';
          } catch (err) {
            console.error('Ошибка верификации email:', err);
            alert('Ошибка соединения с сервером');
            window.location.href = '/';
          }
        }
      }
    };

    handleEmailVerification();
  }, []);

  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setUserData(null);
    // Перенаправляем на главную страницу
    window.location.href = '/';
  };

  const updateUserData = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/current-user/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setUserData(data);
        localStorage.setItem('user', JSON.stringify(data));
      }
    } catch (error) {
      console.error('Ошибка обновления данных пользователя:', error);
    }
  };

  const handleShowAllServices = () => {
    setCurrentPage('services');
    window.location.href = '/services';
  };

  const handleShowDoctors = () => {
    setCurrentPage('doctors');
    window.location.href = '/doctors';
  };

  // Компонент для главной страницы
  const HomePage = () => (
    <>
      <Hero />
      <Services onShowAllServices={handleShowAllServices} onShowDoctors={handleShowDoctors} userData={userData} />
    </>
  );

  // Компонент для страницы врачей (только для авторизованных пациентов)
  const DoctorsPage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <Doctors />;
  };

  // Компонент для профиля врача (доступен всем)
  const DoctorProfilePage = () => {
    return <DoctorProfile />;
  };

  // Компонент для профиля пользователя (только для авторизованных)
  const ProfilePage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <Profile />;
  };

  // Компонент для админ панели (только для админов)
  const AdminPanelPage = () => {
    if (!isAuthenticated || userData?.role !== 'admin') {
      return <Navigate to="/" replace />;
    }
    return <AdminPanel />;
  };

  // Компонент для заявки врача (только для авторизованных)
  const DoctorApplicationPage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <DoctorApplication updateUserData={updateUserData} />;
  };

  // Компонент для консультаций (только для авторизованных)
  const ConsultationsPage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <Consultations />;
  };

  // Компонент для чата (только для авторизованных)
  const ChatPage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <Chat />;
  };

  // Компонент для AI диагностики (только для авторизованных)
  const AIDiagnosisPage = () => {
    if (!isAuthenticated) {
      return <Navigate to="/" replace />;
    }
    return <AIDiagnosis />;
  };

  return (
    <Router>
      <div className="app">
        <Header 
          isAuthenticated={isAuthenticated}
          userData={userData}
          onLogout={handleLogout}
          onAuthSuccess={updateAuthState}
          isDarkTheme={isDarkTheme}
          toggleTheme={toggleTheme}
        />
        <Sidebar 
          toggleTheme={toggleTheme} 
          isDarkTheme={isDarkTheme} 
          isAuthenticated={isAuthenticated}
          userData={userData}
        />
        <main className="main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<About />} />
            <Route path="/services" element={<ServicesPage userData={userData} />} />
            <Route path="/doctors" element={<DoctorsPage />} />
            <Route path="/doctors/:id" element={<DoctorProfilePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/admin" element={<AdminPanelPage />} />
            <Route path="/doctor-application" element={<DoctorApplicationPage />} />
            <Route path="/consultations" element={<ConsultationsPage />} />
            <Route path="/consultations/:consultationId" element={<ChatPage />} />
            <Route path="/ai-diagnosis" element={<AIDiagnosisPage />} />
          </Routes>
        </main>
        <Footer />
        <MobileNav 
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          isAuthenticated={isAuthenticated}
          userData={userData}
          isDarkTheme={isDarkTheme}
          toggleTheme={toggleTheme}
        />
      </div>
    </Router>
  );
}

export default App;
