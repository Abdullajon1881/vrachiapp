import React, { useState, useEffect } from 'react';
import './Doctors.scss';

const Doctors = () => {
  const [doctors, setDoctors] = useState([]);
  const [filteredDoctors, setFilteredDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedService, setSelectedService] = useState('all');
  const [selectedSpecialization, setSelectedSpecialization] = useState('all');
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [showDoctorModal, setShowDoctorModal] = useState(false);

  // Услуги для фильтрации
  const services = [
    'all',
    'Медицинские услуги',
    'Спортивные и диетические',
    'Физиотерапия',
    'Массаж',
    'Психологические консультации',
    'Уход за пожилыми'
  ];

  // Специализации, сгруппированные по услугам
  const specializationsByService = {
    'Медицинские услуги': [
      'Терапевт',
      'Кардиолог',
      'Невролог',
      'Офтальмолог',
      'Дерматолог',
      'Ортопед',
      'Ревматолог',
      'Педиатр',
      'Гинеколог',
      'Уролог',
      'Эндокринолог',
      'Психиатр',
      'Хирург',
      'Стоматолог',
      'Онколог',
      'Аллерголог',
      'Иммунолог',
      'Гастроэнтеролог',
      'Пульмонолог',
      'Нефролог',
      'Гематолог',
      'Инфекционист',
      'Травматолог',
      'Анестезиолог',
      'Реаниматолог'
    ],
    'Спортивные и диетические': [
      'Спортивный врач',
      'Диетолог'
    ],
    'Физиотерапия': [
      'Физиотерапевт'
    ],
    'Массаж': [
      'Массажист'
    ],
    'Психологические консультации': [
      'Психолог'
    ],
    'Уход за пожилыми': [
      'Гериатр'
    ]
  };

  // Регионы для фильтрации
  const regions = [
    'all',
    'Ташкентская область',
    'Город Ташкент',
    'Самаркандская область',
    'Город Самарканд',
    'Бухарская область',
    'Город Бухара',
    'Ферганская область',
    'Андижанская область',
    'Наманганская область',
    'Кашкадарьинская область',
    'Сурхандарьинская область',
    'Сырдарьинская область',
    'Джизакская область',
    'Навоийская область',
    'Хорезмская область',
    'Республика Каракалпакстан'
  ];

  useEffect(() => {
    fetchDoctors();
  }, []);

  useEffect(() => {
    filterDoctors();
  }, [doctors, selectedService, selectedSpecialization, selectedRegion, searchQuery]);

  // Сброс специализации при изменении услуги
  useEffect(() => {
    if (selectedService === 'all') {
      setSelectedSpecialization('all');
    } else {
      setSelectedSpecialization('all');
    }
  }, [selectedService]);

  // Сброс региона при изменении специализации
  useEffect(() => {
    if (selectedSpecialization === 'all') {
      setSelectedRegion('all');
    }
  }, [selectedSpecialization]);

  const resetFilters = () => {
    setSelectedService('all');
    setSelectedSpecialization('all');
    setSelectedRegion('all');
    setSearchQuery('');
  };

  const fetchDoctors = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/auth/doctors/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setDoctors(data);
        setFilteredDoctors(data);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Ошибка загрузки врачей');
      }
    } catch (error) {
      console.error('Ошибка при загрузке врачей:', error);
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const filterDoctors = () => {
    let filtered = [...doctors];

    // Фильтр по услугам (первый уровень)
    if (selectedService !== 'all') {
      const serviceSpecializations = specializationsByService[selectedService];
      if (serviceSpecializations) {
        filtered = filtered.filter(doctor => 
          doctor.specialization && 
          serviceSpecializations.some(spec => 
            doctor.specialization.toLowerCase().includes(spec.toLowerCase())
          )
        );
      }
    }

    // Фильтр по специализации (второй уровень)
    if (selectedSpecialization !== 'all') {
      filtered = filtered.filter(doctor => 
        doctor.specialization && 
        doctor.specialization.toLowerCase().includes(selectedSpecialization.toLowerCase())
      );
    }

    // Фильтр по региону (третий уровень)
    if (selectedRegion !== 'all') {
      filtered = filtered.filter(doctor => 
        doctor.region && 
        doctor.region.toLowerCase().includes(selectedRegion.toLowerCase())
      );
    }

    // Поиск по имени (работает независимо от фильтров)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(doctor => 
        doctor.full_name.toLowerCase().includes(query) ||
        doctor.specialization.toLowerCase().includes(query) ||
        (doctor.city && doctor.city.toLowerCase().includes(query))
      );
    }

    setFilteredDoctors(filtered);
  };

  const openDoctorProfile = async (doctorId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/doctors/${doctorId}/`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const doctorData = await response.json();
        setSelectedDoctor(doctorData);
        setShowDoctorModal(true);
      } else {
        alert('Ошибка при загрузке профиля врача');
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const closeDoctorModal = () => {
    setShowDoctorModal(false);
    setSelectedDoctor(null);
  };

  const getSpecializationIcon = (specialization) => {
    const icons = {
      'Терапевт': '🩺',
      'Кардиолог': '❤️',
      'Невролог': '🧠',
      'Офтальмолог': '👁️',
      'Дерматолог': '🔬',
      'Ортопед': '🦴',
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
      <div className="doctors">
        <div className="doctors__loading">
          <div className="loading-spinner"></div>
          <p>Загрузка врачей...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doctors">
        <div className="doctors__error">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={fetchDoctors} className="btn btn--primary">
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="doctors">
      <div className="doctors__header">
        <h1>Наши врачи</h1>
        <p>Найдите подходящего специалиста для решения ваших проблем со здоровьем</p>
      </div>

      <div className="doctors__filters">
        <div className="doctors__search">
          <input
            type="text"
            placeholder="Поиск по имени, специализации или городу..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="doctors__search-input"
          />
        </div>

        <div className="doctors__filter-hint">
          <p>Выберите услугу, затем специализацию и регион для точного поиска</p>
          <button 
            onClick={resetFilters}
            className="doctors__reset-btn"
            disabled={selectedService === 'all' && selectedSpecialization === 'all' && selectedRegion === 'all' && !searchQuery}
          >
            Сбросить фильтры
          </button>
        </div>

        <div className="doctors__filter-controls">
          <div className="doctors__filter-group">
            <label className="doctors__filter-label">Услуга</label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              className="doctors__filter-select"
            >
              {services.map(service => (
                <option key={service} value={service}>
                  {service === 'all' ? 'Все услуги' : service}
                </option>
              ))}
            </select>
          </div>

          <div className="doctors__filter-group">
            <label className="doctors__filter-label">Специализация</label>
            <select
              value={selectedSpecialization}
              onChange={(e) => setSelectedSpecialization(e.target.value)}
              className="doctors__filter-select"
              disabled={selectedService === 'all'}
            >
              <option value="all">Все специализации</option>
              {selectedService !== 'all' && specializationsByService[selectedService]?.map(spec => (
                <option key={spec} value={spec}>
                  {spec}
                </option>
              ))}
            </select>
          </div>

          <div className="doctors__filter-group">
            <label className="doctors__filter-label">Регион</label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              className="doctors__filter-select"
              disabled={selectedSpecialization === 'all'}
            >
              <option value="all">Все регионы</option>
              {selectedSpecialization !== 'all' && regions.filter(region => region !== 'all').map(region => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="doctors__stats">
        <p>Найдено врачей: <strong>{filteredDoctors.length}</strong></p>
      </div>

      {filteredDoctors.length === 0 ? (
        <div className="doctors__empty">
          <div className="doctors__empty-icon"></div>
          <h3>Врачи не найдены</h3>
          <p>Попробуйте изменить параметры поиска или фильтры</p>
        </div>
      ) : (
        <div className="doctors__grid">
          {filteredDoctors.map(doctor => (
            <div key={doctor.id} className="doctor-card">
              <div className="doctor-card__header">
                <div className="doctor-card__avatar">
                  {doctor.avatar ? (
                    <img src={doctor.avatar} alt={doctor.full_name} />
                  ) : (
                    <div className="doctor-card__avatar-placeholder">
                      {doctor.initials}
                    </div>
                  )}
                </div>
                <div className="doctor-card__info">
                  <h3 className="doctor-card__name">{doctor.full_name}</h3>
                  <p className="doctor-card__specialization">
                    {getSpecializationIcon(doctor.specialization)} {doctor.specialization}
                  </p>
                </div>
              </div>

              <div className="doctor-card__details">
                {doctor.region && (
                  <p className="doctor-card__location">
                    📍 {doctor.city ? `${doctor.city}, ${doctor.region}` : doctor.region}
                  </p>
                )}
                {doctor.experience && (
                  <p className="doctor-card__experience">
                    💼 {doctor.experience.length > 100 
                      ? `${doctor.experience.substring(0, 100)}...` 
                      : doctor.experience}
                  </p>
                )}
                {doctor.languages && doctor.languages.length > 0 && (
                  <p className="doctor-card__languages">
                    🌍 {doctor.languages.join(', ')}
                  </p>
                )}
              </div>

              <div className="doctor-card__actions">
                <button 
                  onClick={() => openDoctorProfile(doctor.id)}
                  className="btn btn--primary btn--small"
                >
                  Посмотреть профиль
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Модальное окно профиля врача */}
      {showDoctorModal && selectedDoctor && (
        <div className="doctor-modal" onClick={closeDoctorModal}>
          <div className="doctor-modal__content" onClick={(e) => e.stopPropagation()}>
            <button className="doctor-modal__close" onClick={closeDoctorModal}>
              ✕
            </button>
            
            <div className="doctor-modal__header">
              <div className="doctor-modal__avatar">
                {selectedDoctor.avatar ? (
                  <img src={selectedDoctor.avatar} alt={selectedDoctor.full_name} />
                ) : (
                  <div className="doctor-modal__avatar-placeholder">
                    {selectedDoctor.initials}
                  </div>
                )}
              </div>
              <div className="doctor-modal__info">
                <h2>{selectedDoctor.full_name}</h2>
                <p className="doctor-modal__specialization">
                  {getSpecializationIcon(selectedDoctor.specialization)} {selectedDoctor.specialization}
                </p>
                {selectedDoctor.license_number && (
                  <p className="doctor-modal__license">
                    Лицензия: {selectedDoctor.license_number}
                  </p>
                )}
              </div>
            </div>

            <div className="doctor-modal__body">
              {selectedDoctor.region && (
                <div className="doctor-modal__section">
                  <h3>📍 Местоположение</h3>
                  <p>{selectedDoctor.city ? `${selectedDoctor.city}, ${selectedDoctor.region}` : selectedDoctor.region}</p>
                  {selectedDoctor.address && <p>{selectedDoctor.address}</p>}
                </div>
              )}

              {selectedDoctor.experience && (
                <div className="doctor-modal__section">
                  <h3>💼 Опыт работы</h3>
                  <p>{selectedDoctor.experience}</p>
                </div>
              )}

              {selectedDoctor.education && (
                <div className="doctor-modal__section">
                  <h3>🎓 Образование</h3>
                  <p>{selectedDoctor.education}</p>
                </div>
              )}

              {selectedDoctor.languages && selectedDoctor.languages.length > 0 && (
                <div className="doctor-modal__section">
                  <h3>🌍 Языки</h3>
                  <p>{selectedDoctor.languages.join(', ')}</p>
                </div>
              )}

              {selectedDoctor.additional_info && (
                <div className="doctor-modal__section">
                  <h3>ℹ️ Дополнительная информация</h3>
                  <p>{selectedDoctor.additional_info}</p>
                </div>
              )}

              {selectedDoctor.phone && (
                <div className="doctor-modal__section">
                  <h3>📞 Контакты</h3>
                  <p>{selectedDoctor.phone}</p>
                </div>
              )}

              <div className="doctor-modal__section">
                <h3>⭐ Отзывы</h3>
                <div className="doctor-modal__reviews">
                  <p>Отзывы пока отсутствуют</p>
                </div>
              </div>
            </div>

            <div className="doctor-modal__footer">
              <button className="btn btn--secondary" onClick={closeDoctorModal}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Doctors; 