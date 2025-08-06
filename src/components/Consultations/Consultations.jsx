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
      const response = await fetch('http://localhost:8000/api/auth/consultations/', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setConsultations(data);
      } else {
        setError('Ошибка загрузки консультаций');
      }
    } catch (error) {
      console.error('Ошибка при загрузке консультаций:', error);
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

  return (
    <div className="consultations">
      <div className="consultations__header">
        <h1 className="consultations__title">Мои консультации</h1>
        <p className="consultations__subtitle">
          Управляйте своими консультациями с врачами
        </p>
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
          {consultations.map((consultation) => (
            <div 
              key={consultation.id} 
              className={`consultations__item consultations__item--${getStatusColor(consultation.status)}`}
              onClick={() => handleConsultationClick(consultation.id)}
            >
              <div className="consultations__item-header">
                <div className="consultations__item-info">
                  <h3 className="consultations__item-title">
                    {consultation.title || `Консультация с ${consultation.doctor_name}`}
                  </h3>
                  <p className="consultations__item-doctor">
                    {consultation.doctor_name}
                  </p>
                </div>
                <div className={`consultations__item-status consultations__item-status--${getStatusColor(consultation.status)}`}>
                  {getStatusText(consultation.status)}
                </div>
              </div>

              <div className="consultations__item-content">
                {consultation.description && (
                  <p className="consultations__item-description">
                    {consultation.description}
                  </p>
                )}
                
                <div className="consultations__item-meta">
                  <span className="consultations__item-date">
                    {formatDate(consultation.created_at)}
                  </span>
                  {consultation.messages_count > 0 && (
                    <span className="consultations__item-messages">
                      {consultation.messages_count} сообщений
                    </span>
                  )}
                </div>

                {consultation.last_message && (
                  <div className="consultations__item-last-message">
                    <span className="consultations__item-last-message-text">
                      {consultation.last_message.content}
                    </span>
                    <span className="consultations__item-last-message-time">
                      {formatDate(consultation.last_message.created_at)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Consultations; 