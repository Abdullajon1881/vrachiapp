import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Consultations.scss';

const Consultations = () => {
  const [consultations, setConsultations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchConsultations();
  }, []);

  const fetchConsultations = async () => {
    try {
      const response = await fetch('https://healzy.uz/api/auth/consultations/', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setConsultations(data);
      } else {
        setError('Ошибка загрузки консультаций');
      }
    } catch (error) {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'pending';
      case 'active':
        return 'active';
      case 'completed':
        return 'completed';
      case 'cancelled':
        return 'cancelled';
      default:
        return 'default';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'pending':
        return 'Ожидание';
      case 'active':
        return 'Активна';
      case 'completed':
        return 'Завершена';
      case 'cancelled':
        return 'Отменена';
      default:
        return status;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleConsultationClick = (consultationId) => {
    navigate(`/consultations/${consultationId}`);
  };

  if (loading) {
    return (
      <div className="consultations">
        <div className="consultations__loading">
          <div className="loading-spinner"></div>
          <p>Загрузка консультаций...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="consultations">
        <div className="consultations__error">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={fetchConsultations} className="consultations__retry-btn">
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  const getCurrentUser = () => {
    return JSON.parse(localStorage.getItem('user') || '{}');
  };

  const getOtherParticipant = (consultation) => {
    const currentUser = getCurrentUser();
    if (currentUser.role === 'doctor') {
      return consultation.patient;
    } else {
      return consultation.doctor;
    }
  };

  const getOtherParticipantRole = (consultation) => {
    const currentUser = getCurrentUser();
    if (currentUser.role === 'doctor') {
      return 'Пациент';
    } else {
      return 'Врач';
    }
  };

  const getInitials = (name) => {
    if (!name) return '?';
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return parts[0].charAt(0).toUpperCase() + parts[1].charAt(0).toUpperCase();
    }
    return name.charAt(0).toUpperCase();
  };

  const formatCreationDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="consultations">
      <div className="consultations__header">
        <h1 className="consultations__title">История</h1>
      </div>

      {consultations.length === 0 ? (
        <div className="consultations__empty">
          <div className="consultations__empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 9h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 13h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h3>Консультаций пока нет</h3>
          <p>У вас пока нет консультаций. Запишитесь к врачу, чтобы начать консультацию.</p>
          <button 
            onClick={() => navigate('/doctors')} 
            className="consultations__find-doctor-btn"
          >
            Найти врача
          </button>
        </div>
      ) : (
        <div className="consultations__list">
          {consultations.map((consultation) => {
            const otherParticipant = getOtherParticipant(consultation);
            const otherParticipantRole = getOtherParticipantRole(consultation);
            
            return (
              <div 
                key={consultation.id} 
                className="consultations__card"
              >
                <div className="consultations__card-header">
                  <div className="consultations__avatar">
                    {getInitials(otherParticipant?.full_name || '')}
                  </div>
                  <div className="consultations__card-info">
                    <h3 className="consultations__participant-name">
                      {otherParticipant?.full_name || 'Неизвестно'}
                    </h3>
                    <p className="consultations__participant-role">
                      {otherParticipantRole}
                    </p>
                  </div>
                </div>

                <div className="consultations__card-details">
                  <div className="consultations__detail-row">
                    <span className="consultations__detail-label">Статус:</span>
                    <span className={`consultations__detail-value consultations__status--${getStatusColor(consultation.status)}`}>
                      {getStatusText(consultation.status)}
                    </span>
                  </div>

                  <div className="consultations__detail-row">
                    <span className="consultations__detail-label">Дата создания:</span>
                    <span className="consultations__detail-value">
                      {formatCreationDate(consultation.created_at)}
                    </span>
                  </div>

                  {consultation.started_at && (
                    <div className="consultations__detail-row">
                      <span className="consultations__detail-label">Время начала:</span>
                      <span className="consultations__detail-value">
                        {formatTime(consultation.started_at)}
                      </span>
                    </div>
                  )}

                  <div className="consultations__detail-row">
                    <span className="consultations__detail-label">Сообщения:</span>
                    <span className="consultations__detail-value">
                      {consultation.messages_count || 0} / 50
                    </span>
                  </div>
                </div>

                <button 
                  className="consultations__chat-btn"
                  onClick={() => handleConsultationClick(consultation.id)}
                >
                  Открыть чат
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Consultations; 