import React, { useState, useEffect } from "react";
import "./AdminPanel.scss";

const AdminPanel = ({ updateUserData }) => {
  const [applications, setApplications] = useState([]);
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [regions, setRegions] = useState([]);
  const [cities, setCities] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [activeSection, setActiveSection] = useState('applications');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('AdminPanel: useEffect triggered, activeSection:', activeSection);
    if (activeSection === 'applications') {
      fetchApplications();
    } else if (activeSection === 'users') {
      fetchUsers();
    }
  }, [activeSection, activeTab]);

  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = activeTab === 'all' 
        ? 'http://localhost:8000/api/auth/doctor-applications/list/'
        : `http://localhost:8000/api/auth/doctor-applications/list/?status=${activeTab}`;
      
      const response = await fetch(url, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setApplications(data);
      } else {
        console.error('Ошибка загрузки заявок:', response.status);
        setError('Ошибка загрузки заявок');
        setApplications([]);
      }
    } catch (error) {
      console.error('Ошибка загрузки заявок:', error);
      setError('Ошибка соединения с сервером');
      setApplications([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Загружаем пользователей...');
      const response = await fetch('http://localhost:8000/api/auth/users/', {
        credentials: 'include'
      });
      
      console.log('Ответ сервера:', response.status);
      console.log('Заголовки ответа:', response.headers);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Полученные пользователи:', data);
        console.log('Тип данных:', typeof data);
        console.log('Является ли массивом:', Array.isArray(data));
        console.log('Длина данных:', data ? data.length : 'undefined');
        console.log('Ключи объекта:', data ? Object.keys(data) : 'undefined');
        console.log('Структура данных:', JSON.stringify(data, null, 2));
        
        // Проверяем, что data является массивом
        if (Array.isArray(data)) {
          setUsers(data);
        } else if (data && typeof data === 'object') {
          // Ищем массив пользователей в объекте
          const usersArray = data.users || data.results || data.data || Object.values(data).find(val => Array.isArray(val));
          if (usersArray && Array.isArray(usersArray)) {
            console.log('Найден массив пользователей в объекте:', usersArray);
            setUsers(usersArray);
          } else {
            console.error('Полученные данные не являются массивом:', data);
            setError('Неверный формат данных');
            setUsers([]);
          }
        } else {
          console.error('Полученные данные не являются массивом:', data);
          setError('Неверный формат данных');
          setUsers([]);
        }
      } else {
        console.error('Ошибка загрузки пользователей:', response.status);
        const errorData = await response.json();
        console.error('Детали ошибки:', errorData);
        setError(`Ошибка загрузки пользователей: ${response.status}`);
        setUsers([]);
      }
    } catch (error) {
      console.error('Ошибка соединения при загрузке пользователей:', error);
      setError('Ошибка соединения с сервером');
      setUsers([]);
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

  const openApplicationModal = async (application) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/doctor-applications/${application.id}/`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setSelectedApplication(data);
        setShowModal(true);
      }
    } catch (error) {
      console.error('Ошибка загрузки деталей заявки:', error);
    }
  };

  const openUserModal = async (user) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/users/${user.id}/profile/`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const userData = await response.json();
        setSelectedUser(userData);
        setEditingUser({ ...userData });
        setShowUserModal(true);
        setIsEditing(false);
        
        // Загружаем регионы
        await loadRegions();
        
        // Если есть регион, загружаем города и районы
        if (userData.region) {
          await loadCities(userData.region);
          await loadDistricts(userData.region);
        }
      } else {
        alert('Ошибка при загрузке профиля пользователя');
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleApprove = async (applicationId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/doctor-applications/${applicationId}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          status: 'approved'
        })
      });
      
      if (response.ok) {
        alert('Заявка одобрена!');
        fetchApplications();
        fetchUsers();
        
        // Обновляем данные пользователя в Header
        if (updateUserData) {
          await updateUserData();
        }
      } else {
        alert('Ошибка при одобрении заявки');
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleReject = async (applicationId) => {
    const reason = prompt('Укажите причину отклонения:');
    if (!reason) return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/auth/doctor-applications/${applicationId}/update/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          status: 'rejected',
          rejection_reason: reason
        })
      });
      
      if (response.ok) {
        alert('Заявка отклонена!');
        fetchApplications();
        fetchUsers();
      } else {
        alert('Ошибка при отклонении заявки');
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleUpdateDoctorName = async (applicationId) => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/doctor-applications/${applicationId}/update-name/`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(`Имя врача обновлено: ${data.new_name}`);
        fetchUsers(); // Обновляем список пользователей
        
        // Обновляем данные пользователя в Header
        if (updateUserData) {
          await updateUserData();
        }
      } else {
        const error = await response.json();
        alert(`Ошибка: ${error.error}`);
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleEditUser = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditingUser({ ...selectedUser });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setEditingUser(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleRegionChange = (e) => {
    const regionId = e.target.value;
    setEditingUser(prev => ({
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

  const handleSaveUser = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/users/${selectedUser.user.id}/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(editingUser)
      });
      
      if (response.ok) {
        const data = await response.json();
        alert('Профиль пользователя успешно обновлен!');
        setSelectedUser(data.profile);
        setEditingUser({ ...data.profile });
        setIsEditing(false);
        fetchUsers();
        
        // Обновляем данные пользователя в Header если это текущий пользователь
        if (updateUserData) {
          await updateUserData();
        }
      } else {
        const error = await response.json();
        alert(`Ошибка: ${JSON.stringify(error)}`);
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    const confirmed = window.confirm(
      `Вы уверены, что хотите удалить пользователя ${selectedUser.user.email}?\n\nЭто действие нельзя отменить!`
    );
    
    if (!confirmed) return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/auth/users/${selectedUser.user.id}/delete/`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        alert(data.message);
        setShowUserModal(false);
        setSelectedUser(null);
        setEditingUser(null);
        setIsEditing(false);
        fetchUsers();
      } else {
        const error = await response.json();
        alert(`Ошибка: ${error.error}`);
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const getStatusCount = (status) => {
    return applications.filter(app => app.status === status).length;
  };

  const getUserRoleDisplay = (user) => {
    if (user.is_staff || user.is_superuser) return 'Администратор';
    if (user.role === 'doctor') return 'Врач';
    return 'Пациент';
  };

  console.log('AdminPanel render:', { activeSection, loading, error, usersCount: users.length, applicationsCount: applications.length });

  return (
    <div className="admin-panel">
      <div className="admin-panel__header">
        <h1>Панель администратора</h1>
        <div className="admin-panel__tabs">
          <button 
            className={`admin-panel__tab ${activeSection === 'applications' ? 'active' : ''}`}
            onClick={() => setActiveSection('applications')}
          >
            Заявки на роль врача
          </button>
          <button 
            className={`admin-panel__tab ${activeSection === 'users' ? 'active' : ''}`}
            onClick={() => setActiveSection('users')}
          >
            Управление пользователями
          </button>
        </div>
      </div>

      {activeSection === 'applications' && (
        <>
          <div className="admin-panel__stats">
            <div className="admin-panel__stat">
              <span className="admin-panel__stat-number">{getStatusCount('pending')}</span>
              <span className="admin-panel__stat-label">Ожидают рассмотрения</span>
            </div>
            <div className="admin-panel__stat">
              <span className="admin-panel__stat-number">{getStatusCount('approved')}</span>
              <span className="admin-panel__stat-label">Одобрены</span>
            </div>
            <div className="admin-panel__stat">
              <span className="admin-panel__stat-number">{getStatusCount('rejected')}</span>
              <span className="admin-panel__stat-label">Отклонены</span>
            </div>
          </div>

          <div className="admin-panel__filters">
            <button 
              className={`admin-panel__filter ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              Все заявки
            </button>
            <button 
              className={`admin-panel__filter ${activeTab === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveTab('pending')}
            >
              Ожидают рассмотрения
            </button>
            <button 
              className={`admin-panel__filter ${activeTab === 'approved' ? 'active' : ''}`}
              onClick={() => setActiveTab('approved')}
            >
              Одобрены
            </button>
            <button 
              className={`admin-panel__filter ${activeTab === 'rejected' ? 'active' : ''}`}
              onClick={() => setActiveTab('rejected')}
            >
              Отклонены
            </button>
          </div>

          <div className="admin-panel__applications">
            {loading ? (
              <div className="admin-panel__empty">
                <p>Загрузка заявок...</p>
              </div>
            ) : error ? (
              <div className="admin-panel__empty">
                <p>{error}</p>
              </div>
            ) : applications.length === 0 ? (
              <div className="admin-panel__empty">
                <p>Нет заявок для отображения</p>
              </div>
            ) : (
              applications.map(application => (
                <div key={application.id} className="admin-panel__application-card">
                  <div className="admin-panel__application-info">
                    <h3>{application.full_name}</h3>
                    <p className="admin-panel__application-specialization">
                      {application.specialization}
                    </p>
                    <p className="admin-panel__application-location">
                      {application.region_name && `${application.region_name}, `}{application.city_name}, {application.district_name}
                    </p>
                    <p className="admin-panel__application-status">
                      Статус: <span className={`status-${application.status}`}>
                        {application.status === 'pending' && 'Ожидает рассмотрения'}
                        {application.status === 'approved' && 'Одобрена'}
                        {application.status === 'rejected' && 'Отклонена'}
                      </span>
                    </p>
                  </div>
                  <div className="admin-panel__application-actions">
                    <button 
                      className="admin-panel__view-btn"
                      onClick={() => openApplicationModal(application)}
                    >
                      Просмотреть
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {activeSection === 'users' && (
        <div className="admin-panel__users">
          {loading ? (
            <div className="admin-panel__empty">
              <p>Загрузка пользователей...</p>
            </div>
          ) : error ? (
            <div className="admin-panel__empty">
              <p>{error}</p>
            </div>
          ) : !Array.isArray(users) || users.length === 0 ? (
            <div className="admin-panel__empty">
              <p>Нет пользователей для отображения</p>
            </div>
          ) : (
            users.map(user => (
              <div key={user.id} className="admin-panel__user-card">
                <div className="admin-panel__user-info">
                  <h3>{user.first_name} {user.last_name}</h3>
                  <p className="admin-panel__user-email">{user.email}</p>
                  <p className="admin-panel__user-role">
                    Роль: <span className={`role-${user.role || 'patient'}`}>
                      {getUserRoleDisplay(user)}
                    </span>
                  </p>
                </div>
                <div className="admin-panel__user-actions">
                  <button 
                    className="admin-panel__view-btn"
                    onClick={() => openUserModal(user)}
                  >
                    Управлять профилем
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Модальные окна остаются без изменений */}
      {showModal && selectedApplication && (
        <div className="admin-panel__modal-overlay">
          <div className="admin-panel__modal">
            <div className="admin-panel__modal-header">
              <h2>Детали заявки</h2>
              <button 
                className="admin-panel__modal-close"
                onClick={() => {
                  setShowModal(false);
                  setSelectedApplication(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="admin-panel__modal-content">
              <div className="admin-panel__modal-section">
                <h3>Основная информация</h3>
                <p><strong>ФИО:</strong> {selectedApplication.full_name}</p>
                <p><strong>Специализация:</strong> {selectedApplication.specialization}</p>
                <p><strong>Местоположение:</strong> {selectedApplication.region_name && `${selectedApplication.region_name}, `}{selectedApplication.city_name}, {selectedApplication.district_name}</p>
                <p><strong>Языки:</strong> {selectedApplication.languages.join(', ')}</p>
              </div>
              
              <div className="admin-panel__modal-section">
                <h3>Образование и опыт</h3>
                <p><strong>Образование:</strong> {selectedApplication.education}</p>
                <p><strong>Опыт работы:</strong> {selectedApplication.experience}</p>
                <p><strong>Номер лицензии:</strong> {selectedApplication.license_number}</p>
              </div>
              
              {selectedApplication.additional_info && (
                <div className="admin-panel__modal-section">
                  <h3>Дополнительная информация</h3>
                  <p>{selectedApplication.additional_info}</p>
                </div>
              )}
              
              <div className="admin-panel__modal-section">
                <h3>Документы</h3>
                <div className="admin-panel__documents">
                  {selectedApplication.photo && (
                    <div className="admin-panel__document">
                      <h4>Фотография</h4>
                      <img 
                        src={`http://localhost:8000${selectedApplication.photo}`} 
                        alt="Фото врача" 
                        className="admin-panel__document-image"
                      />
                    </div>
                  )}
                  
                  {selectedApplication.diploma && (
                    <div className="admin-panel__document">
                      <h4>Диплом</h4>
                      <a 
                        href={`http://localhost:8000${selectedApplication.diploma}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="admin-panel__document-link"
                      >
                        Просмотреть диплом
                      </a>
                    </div>
                  )}
                  
                  {selectedApplication.license && (
                    <div className="admin-panel__document">
                      <h4>Лицензия</h4>
                      <a 
                        href={`http://localhost:8000${selectedApplication.license}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="admin-panel__document-link"
                      >
                        Просмотреть лицензию
                      </a>
                    </div>
                  )}
                </div>
              </div>
              
              {selectedApplication.status === 'rejected' && selectedApplication.rejection_reason && (
                <div className="admin-panel__modal-section">
                  <h3>Причина отклонения</h3>
                  <p>{selectedApplication.rejection_reason}</p>
                </div>
              )}
              
              {selectedApplication.status === 'pending' && (
                <div className="admin-panel__modal-section">
                  <h3>Действия</h3>
                  <div className="admin-panel__modal-actions">
                    <button 
                      className="admin-panel__approve-btn"
                      onClick={() => handleApprove(selectedApplication.id)}
                    >
                      Одобрить
                    </button>
                    <button 
                      className="admin-panel__reject-btn"
                      onClick={() => handleReject(selectedApplication.id)}
                    >
                      Отклонить
                    </button>
                  </div>
                </div>
              )}
              
              {selectedApplication.status === 'approved' && (
                <div className="admin-panel__modal-section">
                  <h3>Действия</h3>
                  <div className="admin-panel__modal-actions">
                    <button 
                      className="admin-panel__update-name-btn"
                      onClick={() => handleUpdateDoctorName(selectedApplication.id)}
                    >
                      Обновить имя врача
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showUserModal && selectedUser && (
        <div className="admin-panel__modal-overlay">
          <div className="admin-panel__modal admin-panel__modal--large">
            <div className="admin-panel__modal-header">
              <h2>Управление профилем пользователя</h2>
              <button 
                className="admin-panel__modal-close"
                onClick={() => {
                  setShowUserModal(false);
                  setSelectedUser(null);
                  setEditingUser(null);
                  setIsEditing(false);
                }}
              >
                ×
              </button>
            </div>
            <div className="admin-panel__modal-content">
              <div className="admin-panel__modal-section">
                <h3>Основная информация</h3>
                {isEditing ? (
                  <div className="admin-panel__form">
                    <div className="admin-panel__form-row">
                      <div className="admin-panel__form-group">
                        <label>Имя</label>
                        <input
                          type="text"
                          name="first_name"
                          value={editingUser.first_name || ''}
                          onChange={handleInputChange}
                          className="admin-panel__input"
                        />
                      </div>
                      <div className="admin-panel__form-group">
                        <label>Фамилия</label>
                        <input
                          type="text"
                          name="last_name"
                          value={editingUser.last_name || ''}
                          onChange={handleInputChange}
                          className="admin-panel__input"
                        />
                      </div>
                    </div>
                    <div className="admin-panel__form-group">
                      <label>Email</label>
                      <input
                        type="email"
                        value={selectedUser.user.email}
                        className="admin-panel__input"
                        disabled
                      />
                    </div>
                    <div className="admin-panel__form-group">
                      <label>Роль</label>
                      <select
                        name="role"
                        value={editingUser.role || 'patient'}
                        onChange={handleInputChange}
                        className="admin-panel__select"
                      >
                        <option value="patient">Пациент</option>
                        <option value="doctor">Врач</option>
                        <option value="admin">Администратор</option>
                      </select>
                    </div>
                  </div>
                ) : (
                  <div className="admin-panel__info">
                    <p><strong>ФИО:</strong> {selectedUser.first_name} {selectedUser.last_name}</p>
                    <p><strong>Email:</strong> {selectedUser.user.email}</p>
                    <p><strong>Роль:</strong> {getUserRoleDisplay(selectedUser.user)}</p>
                  </div>
                )}
              </div>
              
              <div className="admin-panel__modal-section">
                <h3>Контактная информация</h3>
                {isEditing ? (
                  <div className="admin-panel__form">
                    <div className="admin-panel__form-group">
                      <label>Телефон</label>
                      <input
                        type="tel"
                        name="phone"
                        value={editingUser.phone || ''}
                        onChange={handleInputChange}
                        className="admin-panel__input"
                      />
                    </div>
                    <div className="admin-panel__form-row">
                      <div className="admin-panel__form-group">
                        <label>Регион</label>
                        <select
                          name="region"
                          value={editingUser.region || ''}
                          onChange={handleRegionChange}
                          className="admin-panel__select"
                        >
                          <option value="">Выберите регион</option>
                          {regions.map(region => (
                            <option key={region.id} value={region.id}>
                              {region.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="admin-panel__form-group">
                        <label>Город</label>
                        <select
                          name="city"
                          value={editingUser.city || ''}
                          onChange={handleInputChange}
                          className="admin-panel__select"
                          disabled={!editingUser.region}
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
                    <div className="admin-panel__form-group">
                      <label>Адрес</label>
                      <input
                        type="text"
                        name="address"
                        value={editingUser.address || ''}
                        onChange={handleInputChange}
                        className="admin-panel__input"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="admin-panel__info">
                    <p><strong>Телефон:</strong> {selectedUser.phone || 'Не указан'}</p>
                    <p><strong>Адрес:</strong> {selectedUser.address || 'Не указан'}</p>
                  </div>
                )}
              </div>
              
              {selectedUser.role === 'doctor' && (
                <div className="admin-panel__modal-section">
                  <h3>Информация врача</h3>
                  {isEditing ? (
                    <div className="admin-panel__form">
                      <div className="admin-panel__form-group">
                        <label>Специализация</label>
                        <input
                          type="text"
                          name="specialization"
                          value={editingUser.specialization || ''}
                          onChange={handleInputChange}
                          className="admin-panel__input"
                        />
                      </div>
                      <div className="admin-panel__form-group">
                        <label>Образование</label>
                        <textarea
                          name="education"
                          value={editingUser.education || ''}
                          onChange={handleInputChange}
                          className="admin-panel__textarea"
                          rows={3}
                        />
                      </div>
                      <div className="admin-panel__form-group">
                        <label>Опыт работы</label>
                        <textarea
                          name="experience"
                          value={editingUser.experience || ''}
                          onChange={handleInputChange}
                          className="admin-panel__textarea"
                          rows={3}
                        />
                      </div>
                      <div className="admin-panel__form-group">
                        <label>Номер лицензии</label>
                        <input
                          type="text"
                          name="license_number"
                          value={editingUser.license_number || ''}
                          onChange={handleInputChange}
                          className="admin-panel__input"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="admin-panel__info">
                      <p><strong>Специализация:</strong> {selectedUser.specialization || 'Не указана'}</p>
                      <p><strong>Образование:</strong> {selectedUser.education || 'Не указано'}</p>
                      <p><strong>Опыт работы:</strong> {selectedUser.experience || 'Не указан'}</p>
                      <p><strong>Номер лицензии:</strong> {selectedUser.license_number || 'Не указан'}</p>
                      <p><strong>Языки:</strong> {selectedUser.languages ? selectedUser.languages.join(', ') : 'Не указаны'}</p>
                    </div>
                  )}
                </div>
              )}
              
              <div className="admin-panel__modal-section">
                <h3>Действия</h3>
                <div className="admin-panel__modal-actions">
                  {isEditing ? (
                    <>
                      <button 
                        className="admin-panel__save-btn"
                        onClick={handleSaveUser}
                      >
                        Сохранить
                      </button>
                      <button 
                        className="admin-panel__cancel-btn"
                        onClick={handleCancelEdit}
                      >
                        Отмена
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        className="admin-panel__edit-btn"
                        onClick={handleEditUser}
                      >
                        Редактировать профиль
                      </button>
                      <button 
                        className="admin-panel__delete-btn"
                        onClick={handleDeleteUser}
                      >
                        Удалить пользователя
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminPanel; 