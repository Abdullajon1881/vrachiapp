import React, { useState, useEffect } from 'react';
import './DoctorApplication.scss';

const DoctorApplication = () => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    specialization: '',
    region: '',
    city: '',
    district: '',
    languages: [],
    experience: '',
    education: '',
    license_number: '',
    additional_info: '',
    // Поля профиля
    date_of_birth: '',
    gender: '',
    phone: '',
    address: '',
    medical_info: '',
    emergency_contact: '',
    // Файлы
    photo: null,
    diploma: null,
    license: null
  });

  const [regions, setRegions] = useState([]);
  const [cities, setCities] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('success');

  const specializations = [
    'Терапевт',
    'Кардиолог',
    'Невролог',
    'Офтальмолог',
    'Отоларинголог',
    'Хирург',
    'Ортопед',
    'Дерматолог',
    'Педиатр',
    'Гинеколог',
    'Уролог',
    'Психиатр',
    'Стоматолог',
    'Онколог',
    'Эндокринолог',
    'Гастроэнтеролог',
    'Пульмонолог',
    'Ревматолог',
    'Аллерголог',
    'Инфекционист'
  ];

  const languages = [
    { code: 'ru', name: 'Русский' },
    { code: 'uz', name: 'Узбекский' },
    { code: 'en', name: 'Английский' },
    { code: 'kk', name: 'Казахский' },
    { code: 'ky', name: 'Киргизский' },
    { code: 'tg', name: 'Таджикский' },
    { code: 'tk', name: 'Туркменский' }
  ];

  useEffect(() => {
    loadRegions();
  }, []);

  const loadRegions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/auth/regions/');
      if (response.ok) {
        const data = await response.json();
        setRegions(data);
      }
    } catch (error) {
      console.error('Ошибка загрузки регионов:', error);
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
      console.error('Ошибка загрузки городов:', error);
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
      console.error('Ошибка загрузки районов:', error);
    }
  };

  const loadDistrictsByCity = async (cityId) => {
    try {
      // Сначала пытаемся найти районы конкретного города
      const response = await fetch(`http://localhost:8000/api/auth/districts/?city_id=${cityId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          // Если у города есть свои районы, показываем их
          setDistricts(data);
        } else {
          // Если у города нет своих районов, показываем районы региона
          if (formData.region) {
            loadDistricts(formData.region);
          }
        }
      }
    } catch (error) {
      console.error('Ошибка загрузки районов по городу:', error);
      // В случае ошибки показываем районы региона
      if (formData.region) {
        loadDistricts(formData.region);
      }
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Если изменился регион, загружаем города и районы
    if (name === 'region' && value) {
      loadCities(value);
      loadDistricts(value);
      // Очищаем город и район при смене региона
      setFormData(prev => ({
        ...prev,
        city: '',
        district: ''
      }));
    }
    
    // Если изменился город, загружаем районы для этого города
    if (name === 'city' && value) {
      loadDistrictsByCity(value);
      // Очищаем выбранный район
      setFormData(prev => ({
        ...prev,
        district: ''
      }));
    }
  };

  const handleLanguageChange = (e) => {
    const languageCode = e.target.value;
    setFormData(prev => ({
      ...prev,
      languages: prev.languages.includes(languageCode)
        ? prev.languages.filter(lang => lang !== languageCode)
        : [...prev.languages, languageCode]
    }));
  };

  const handleFileChange = (e, field) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({
        ...prev,
        [field]: file
      }));
    }
  };

  const showMessage = (text, type = 'success') => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formDataToSend = new FormData();

      // Добавляем все поля формы
      Object.keys(formData).forEach(key => {
        if (key === 'languages') {
          formDataToSend.append(key, JSON.stringify(formData[key]));
        } else if (key === 'region' || key === 'city' || key === 'district') {
          // Для региона, города и района отправляем ID
          if (formData[key]) {
            formDataToSend.append(key, formData[key]);
          }
        } else if (key === 'date_of_birth' && formData[key]) {
          // Форматируем дату
          formDataToSend.append(key, formData[key]);
        } else if (formData[key] !== null && formData[key] !== '' && key !== 'photo' && key !== 'diploma' && key !== 'license') {
          formDataToSend.append(key, formData[key]);
        }
      });

      // Добавляем файлы
      if (formData.photo) formDataToSend.append('photo', formData.photo);
      if (formData.diploma) formDataToSend.append('diploma', formData.diploma);
      if (formData.license) formDataToSend.append('license', formData.license);

      console.log('Отправляем данные:', Object.fromEntries(formDataToSend));

      const response = await fetch('http://localhost:8000/api/auth/doctor-applications/', {
        method: 'POST',
        credentials: 'include',
        body: formDataToSend
      });

      if (response.ok) {
        const result = await response.json();
        showMessage(result.message || 'Заявка успешно отправлена!');
        setFormData({
          first_name: '',
          last_name: '',
          specialization: '',
          region: '',
          city: '',
          district: '',
          languages: [],
          experience: '',
          education: '',
          license_number: '',
          additional_info: '',
          // Поля профиля
          date_of_birth: '',
          gender: '',
          phone: '',
          address: '',
          medical_info: '',
          emergency_contact: '',
          // Файлы
          photo: null,
          diploma: null,
          license: null
        });
      } else {
        const error = await response.json();
        console.error('Ошибка сервера:', error);
        showMessage(error.message || 'Ошибка отправки заявки', 'error');
      }
    } catch (error) {
      console.error('Ошибка соединения:', error);
      showMessage('Ошибка соединения с сервером', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="doctor-application">
      {message && (
        <div className={`doctor-application__message ${messageType}`}>
          {message}
        </div>
      )}

      <div className="doctor-application__content">
        <div className="doctor-application__header">
          <h1>Подача заявки на роль врача</h1>
          <p>Заполните форму ниже, чтобы стать врачом в нашей системе. Мы рассмотрим вашу заявку в течение 1-3 рабочих дней.</p>
        </div>

        <form className="doctor-application__form" onSubmit={handleSubmit}>
          <div className="doctor-application__section">
            <h3 className="doctor-application__section-title">Данные для заявки</h3>
            <p className="doctor-application__section-subtitle">Заполните форму ниже и предоставьте необходимые документы</p>
            
            <div className="doctor-application__form-row">
              <div className="doctor-application__form-group">
                <label htmlFor="first_name" className="required">Имя</label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__input"
                  placeholder="Иван"
                />
              </div>
              
              <div className="doctor-application__form-group">
                <label htmlFor="last_name" className="required">Фамилия</label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__input"
                  placeholder="Иванов"
                />
              </div>
            </div>

            <div className="doctor-application__form-row">
              <div className="doctor-application__form-group">
                <label htmlFor="specialization" className="required">Специализация</label>
                <select
                  id="specialization"
                  name="specialization"
                  value={formData.specialization}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__select"
                >
                  <option value="">Выберите специализацию</option>
                  <option value="Терапевт">Терапевт</option>
                  <option value="Кардиолог">Кардиолог</option>
                  <option value="Невролог">Невролог</option>
                  <option value="Офтальмолог">Офтальмолог</option>
                  <option value="Дерматолог">Дерматолог</option>
                  <option value="Ортопед">Ортопед</option>
                  <option value="Хирург">Хирург</option>
                  <option value="Педиатр">Педиатр</option>
                  <option value="Гинеколог">Гинеколог</option>
                  <option value="Уролог">Уролог</option>
                  <option value="Психиатр">Психиатр</option>
                  <option value="Ревматолог">Ревматолог</option>
                  <option value="Эндокринолог">Эндокринолог</option>
                  <option value="Гастроэнтеролог">Гастроэнтеролог</option>
                  <option value="Пульмонолог">Пульмонолог</option>
                  <option value="Онколог">Онколог</option>
                  <option value="Другое">Другое</option>
                </select>
              </div>
            </div>

            <div className="doctor-application__form-row">
              <div className="doctor-application__form-group">
                <label htmlFor="region" className="required">Регион</label>
                <select
                  id="region"
                  name="region"
                  value={formData.region}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__select"
                >
                  <option value="">Выберите регион</option>
                  {regions.map(region => (
                    <option key={region.id} value={region.id}>
                      {region.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="doctor-application__form-group">
                <label htmlFor="city" className="required">Город</label>
                <select
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__select"
                  disabled={!formData.region}
                >
                  <option value="">Выберите город</option>
                  {cities.map(city => (
                    <option key={city.id} value={city.id}>
                      {city.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="doctor-application__form-group">
                <label htmlFor="district" className="required">Район практики</label>
                <select
                  id="district"
                  name="district"
                  value={formData.district}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__select"
                  disabled={!formData.region}
                >
                  <option value="">Выберите район</option>
                  {districts.map(district => (
                    <option key={district.id} value={district.id}>
                      {district.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="doctor-application__form-row">
              <div className="doctor-application__form-group">
                <label htmlFor="phone" className="required">Телефон</label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  required
                  className="doctor-application__input"
                  placeholder="+998 XX XXX XX XX"
                />
              </div>
              
              <div className="doctor-application__form-group">
                <label htmlFor="date_of_birth">Дата рождения</label>
                <input
                  type="date"
                  id="date_of_birth"
                  name="date_of_birth"
                  value={formData.date_of_birth}
                  onChange={handleInputChange}
                  className="doctor-application__input"
                />
              </div>
              
              <div className="doctor-application__form-group">
                <label htmlFor="gender">Пол</label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleInputChange}
                  className="doctor-application__select"
                >
                  <option value="">Выберите пол</option>
                  <option value="male">Мужской</option>
                  <option value="female">Женский</option>
                  <option value="other">Другой</option>
                </select>
              </div>
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="address">Адрес</label>
              <textarea
                id="address"
                name="address"
                value={formData.address}
                onChange={handleInputChange}
                className="doctor-application__textarea"
                placeholder="Введите полный адрес"
                rows="3"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="medical_info">Медицинская информация</label>
              <textarea
                id="medical_info"
                name="medical_info"
                value={formData.medical_info}
                onChange={handleInputChange}
                className="doctor-application__textarea"
                placeholder="Информация о заболеваниях, аллергиях и т.д."
                rows="3"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="emergency_contact">Экстренный контакт</label>
              <input
                type="tel"
                id="emergency_contact"
                name="emergency_contact"
                value={formData.emergency_contact}
                onChange={handleInputChange}
                className="doctor-application__input"
                placeholder="+998 XX XXX XX XX"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="languages" className="required">Языки консультаций</label>
              <div className="doctor-application__checkbox-group">
                {['ru', 'uz', 'en'].map(lang => (
                  <label key={lang} className="doctor-application__checkbox">
                    <input
                      type="checkbox"
                      value={lang}
                      checked={formData.languages.includes(lang)}
                      onChange={handleLanguageChange}
                    />
                    <span className="doctor-application__checkbox-text">
                      {lang === 'ru' ? 'Русский' : lang === 'uz' ? 'Узбекский' : 'Английский'}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="experience" className="required">Опыт работы</label>
              <textarea
                id="experience"
                name="experience"
                value={formData.experience}
                onChange={handleInputChange}
                required
                className="doctor-application__textarea"
                placeholder="Опишите ваш опыт работы в медицине"
                rows="4"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="education" className="required">Образование</label>
              <textarea
                id="education"
                name="education"
                value={formData.education}
                onChange={handleInputChange}
                required
                className="doctor-application__textarea"
                placeholder="Укажите ваше медицинское образование"
                rows="4"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="license_number" className="required">Номер лицензии</label>
              <input
                type="text"
                id="license_number"
                name="license_number"
                value={formData.license_number}
                onChange={handleInputChange}
                required
                className="doctor-application__input"
                placeholder="Введите номер лицензии"
              />
            </div>

            <div className="doctor-application__form-group">
              <label htmlFor="additional_info">Дополнительная информация</label>
              <textarea
                id="additional_info"
                name="additional_info"
                value={formData.additional_info}
                onChange={handleInputChange}
                className="doctor-application__textarea"
                placeholder="Любая дополнительная информация о вас"
                rows="4"
              />
            </div>
          </div>

          <div className="doctor-application__section">
            <h3 className="doctor-application__section-title">Загрузка документов</h3>
            <p className="doctor-application__section-subtitle">Загрузите необходимые документы для подтверждения вашей квалификации</p>
            
            <div className="doctor-application__file-section">
              <div className="doctor-application__file-group">
                <label className="doctor-application__file-label required">Фотография</label>
                <div className={`doctor-application__file-upload ${formData.photo ? 'has-file' : ''}`}>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleFileChange(e, 'photo')}
                    className="doctor-application__file-input"
                    required
                  />
                  <div className="doctor-application__file-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <polyline points="7,10 12,15 17,10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <line x1="12" y1="15" x2="12" y2="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span>Нажмите для загрузки</span>
                    <small>Фото для профиля</small>
                  </div>
                </div>
                {formData.photo && (
                  <div className="doctor-application__file-preview">
                    <img src={URL.createObjectURL(formData.photo)} alt="Preview" />
                    <div className="file-name">{formData.photo.name}</div>
                  </div>
                )}
              </div>

              <div className="doctor-application__file-group">
                <label className="doctor-application__file-label required">Скан диплома</label>
                <div className={`doctor-application__file-upload ${formData.diploma ? 'has-file' : ''}`}>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange(e, 'diploma')}
                    className="doctor-application__file-input"
                    required
                  />
                  <div className="doctor-application__file-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span>Нажмите для загрузки</span>
                    <small>PDF, JPG или PNG</small>
                  </div>
                </div>
                {formData.diploma && (
                  <div className="doctor-application__file-preview">
                    <div className="file-name">{formData.diploma.name}</div>
                  </div>
                )}
              </div>

              <div className="doctor-application__file-group">
                <label className="doctor-application__file-label required">Скан лицензии</label>
                <div className={`doctor-application__file-upload ${formData.license ? 'has-file' : ''}`}>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => handleFileChange(e, 'license')}
                    className="doctor-application__file-input"
                    required
                  />
                  <div className="doctor-application__file-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span>Нажмите для загрузки</span>
                    <small>PDF, JPG или PNG</small>
                  </div>
                </div>
                {formData.license && (
                  <div className="doctor-application__file-preview">
                    <div className="file-name">{formData.license.name}</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="doctor-application__actions">
            <button
              type="submit"
              className="doctor-application__submit"
              disabled={loading}
            >
              {loading ? 'Отправка...' : 'Отправить заявку'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DoctorApplication; 