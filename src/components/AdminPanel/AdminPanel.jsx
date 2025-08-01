import React, { useState, useEffect } from "react";
import "./AdminPanel.scss";

const AdminPanel = () => {
  const [applications, setApplications] = useState([]);
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
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
        const data = await response.json();
        setSelectedUser(data);
        setShowUserModal(true);
      }
    } catch (error) {
      console.error('Ошибка загрузки профиля пользователя:', error);
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
        const result = await response.json();
        alert(result.message);
        fetchApplications();
        setSelectedApplication(null);
        setShowModal(false);
      } else {
        const error = await response.json();
        alert(error.error || 'Ошибка при одобрении заявки');
      }
    } catch (error) {
      alert('Ошибка соединения с сервером');
    }
  };

  const handleReject = async (applicationId) => {
    const reason = prompt('Укажите причину отклонения заявки:');
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
        const result = await response.json();
        alert(result.message);
        fetchApplications();
        setSelectedApplication(null);
        setShowModal(false);
      } else {
        const error = await response.json();
        alert(error.error || 'Ошибка при отклонении заявки');
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
                      {application.region && `${application.region}, `}{application.city}, {application.district}
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
                <p><strong>Местоположение:</strong> {selectedApplication.region && `${selectedApplication.region}, `}{selectedApplication.city}, {selectedApplication.district}</p>
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
            </div>
          </div>
        </div>
      )}

      {showUserModal && selectedUser && (
        <div className="admin-panel__modal-overlay">
          <div className="admin-panel__modal">
            <div className="admin-panel__modal-header">
              <h2>Управление профилем пользователя</h2>
              <button 
                className="admin-panel__modal-close"
                onClick={() => {
                  setShowUserModal(false);
                  setSelectedUser(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="admin-panel__modal-content">
              <div className="admin-panel__modal-section">
                <h3>Основная информация</h3>
                <p><strong>ФИО:</strong> {selectedUser.user.first_name} {selectedUser.user.last_name}</p>
                <p><strong>Email:</strong> {selectedUser.user.email}</p>
                <p><strong>Роль:</strong> {getUserRoleDisplay(selectedUser.user)}</p>
              </div>
              
              {selectedUser.specialization && (
                <div className="admin-panel__modal-section">
                  <h3>Информация врача</h3>
                  <p><strong>Специализация:</strong> {selectedUser.specialization}</p>
                  <p><strong>Образование:</strong> {selectedUser.education}</p>
                  <p><strong>Опыт работы:</strong> {selectedUser.experience}</p>
                  <p><strong>Номер лицензии:</strong> {selectedUser.license_number}</p>
                  <p><strong>Языки:</strong> {selectedUser.languages.join(', ')}</p>
                </div>
              )}
              
              <div className="admin-panel__modal-section">
                <h3>Действия</h3>
                <div className="admin-panel__modal-actions">
                  <button 
                    className="admin-panel__approve-btn"
                    onClick={() => {
                      alert('Функция изменения роли пользователя будет добавлена позже');
                    }}
                  >
                    Изменить роль
                  </button>
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