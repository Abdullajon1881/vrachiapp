import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './DoctorProfile.scss';

const DoctorProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doctor, setDoctor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDoctorProfile = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/auth/doctors/${id}/`, {
          credentials: 'include'
        });
        
        if (response.ok) {
          const data = await response.json();
          setDoctor(data);
        } else {
          setError('Врач не найден');
        }
      } catch (error) {
        console.error('Ошибка при загрузке профиля врача:', error);
        setError('Ошибка соединения с сервером');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchDoctorProfile();
    }
  }, [id]);

  const getSpecializationIcon = (specialization) => {
    const icons = {
      'Терапевт': '🩺',
      'Кардиолог': '❤️',
      'Невролог': '🧠',
      'Офтальмолог': '👁️',
      'Дерматолог': '🔬',
      'Ортопед': '🦴',
      'Ревматолог': '🦴',
      'Педиатр': '👶',
      'Гинеколог': '👩‍⚕️',
      'Уролог': '🔬',
      'Эндокринолог': '⚖️',
      'Психиатр': '🧠',
      'Хирург': '🔪',
      'Стоматолог': '🦷',
      'Физиотерапевт': '💪',
      'Массажист': '🤲',
      'Психолог': '🧘',
      'Диетолог': '🥗',
      'Спортивный врач': '🏃',
      'Гериатр': '👴'
    };
    
    return icons[specialization] || '👨‍⚕️';
  };

  if (loading) {
    return (
      <div className="doctor-profile">
        <div className="doctor-profile__loading">
          <div className="loading-spinner"></div>
          <p>Загрузка профиля врача...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctor-profile">
        <div className="doctor-profile__error">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/doctors')} className="doctor-profile__back-btn">
            ← Вернуться к списку врачей
          </button>
        </div>
      </div>
    );
  }

  if (!doctor) {
    return (
      <div className="doctor-profile">
        <div className="doctor-profile__error">
          <h2>Врач не найден</h2>
          <p>Запрошенный врач не существует или был удален</p>
          <button onClick={() => navigate('/doctors')} className="doctor-profile__back-btn">
            ← Вернуться к списку врачей
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="doctor-profile">
      <div className="doctor-profile__container">
        {/* Кнопка назад */}
        <button onClick={() => navigate('/doctors')} className="doctor-profile__back-btn">
          ← Вернуться к списку врачей
        </button>

        {/* Основная информация */}
        <div className="doctor-profile__header">
          <div className="doctor-profile__avatar-section">
            <div className="doctor-profile__avatar">
              {doctor.avatar ? (
                <img src={doctor.avatar} alt={doctor.full_name} />
              ) : (
                <div className="doctor-profile__avatar-placeholder">
                  {doctor.first_name && doctor.last_name 
                    ? `${doctor.first_name[0]}${doctor.last_name[0]}`.toUpperCase()
                    : doctor.first_name?.[0]?.toUpperCase() || 'U'}
                </div>
              )}
            </div>
            <div className="doctor-profile__basic-info">
              <h1 className="doctor-profile__name">{doctor.full_name}</h1>
              <p className="doctor-profile__specialization">
                {getSpecializationIcon(doctor.specialization)} {doctor.specialization}
              </p>
              {doctor.region && (
                <p className="doctor-profile__location">
                  📍 {doctor.city ? `${doctor.city}, ${doctor.region}` : doctor.region}
                  {doctor.district && `, ${doctor.district}`}
                </p>
              )}
              {doctor.license_number && (
                <p className="doctor-profile__license">
                  📋 Лицензия: {doctor.license_number}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Детальная информация */}
        <div className="doctor-profile__content">
          <div className="doctor-profile__main-info">
            {doctor.experience && (
              <div className="doctor-profile__section">
                <h2>💼 Опыт работы</h2>
                <div className="doctor-profile__section-content">
                  <p>{doctor.experience}</p>
                </div>
              </div>
            )}

            {doctor.education && (
              <div className="doctor-profile__section">
                <h2>🎓 Образование</h2>
                <div className="doctor-profile__section-content">
                  <p>{doctor.education}</p>
                </div>
              </div>
            )}

            {doctor.languages && doctor.languages.length > 0 && (
              <div className="doctor-profile__section">
                <h2>🌍 Языки</h2>
                <div className="doctor-profile__section-content">
                  <div className="doctor-profile__languages">
                    {doctor.languages.map((language, index) => (
                      <span key={index} className="doctor-profile__language-tag">
                        {language}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {doctor.additional_info && (
              <div className="doctor-profile__section">
                <h2>ℹ️ Дополнительная информация</h2>
                <div className="doctor-profile__section-content">
                  <p>{doctor.additional_info}</p>
                </div>
              </div>
            )}
          </div>

          {/* Боковая панель с контактами */}
          <div className="doctor-profile__sidebar">
            <div className="doctor-profile__contact-card">
              <h3>📞 Контакты</h3>
              {doctor.phone && (
                <div className="doctor-profile__contact-item">
                  <span className="doctor-profile__contact-label">Телефон:</span>
                  <a href={`tel:${doctor.phone}`} className="doctor-profile__contact-value">
                    {doctor.phone}
                  </a>
                </div>
              )}
              {doctor.email && (
                <div className="doctor-profile__contact-item">
                  <span className="doctor-profile__contact-label">Email:</span>
                  <a href={`mailto:${doctor.email}`} className="doctor-profile__contact-value">
                    {doctor.email}
                  </a>
                </div>
              )}
              {doctor.address && (
                <div className="doctor-profile__contact-item">
                  <span className="doctor-profile__contact-label">Адрес:</span>
                  <span className="doctor-profile__contact-value">{doctor.address}</span>
                </div>
              )}
            </div>

            <div className="doctor-profile__action-card">
              <h3>Записаться на прием</h3>
              <p>Для записи на прием свяжитесь с врачом по указанным контактам</p>
              {doctor.phone && (
                <a href={`tel:${doctor.phone}`} className="doctor-profile__call-btn">
                  📞 Позвонить
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DoctorProfile; 