import React, { useState, useEffect } from 'react';
import './Profile.scss';

const Profile = ({ userData }) => {
  const [profile, setProfile] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    region: null,
    city: null,
    district: null,
    address: '',
    medical_info: '',
    // Поля врача
    specialization: '',
    experience: '',
    education: '',
    license_number: '',
    languages: [],
    additional_info: ''
  });
  
  const [regions, setRegions] = useState([]);
  const [cities, setCities] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('success');
  const [isMessageVisible, setIsMessageVisible] = useState(false);

  // Проверяем, является ли пользователь врачом
  const isDoctor = userData?.role === 'doctor';

  // Загружаем данные профиля
  useEffect(() => {
    loadProfile();
    loadRegions();
  }, []);

  // Функция для показа сообщений с анимацией
  const showMessage = (text, type = 'success', duration = 8000) => {
    setMessage(text);
    setMessageType(type);
    setIsMessageVisible(true);
    
    setTimeout(() => {
      setIsMessageVisible(false);
      setTimeout(() => {
        setMessage('');
      }, 300); // Ждем окончания анимации исчезновения
    }, duration);
  };

  const loadProfile = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/profile/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Данные профиля:', data); // Отладочная информация
        
        setProfile({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          phone: data.phone || '',
          region: data.region?.id || null,
          city: data.city?.id || null,
          district: data.district?.id || null,
          address: data.address || '',
          medical_info: data.medical_info || '',
          // Поля врача
          specialization: data.specialization || '',
          experience: data.experience || '',
          education: data.education || '',
          license_number: data.license_number || '',
          languages: data.languages || [],
          additional_info: data.additional_info || ''
        });
        
        console.log('Состояние профиля после установки:', {
          first_name: data.first_name,
          last_name: data.last_name,
          specialization: data.specialization,
          experience: data.experience,
          education: data.education,
          license_number: data.license_number,
          languages: data.languages,
          additional_info: data.additional_info
        });
        
        // Загружаем города и районы если есть регион
        if (data.region?.id) {
          loadCities(data.region.id);
          loadDistricts(data.region.id);
        }
      } else {
        showMessage('Ошибка загрузки профиля', 'error');
      }
    } catch (error) {
      showMessage('Ошибка соединения с сервером', 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadRegions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/regions/');
      if (response.ok) {
        const data = await response.json();
        setRegions(data);
      }
    } catch (error) {
      // Ошибка загрузки регионов
    }
  };

  const loadCities = async (regionId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/cities/?region_id=${regionId}`);
      if (response.ok) {
        const data = await response.json();
        setCities(data);
      }
    } catch (error) {
      // Ошибка загрузки городов
    }
  };

  const loadDistricts = async (regionId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/districts/?region_id=${regionId}`);
      if (response.ok) {
        const data = await response.json();
        setDistricts(data);
      }
    } catch (error) {
      // Ошибка загрузки районов
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfile(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRegionChange = (e) => {
    const regionId = e.target.value;
    setProfile(prev => ({
      ...prev,
      region: regionId,
      city: null,
      district: null
    }));
    
    if (regionId) {
      loadCities(regionId);
      loadDistricts(regionId);
    } else {
      setCities([]);
      setDistricts([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/api/auth/profile/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(profile)
      });

      if (response.ok) {
        const result = await response.json();
        showMessage(result.message || 'Профиль успешно обновлен!', 'success');
      } else {
        const error = await response.json();
        showMessage('Ошибка: ' + (error.message || JSON.stringify(error)), 'error');
      }
    } catch (error) {
      showMessage('Ошибка соединения с сервером', 'error');
    } finally {
      setSaving(false);
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="profile__loading">
          <div className="profile__spinner"></div>
          <p>Загрузка профиля...</p>
        </div>
      );
    }

    // Если пользователь врач, показываем только информацию о враче
    if (isDoctor) {
      console.log('Рендерим профиль врача:', {
        isDoctor,
        profile,
        specialization: profile.specialization,
        experience: profile.experience,
        languages: profile.languages
      });
      
      return (
        <div className="profile">
          {message && (
            <div className={`profile__message ${messageType} ${isMessageVisible ? 'profile__message--visible' : ''}`}>
              {message}
            </div>
          )}
          
          <div className="profile__container">
            <div className="profile__header">
              <h1 className="profile__title">Профиль врача</h1>
              <p className="profile__subtitle">Информация заполнена автоматически из заявки</p>
            </div>

            <div className="profile__section">
              <h2 className="profile__section-title">Основная информация</h2>
              
              <div className="profile__row">
                <div className="profile__field">
                  <label className="profile__label">Специализация</label>
                  <input
                    type="text"
                    name="specialization"
                    value={profile.specialization}
                    className="profile__input profile__input--readonly"
                    readOnly
                    disabled
                  />
                </div>
                
                <div className="profile__field">
                  <label className="profile__label">Номер лицензии</label>
                  <input
                    type="text"
                    name="license_number"
                    value={profile.license_number}
                    className="profile__input profile__input--readonly"
                    readOnly
                    disabled
                  />
                </div>
              </div>

              <div className="profile__field">
                <label className="profile__label">Языки консультаций</label>
                <div className="profile__languages">
                  {profile.languages.map(lang => (
                    <span key={lang} className="profile__language-tag">
                      {lang === 'ru' ? 'Русский' : lang === 'uz' ? 'Узбекский' : 'Английский'}
                    </span>
                  ))}
                </div>
              </div>

              <div className="profile__field">
                <label className="profile__label">Опыт работы</label>
                <textarea
                  name="experience"
                  value={profile.experience}
                  className="profile__textarea profile__textarea--readonly"
                  readOnly
                  disabled
                  rows={4}
                />
              </div>

              <div className="profile__field">
                <label className="profile__label">Образование</label>
                <textarea
                  name="education"
                  value={profile.education}
                  className="profile__textarea profile__textarea--readonly"
                  readOnly
                  disabled
                  rows={4}
                />
              </div>

              {profile.additional_info && (
                <div className="profile__field">
                  <label className="profile__label">Дополнительная информация</label>
                  <textarea
                    name="additional_info"
                    value={profile.additional_info}
                    className="profile__textarea profile__textarea--readonly"
                    readOnly
                    disabled
                    rows={3}
                  />
                </div>
              )}
            </div>

            <div className="profile__info">
              <p className="profile__info-text">
                <strong>Примечание:</strong> Данная информация заполнена автоматически из вашей заявки на роль врача. 
                Для внесения изменений обратитесь к администратору.
              </p>
            </div>
          </div>
        </div>
      );
    }

    // Для обычных пользователей показываем стандартную форму профиля
    return (
      <div className="profile">
        {message && (
          <div className={`profile__message ${messageType} ${isMessageVisible ? 'profile__message--visible' : ''}`}>
            {message}
          </div>
        )}
        
        <div className="profile__container">
          <div className="profile__header">
            <h1 className="profile__title">Профиль пользователя</h1>
            <p className="profile__subtitle">Управление личной информацией</p>
          </div>

          <form className="profile__form" onSubmit={handleSubmit}>
            <div className="profile__section">
              <h2 className="profile__section-title">Личная информация</h2>
              
              <div className="profile__row">
                <div className="profile__field">
                  <label className="profile__label">Имя</label>
                  <input
                    type="text"
                    name="first_name"
                    value={profile.first_name}
                    onChange={handleInputChange}
                    className="profile__input"
                    placeholder="Введите ваше имя"
                  />
                </div>
                
                <div className="profile__field">
                  <label className="profile__label">Фамилия</label>
                  <input
                    type="text"
                    name="last_name"
                    value={profile.last_name}
                    onChange={handleInputChange}
                    className="profile__input"
                    placeholder="Введите вашу фамилию"
                  />
                </div>
              </div>

              <div className="profile__field">
                <label className="profile__label">Номер телефона</label>
                <input
                  type="tel"
                  name="phone"
                  value={profile.phone}
                  onChange={handleInputChange}
                  className="profile__input"
                  placeholder="+998XXXXXXXXX"
                />
              </div>
            </div>

            <div className="profile__section">
              <h2 className="profile__section-title">Адрес</h2>
              
              <div className="profile__row">
                <div className="profile__field">
                  <label className="profile__label">Регион</label>
                  <select
                    name="region"
                    value={profile.region || ''}
                    onChange={handleRegionChange}
                    className="profile__select"
                  >
                    <option value="">Выберите регион</option>
                    {regions.map(region => (
                      <option key={region.id} value={region.id}>
                        {region.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="profile__field">
                  <label className="profile__label">Город</label>
                  <select
                    name="city"
                    value={profile.city || ''}
                    onChange={handleInputChange}
                    className="profile__select"
                    disabled={!profile.region}
                  >
                    <option value="">Выберите город</option>
                    {cities.map(city => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="profile__row">
                <div className="profile__field">
                  <label className="profile__label">Район</label>
                  <select
                    name="district"
                    value={profile.district || ''}
                    onChange={handleInputChange}
                    className="profile__select"
                    disabled={!profile.region}
                  >
                    <option value="">Выберите район</option>
                    {districts.map(district => (
                      <option key={district.id} value={district.id}>
                        {district.name}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="profile__field">
                  <label className="profile__label">Адрес</label>
                  <input
                    type="text"
                    name="address"
                    value={profile.address}
                    onChange={handleInputChange}
                    className="profile__input"
                    placeholder="Улица, дом, квартира"
                  />
                </div>
              </div>
            </div>

            <div className="profile__section">
              <h2 className="profile__section-title">Медицинская информация</h2>
              
              <div className="profile__field">
                <label className="profile__label">Медицинская информация</label>
                <textarea
                  name="medical_info"
                  value={profile.medical_info}
                  onChange={handleInputChange}
                  className="profile__textarea"
                  placeholder="Опишите ваши заболевания, аллергии, принимаемые лекарства и т.д."
                  rows={4}
                />
              </div>
            </div>

            <div className="profile__actions">
              <button
                type="submit"
                className="profile__submit"
                disabled={saving}
              >
                {saving ? 'Сохранение...' : 'Сохранить изменения'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  return renderContent();
};

export default Profile; 