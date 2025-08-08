import React, { useState, useEffect } from 'react';
import './Profile.scss';

const Profile = () => {
  const [userData, setUserData] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [regions, setRegions] = useState([]);
  const [cities, setCities] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [isEditingAvatar, setIsEditingAvatar] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [avatarFile, setAvatarFile] = useState(null);

  useEffect(() => {
    fetchUserData();
    fetchRegions();
  }, []);

  const fetchUserData = async () => {
    try {
      const response = await fetch('https://healzy.uz/api/auth/current-user/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setUserData(data);
        setProfileData(data.profile);
        setFormData({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          phone: data.profile?.phone || '',
          date_of_birth: data.profile?.date_of_birth || '',
          gender: data.profile?.gender || '',
          region: data.profile?.region?.id || '',
          city: data.profile?.city?.id || '',
          district: data.profile?.district?.id || '',
          address: data.profile?.address || '',
          medical_info: data.profile?.medical_info || '',
          emergency_contact: data.profile?.emergency_contact || ''
        });
        setAvatarUrl(data.avatar || '');
        
        // Загружаем города и районы если есть регион
        if (data.profile?.region?.id) {
          await fetchCities(data.profile.region.id);
          await fetchDistricts(data.profile.region.id);
        }
      } else {
        setError('Ошибка загрузки данных профиля');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const fetchRegions = async () => {
    try {
      const response = await fetch('https://healzy.uz/api/auth/regions/');
      if (response.ok) {
        const data = await response.json();
        setRegions(data);
      }
    } catch (err) {
      console.error('Ошибка загрузки регионов:', err);
    }
  };

  const fetchCities = async (regionId) => {
    if (!regionId) {
      setCities([]);
      return;
    }
    try {
      const response = await fetch(`https://healzy.uz/api/auth/cities/?region_id=${regionId}`);
      if (response.ok) {
        const data = await response.json();
        setCities(data);
        
        // Если у пользователя есть город, устанавливаем его
        if (userData?.profile?.city?.id) {
          setFormData(prev => ({
            ...prev,
            city: userData.profile.city.id
          }));
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки городов:', err);
    }
  };

  const fetchDistricts = async (regionId) => {
    if (!regionId) {
      setDistricts([]);
      return;
    }
    try {
      const response = await fetch(`https://healzy.uz/api/auth/districts/?region_id=${regionId}`);
      if (response.ok) {
        const data = await response.json();
        setDistricts(data);
        
        // Если у пользователя есть район, устанавливаем его
        if (userData?.profile?.district?.id) {
          setFormData(prev => ({
            ...prev,
            district: userData.profile.district.id
          }));
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки районов:', err);
    }
  };

  const fetchDistrictsByCity = async (cityId) => {
    if (!cityId) {
      setDistricts([]);
      return;
    }
    try {
      // Сначала пытаемся найти районы конкретного города
      const response = await fetch(`https://healzy.uz/api/auth/districts/?city_id=${cityId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          // Если у города есть свои районы, показываем их
          setDistricts(data);
        } else {
          // Если у города нет своих районов, показываем районы региона
          if (formData.region) {
            fetchDistricts(formData.region);
          }
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки районов по городу:', err);
      // В случае ошибки показываем районы региона
      if (formData.region) {
        fetchDistricts(formData.region);
      }
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Загружаем города при изменении региона
    if (name === 'region') {
      fetchCities(value);
      fetchDistricts(value);
      setFormData(prev => ({
        ...prev,
        city: '',
        district: ''
      }));
    }

    // Загружаем районы при изменении города
    if (name === 'city') {
      fetchDistrictsByCity(value);
      setFormData(prev => ({
        ...prev,
        district: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('https://healzy.uz/api/auth/profile/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const data = await response.json();
        setUserData(data);
        setIsEditing(false);
        setError(null);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Ошибка сохранения профиля');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarSubmit = async () => {
    if (!avatarFile) {
      setError('Пожалуйста, выберите файл аватарки');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('avatar', avatarFile);

      const response = await fetch('https://healzy.uz/api/auth/profile/', {
        method: 'PUT',
        credentials: 'include',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setUserData(data);
        setIsEditingAvatar(false);
        setAvatarFile(null);
        setError(null);
        // Обновляем данные в localStorage
        localStorage.setItem('user', JSON.stringify(data));
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Ошибка сохранения аватарки');
      }
    } catch (err) {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="profile">
        <div className="profile__loading">
          <div className="loading-spinner"></div>
          <p>Загрузка профиля...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile">
        <div className="profile__error">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={fetchUserData} className="btn btn--primary">
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile">
      <div className="profile__container">
        {/* Заголовок */}
        <div className="profile__header">
          <div className="profile__avatar">
            {userData?.avatar ? (
              <img src={userData.avatar} alt="Аватар" />
            ) : (
              <div className="profile__avatar-placeholder">
                {userData?.first_name && userData?.last_name 
                  ? `${userData.first_name[0]}${userData.last_name[0]}`.toUpperCase()
                  : userData?.first_name?.[0]?.toUpperCase() || 'U'}
              </div>
            )}
            {/* Кнопка редактирования аватарки для врачей */}
            {userData?.role === 'doctor' && (
              <button 
                className="profile__avatar-edit-btn"
                onClick={() => setIsEditingAvatar(true)}
                title="Изменить аватарку"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            )}
          </div>
          <div className="profile__info">
            <h1 className="profile__name">{userData?.full_name || 'Пользователь'}</h1>
            <p className="profile__email">{userData?.email}</p>
            <div className="profile__role">
              <span className={`role-badge role-badge--${userData?.role}`}>
                {userData?.role === 'patient' ? 'Пациент' : 
                 userData?.role === 'doctor' ? 'Врач' : 'Администратор'}
              </span>
            </div>
          </div>
          <div className="profile__actions">
            {/* Показываем кнопку редактирования только для пациентов и администраторов */}
            {userData?.role !== 'doctor' && (
              !isEditing ? (
                <button 
                  onClick={() => setIsEditing(true)}
                  className="btn btn--primary"
                >
                  Редактировать
                </button>
              ) : (
                <div className="profile__edit-actions">
                  <button 
                    onClick={() => setIsEditing(false)}
                    className="btn btn--secondary"
                  >
                    Отмена
                  </button>
                  <button 
                    onClick={handleSubmit}
                    className="btn btn--primary"
                    disabled={loading}
                  >
                    {loading ? 'Сохранение...' : 'Сохранить'}
                  </button>
                </div>
              )
            )}
            {userData?.role === 'doctor' && (
              <div className="profile__doctor-notice">
                <p>Врачи могут изменять только аватарку. Остальные данные может изменить только администратор.</p>
              </div>
            )}
          </div>
        </div>

        {/* Форма профиля */}
        <div className="profile__content">
          <form onSubmit={handleSubmit} className="profile__form">
            <div className="profile__section">
              <h2 className="profile__section-title">Основная информация</h2>
              <div className="profile__form-grid">
                <div className="profile__form-group">
                  <label htmlFor="first_name">Имя</label>
                  <input
                    type="text"
                    id="first_name"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  />
                </div>
                <div className="profile__form-group">
                  <label htmlFor="last_name">Фамилия</label>
                  <input
                    type="text"
                    id="last_name"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  />
                </div>
                <div className="profile__form-group">
                  <label htmlFor="phone">Телефон</label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  />
                </div>
                <div className="profile__form-group">
                  <label htmlFor="date_of_birth">Дата рождения</label>
                  <input
                    type="date"
                    id="date_of_birth"
                    name="date_of_birth"
                    value={formData.date_of_birth}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  />
                </div>
                <div className="profile__form-group">
                  <label htmlFor="gender">Пол</label>
                  <select
                    id="gender"
                    name="gender"
                    value={formData.gender}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  >
                    <option value="">Выберите пол</option>
                    <option value="male">Мужской</option>
                    <option value="female">Женский</option>
                    <option value="other">Другой</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="profile__section">
              <h2 className="profile__section-title">Адрес</h2>
              <div className="profile__form-grid">
                <div className="profile__form-group">
                  <label htmlFor="region">Регион</label>
                  <select
                    id="region"
                    name="region"
                    value={formData.region}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                  >
                    <option value="">Выберите регион</option>
                    {regions.map(region => (
                      <option key={region.id} value={region.id}>
                        {region.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="profile__form-group">
                  <label htmlFor="city">Город</label>
                  <select
                    id="city"
                    name="city"
                    value={formData.city}
                    onChange={handleInputChange}
                    disabled={!isEditing || !formData.region}
                  >
                    <option value="">Выберите город</option>
                    {cities.map(city => (
                      <option key={city.id} value={city.id}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="profile__form-group">
                  <label htmlFor="district">Район</label>
                  <select
                    id="district"
                    name="district"
                    value={formData.district}
                    onChange={handleInputChange}
                    disabled={!isEditing || !formData.region}
                  >
                    <option value="">Выберите район</option>
                    {districts.map(district => (
                      <option key={district.id} value={district.id}>
                        {district.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="profile__form-group profile__form-group--full">
                  <label htmlFor="address">Адрес</label>
                  <textarea
                    id="address"
                    name="address"
                    value={formData.address}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    rows="3"
                  />
                </div>
              </div>
            </div>

            <div className="profile__section">
              <h2 className="profile__section-title">Медицинская информация</h2>
              <div className="profile__form-grid">
                <div className="profile__form-group profile__form-group--full">
                  <label htmlFor="medical_info">Медицинская информация</label>
                  <textarea
                    id="medical_info"
                    name="medical_info"
                    value={formData.medical_info}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    rows="4"
                    placeholder="Аллергии, хронические заболевания, принимаемые лекарства..."
                  />
                </div>
                <div className="profile__form-group">
                  <label htmlFor="emergency_contact">Экстренный контакт</label>
                  <input
                    type="tel"
                    id="emergency_contact"
                    name="emergency_contact"
                    value={formData.emergency_contact}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    placeholder="+998 XX XXX XX XX"
                  />
                </div>
              </div>
            </div>

            {/* Секция для врачей */}
            {userData?.role === 'doctor' && profileData && (
              <div className="profile__section">
                <h2 className="profile__section-title">Информация врача</h2>
                <div className="profile__form-grid">
                  <div className="profile__form-group">
                    <label>Специализация</label>
                    <div className="profile__info-display">
                      {profileData.specialization || 'Не указана'}
                    </div>
                  </div>
                  <div className="profile__form-group">
                    <label>Номер лицензии</label>
                    <div className="profile__info-display">
                      {profileData.license_number || 'Не указан'}
                    </div>
                  </div>
                  <div className="profile__form-group profile__form-group--full">
                    <label>Образование</label>
                    <div className="profile__info-display">
                      {profileData.education || 'Не указано'}
                    </div>
                  </div>
                  <div className="profile__form-group profile__form-group--full">
                    <label>Опыт работы</label>
                    <div className="profile__info-display">
                      {profileData.experience || 'Не указан'}
                    </div>
                  </div>
                  <div className="profile__form-group">
                    <label>Языки</label>
                    <div className="profile__info-display">
                      {profileData.languages && profileData.languages.length > 0 
                        ? profileData.languages.join(', ') 
                        : 'Не указаны'}
                    </div>
                  </div>
                  {profileData.additional_info && (
                    <div className="profile__form-group profile__form-group--full">
                      <label>Дополнительная информация</label>
                      <div className="profile__info-display">
                        {profileData.additional_info}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Модальное окно для редактирования аватарки */}
      {isEditingAvatar && (
        <div className="profile__modal-overlay">
          <div className="profile__modal">
            <div className="profile__modal-header">
              <h3>Изменить аватарку</h3>
              <button 
                className="profile__modal-close"
                onClick={() => {
                  setIsEditingAvatar(false);
                  setAvatarFile(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="profile__modal-content">
              <div className="profile__form-group">
                <label htmlFor="avatar_file">Выберите файл аватарки</label>
                <input
                  type="file"
                  id="avatar_file"
                  accept="image/*"
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      setAvatarFile(file);
                    }
                  }}
                />
                <small>
                  Выберите изображение (JPG, PNG, GIF). Максимальный размер: 5MB
                </small>
              </div>
              <div className="profile__modal-actions">
                <button 
                  className="btn btn--secondary"
                  onClick={() => {
                    setIsEditingAvatar(false);
                    setAvatarFile(null);
                  }}
                >
                  Отмена
                </button>
                <button 
                  className="btn btn--primary"
                  onClick={handleAvatarSubmit}
                  disabled={loading}
                >
                  {loading ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile; 