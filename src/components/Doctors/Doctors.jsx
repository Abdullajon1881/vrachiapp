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
  const [userData, setUserData] = useState(null);



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
      'Психолог',
      'Психиатр'
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
    // Получаем данные пользователя
    const fetchUserData = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/auth/current-user/', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setUserData(data);
          
          // Загружаем врачей только если пользователь - пациент
          if (data.role === 'patient') {
            fetchDoctors();
          } else {
            setLoading(false);
            setError('Доступ запрещен. Только пациенты могут просматривать список врачей.');
          }
        } else {
          setLoading(false);
          setError('Ошибка получения данных пользователя');
        }
      } catch (error) {
        setLoading(false);
        setError('Ошибка соединения с сервером');
      }
    };
    
    fetchUserData();
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
            doctor.specialization.toLowerCase() === spec.toLowerCase()
          )
        );
      }
    }

    // Фильтр по специализации (второй уровень)
    if (selectedSpecialization !== 'all') {
      filtered = filtered.filter(doctor => 
        doctor.specialization && 
        doctor.specialization.toLowerCase() === selectedSpecialization.toLowerCase()
      );
    }

    // Фильтр по региону (третий уровень)
    if (selectedRegion !== 'all') {
      filtered = filtered.filter(doctor => {
        // Проверяем, совпадает ли регион врача с выбранным регионом
        if (doctor.region && doctor.region.toLowerCase().includes(selectedRegion.toLowerCase())) {
          return true;
        }
        
        // Проверяем, находится ли город врача в выбранном регионе
        if (doctor.city) {
          const cityRegionMap = {
            'Фергана': 'Ферганская область',
            'Андижан': 'Андижанская область',
            'Наманган': 'Наманганская область',
            'Ташкент': 'Город Ташкент',
            'Самарканд': 'Город Самарканд',
            'Бухара': 'Город Бухара',
            'Карши': 'Кашкадарьинская область',
            'Термез': 'Сурхандарьинская область',
            'Гулистан': 'Сырдарьинская область',
            'Джизак': 'Джизакская область',
            'Навои': 'Навоийская область',
            'Ургенч': 'Хорезмская область',
            'Нукус': 'Республика Каракалпакстан'
          };
          
          const cityRegion = cityRegionMap[doctor.city];
          if (cityRegion && cityRegion.toLowerCase().includes(selectedRegion.toLowerCase())) {
            return true;
          }
        }
        
        return false;
      });
    }

    // Поиск по имени (работает независимо от фильтров)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(doctor => {
        // Поиск по имени
        if (doctor.full_name.toLowerCase().includes(query)) {
          return true;
        }
        
        // Поиск по специализации
        if (doctor.specialization && doctor.specialization.toLowerCase().includes(query)) {
          return true;
        }
        
        // Поиск по городу
        if (doctor.city && doctor.city.toLowerCase().includes(query)) {
          return true;
        }
        
        // Поиск по региону
        if (doctor.region && doctor.region.toLowerCase().includes(query)) {
          return true;
        }
        
        // Поиск по региону через город
        if (doctor.city) {
          const cityRegionMap = {
            'Фергана': 'Ферганская область',
            'Андижан': 'Андижанская область',
            'Наманган': 'Наманганская область',
            'Ташкент': 'Город Ташкент',
            'Самарканд': 'Город Самарканд',
            'Бухара': 'Город Бухара',
            'Карши': 'Кашкадарьинская область',
            'Термез': 'Сурхандарьинская область',
            'Гулистан': 'Сырдарьинская область',
            'Джизак': 'Джизакская область',
            'Навои': 'Навоийская область',
            'Ургенч': 'Хорезмская область',
            'Нукус': 'Республика Каракалпакстан'
          };
          
          const cityRegion = cityRegionMap[doctor.city];
          if (cityRegion && cityRegion.toLowerCase().includes(query)) {
            return true;
          }
        }
        
        return false;
      });
    }

    setFilteredDoctors(filtered);
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
          <h2>Доступ ограничен</h2>
          <p>{error}</p>
          {userData?.role === 'doctor' && (
            <p>Врачи не могут просматривать список других врачей.</p>
          )}
          {userData?.role === 'admin' && (
            <p>Администраторы могут управлять врачами через админ панель.</p>
          )}
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
            <div 
              key={doctor.id} 
              className="doctor-card"
            >
              <div className="doctor-card__header">
                <div className="doctor-card__avatar">
                  {doctor.avatar ? (
                    <img src={doctor.avatar} alt={doctor.full_name} />
                  ) : (
                    <div className="doctor-card__avatar-placeholder">
                      {doctor.first_name && doctor.last_name 
                        ? `${doctor.first_name[0]}${doctor.last_name[0]}`.toUpperCase()
                        : doctor.first_name?.[0]?.toUpperCase() || 'U'}
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
            </div>
          ))}
        </div>
      )}

    </div>
  );
};

export default Doctors; 