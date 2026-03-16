import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import './App.scss';
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
import Appointments from './components/Appointments/Appointments_1';
import MedicalRecords from './components/MedicalRecords/MedicalRecords_2';
import HealthNews from './components/HealthNews/HealthNews';
import HealthTools from './components/Healthtools/Healthtools';
import DentalChart from './components/DentalChart/DentalChart';
import Facilities from './components/Facilities/Facilities';
import { useTranslation } from 'react-i18next';
import { useAuth } from './shared/AuthContext.jsx';
import { apiClient, getCsrfToken } from './shared/apiClient';
import { useTheme } from './shared/useTheme';
import AppShell from './layout/AppShell.jsx';

function App() {
  const { t } = useTranslation();
  const { user, isAuthenticated, validateAuth, logout, refreshUser } = useAuth();
  const { isDarkTheme, toggleTheme } = useTheme();
  const navigate = useNavigate();

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
            await apiClient.post(
              '/api/auth/google-auth/',
              { access_token: accessToken },
              { csrf: true }
            );
            await validateAuth();
          } catch {
            // ignore, URL cleanup below
          }
          // Очищаем URL
          window.history.replaceState({}, document.title, window.location.pathname);
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
            const data = await apiClient.get(`/api/auth/verify-email/${token}/`);
            alert(t('app.emailVerified', 'Email successfully confirmed! Now you can log in.'));
            
            // Перенаправляем на главную страницу
            window.location.href = '/';
          } catch {
            alert(t('common.serverError', 'Ошибка соединения с сервером'));
            window.location.href = '/';
          }
        }
      }
    };

    handleEmailVerification();
  }, []);

  const handleLogout = () => {
    logout();
  };

  const updateUserData = async () => {
    await refreshUser();
  };

  // Компонент для главной страницы
  const HomePage = () => (
    <>
      <Hero />
      <Services userData={user} />
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
    if (!isAuthenticated || user?.role !== 'admin') {
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
    if (!isAuthenticated) return <Navigate to="/" replace />;
    return <AIDiagnosis />;
  };

  const AppointmentsPage = () => {
    if (!isAuthenticated) return <Navigate to="/" replace />;
    return <Appointments userData={user} />;
  };

  const MedicalRecordsPage = () => {
    if (!isAuthenticated) return <Navigate to="/" replace />;
    return <MedicalRecords />;
  };

  const HealthNewsPage = () => <HealthNews />;

  const HealthToolsPage = () => <HealthTools />;

  const DentalChartPage = () => {
    if (!isAuthenticated) return <Navigate to="/" replace />;
    return <DentalChart userData={user} />;
  };

  const FacilitiesPage = () => <Facilities />;

  return (
    <Router>
      <Routes>
        <Route
          element={
            <AppShell
              isDarkTheme={isDarkTheme}
              toggleTheme={toggleTheme}
            />
          }
        >
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<About />} />
          <Route path="/services" element={<ServicesPage userData={user} />} />
          <Route path="/doctors" element={<DoctorsPage />} />
          <Route path="/doctors/:id" element={<DoctorProfilePage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin" element={<AdminPanelPage />} />
          <Route path="/doctor-application" element={<DoctorApplicationPage />} />
          <Route path="/consultations" element={<ConsultationsPage />} />
          <Route path="/consultations/:consultationId" element={<ChatPage />} />
          <Route path="/ai-diagnosis" element={<AIDiagnosisPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/medical-records" element={<MedicalRecordsPage />} />
          <Route path="/health-news" element={<HealthNewsPage />} />
          <Route path="/health-tools" element={<HealthToolsPage />} />
          <Route path="/dental-chart" element={<DentalChartPage />} />
          <Route path="/facilities" element={<FacilitiesPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;