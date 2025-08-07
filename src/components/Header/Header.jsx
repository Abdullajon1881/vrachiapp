import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import healzyLogo from '../../assets/images/healzy.svg';
import AuthModal from '../AuthModal/AuthModal';
import './Header.scss';

const Header = ({ isAuthenticated, userData, onLogout, onAuthSuccess, isDarkTheme, toggleTheme }) => {
  const navigate = useNavigate();
  const [currentLanguage, setCurrentLanguage] = useState('RU');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [currentUserData, setCurrentUserData] = useState(null);

  // Получаем актуальные данные пользователя с сервера
  useEffect(() => {
    const fetchCurrentUser = async () => {
      if (isAuthenticated) {
        try {
          const response = await fetch('http://localhost:8000/api/auth/current-user/', {
            credentials: 'include'
          });
          if (response.ok) {
            const data = await response.json();
            setCurrentUserData(data);
          }
        } catch (error) {
          console.error('Ошибка получения данных пользователя:', error);
        }
      }
    };

    fetchCurrentUser();
  }, [isAuthenticated]);

  const handleLogoClick = () => {
    navigate('/');
  };

  const languages = [
    { code: 'RU', name: 'Русский' },
    { code: 'UZ', name: 'Узбекский' },
    { code: 'EN', name: 'Английский' }
  ];

  const handleAuthSuccess = (user) => {
    // Обновляем состояние в App.jsx
    if (onAuthSuccess) {
      onAuthSuccess();
    }
    setShowAuthModal(false);
  };

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
  };

  // Определяем роль пользователя
  const getUserRole = () => {
    const data = currentUserData || userData;
    if (!data) return 'Гость';
    
    if (data.is_staff || data.is_superuser) {
      return 'Администратор';
    }
    
    if (data.role === 'doctor') {
      return 'Врач';
    }
    
    return 'Пациент';
  };

  return (
    <header className="header">
      <div className="container">
        <div className="header__content">
          <div className="header__logo">
            <div className="header__logo-container" onClick={handleLogoClick} style={{ cursor: 'pointer' }}>
              <img src={healzyLogo} alt="Healzy" className="header__logo-img" />
            </div>
          </div>

          <div className="header__actions">
            {/* Телефон */}
            <div className="header__phone">
              <div className="header__phone-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <span className="header__phone-number">1188</span>
            </div>

            {/* Переключатель темы */}
            <div className="header__theme">
              <div className="header__theme-container" onClick={toggleTheme}>
                <div className="header__theme-icon">
                  {isDarkTheme ? (
                    // Солнце для темной темы
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="12" y1="1" x2="12" y2="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="12" y1="21" x2="12" y2="23" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="1" y1="12" x2="3" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="21" y1="12" x2="23" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : (
                    // Луна для светлой темы
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>
                <div className="header__theme-divider"></div>
                <div className="header__theme-buttons">
                  <button
                    className="header__theme-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      const currentIndex = languages.findIndex(lang => lang.code === currentLanguage);
                      const nextIndex = (currentIndex + 1) % languages.length;
                      setCurrentLanguage(languages[nextIndex].code);
                    }}
                  >
                    {currentLanguage}
                  </button>
                </div>
              </div>
            </div>

            {/* Пользовательская секция */}
            {isAuthenticated && (currentUserData || userData) ? (
              <div className="header__user">
                <div className="header__user-avatar">
                  {(currentUserData || userData).avatar ? (
                    <img src={(currentUserData || userData).avatar} alt="Аватар" />
                  ) : (
                    <div className="header__user-avatar-placeholder">
                      {(currentUserData || userData).first_name && (currentUserData || userData).last_name 
                        ? `${(currentUserData || userData).first_name[0]}${(currentUserData || userData).last_name[0]}`.toUpperCase()
                        : (currentUserData || userData).first_name?.[0]?.toUpperCase() || 'U'}
                    </div>
                  )}
                </div>
                <div className="header__user-info">
                  <div className="header__user-name">{(currentUserData || userData).full_name || (currentUserData || userData).first_name || (currentUserData || userData).username}</div>
                  <div className="header__user-status">{getUserRole()}</div>
                </div>
                <button className="header__logout-btn" onClick={handleLogout} title="Выйти">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <polyline points="16,17 21,12 16,7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            ) : (
              <button 
                className="header__auth-btn"
                onClick={() => setShowAuthModal(true)}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="10,17 15,12 10,7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="15" y1="12" x2="3" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span>Войти</span>
              </button>
            )}

            {/* Кнопка поддержки */}
            <button className="header__support-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M22 2H2v8h20V2zM2 14h20v8H2v-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M6 6h.01M10 6h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Поддержка</span>
            </button>
          </div>
        </div>
      </div>

      <AuthModal 
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </header>
  );
};

export default Header; 