import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './Chat.scss';

const Chat = () => {
  const { consultationId } = useParams();
  const navigate = useNavigate();
  const [consultation, setConsultation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ws, setWs] = useState(null);
  const messagesEndRef = useRef(null);
  const [sending, setSending] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [showAcceptModal, setShowAcceptModal] = useState(false);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    fetchConsultation();
    fetchMessages();
    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [consultationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchConsultation = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/consultations/${consultationId}/`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setConsultation(data);
      } else {
        setError('Консультация не найдена');
      }
    } catch (error) {
      console.error('Ошибка при загрузке консультации:', error);
      setError('Ошибка соединения с сервером');
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/auth/consultations/${consultationId}/messages/`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      } else {
        setError('Ошибка загрузки сообщений');
      }
    } catch (error) {
      console.error('Ошибка при загрузке сообщений:', error);
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/chat/${consultationId}/`;
    
    console.log('Подключение к WebSocket:', wsUrl);
    
    // WebSocket не поддерживает передачу заголовков, но браузер автоматически передает куки
    // для того же домена, если они httpOnly
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket соединение установлено');
      setWsConnected(true);
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Получено WebSocket сообщение:', data);
        
        if (data.type === 'chat_message') {
          setMessages(prev => {
            // Проверяем, нет ли уже такого сообщения
            const messageExists = prev.some(msg => msg.id === data.message_id);
            if (messageExists) {
              return prev;
            }
            
            return [...prev, {
              id: data.message_id,
              content: data.message,
              sender: {
                id: data.sender_id,
                full_name: data.sender_name,
                initials: data.sender_initials
              },
              created_at: data.timestamp,
              is_read: false
            }];
          });
        } else if (data.type === 'connection_established') {
          console.log('WebSocket соединение подтверждено');
        } else if (data.type === 'error') {
          console.error('WebSocket ошибка:', data.message);
          setError(data.message);
        } else if (data.type === 'pong') {
          console.log('WebSocket pong получен');
        }
      } catch (error) {
        console.error('Ошибка парсинга WebSocket сообщения:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket ошибка:', error);
      setWsConnected(false);
    };

    websocket.onclose = (event) => {
      console.log('WebSocket соединение закрыто:', event.code, event.reason);
      setWsConnected(false);
      
      // Проверяем код закрытия для понимания причины
      if (event.code === 4001) {
        console.error('WebSocket: Ошибка аутентификации');
        setError('Ошибка аутентификации. Перезайдите в систему.');
        return;
      } else if (event.code === 4003) {
        console.error('WebSocket: Нет доступа к консультации');
        setError('У вас нет доступа к этой консультации.');
        return;
      }
      
      // Попытка переподключения через 3 секунды для других ошибок
      setTimeout(() => {
        if (!wsConnected) {
          console.log('Попытка переподключения к WebSocket...');
          connectWebSocket();
        }
      }, 3000);
    };

    setWs(websocket);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim() || sending || !ws || ws.readyState !== WebSocket.OPEN) return;

    setSending(true);

    try {
      // Отправляем сообщение через WebSocket
      ws.send(JSON.stringify({
        type: 'chat_message',
        message: newMessage.trim()
      }));
      
      setNewMessage('');
    } catch (error) {
      console.error('Ошибка при отправке сообщения:', error);
      setError('Ошибка соединения с сервером');
    } finally {
      setSending(false);
    }
  };

  const handleAcceptConsultation = async () => {
    setActionLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/auth/consultations/${consultationId}/accept/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setConsultation(data.consultation);
        setShowAcceptModal(false);
        // Показываем уведомление об успехе
        showNotification('Консультация успешно принята!', 'success');
      } else {
        const error = await response.json();
        showNotification(error.error || 'Ошибка принятия консультации', 'error');
      }
    } catch (error) {
      console.error('Ошибка при принятии консультации:', error);
      showNotification('Ошибка соединения с сервером', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteConsultation = async () => {
    setActionLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/auth/consultations/${consultationId}/complete/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setConsultation(data.consultation);
        setShowCompleteModal(false);
        showNotification('Консультация успешно завершена!', 'success');
      } else {
        const error = await response.json();
        showNotification(error.error || 'Ошибка завершения консультации', 'error');
      }
    } catch (error) {
      console.error('Ошибка при завершении консультации:', error);
      showNotification('Ошибка соединения с сервером', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const showNotification = (message, type = 'info') => {
    // Создаем уведомление
    const notification = document.createElement('div');
    notification.className = `chat__notification chat__notification--${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Удаляем уведомление через 3 секунды
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
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

  const canWrite = () => {
    if (!consultation) return false;
    
    // Получаем текущего пользователя из localStorage
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (userData.role === 'patient') {
      return consultation.can_patient_write;
    } else if (userData.role === 'doctor') {
      return consultation.can_doctor_write;
    }
    
    return false;
  };

  const isDoctor = () => {
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    return userData.role === 'doctor';
  };

  if (loading) {
    return (
      <div className="chat">
        <div className="chat__loading">
          <div className="loading-spinner"></div>
          <p>Загрузка чата...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="chat">
        <div className="chat__error">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/consultations')} className="chat__back-btn">
            ← Вернуться к консультациям
          </button>
        </div>
      </div>
    );
  }

  if (!consultation) {
    return (
      <div className="chat">
        <div className="chat__error">
          <h2>Консультация не найдена</h2>
          <p>Запрошенная консультация не существует или была удалена</p>
          <button onClick={() => navigate('/consultations')} className="chat__back-btn">
            ← Вернуться к консультациям
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="chat">
      <div className="chat__header">
        <button onClick={() => navigate('/consultations')} className="chat__back-btn">
          ← Вернуться к консультациям
        </button>
        
        <div className="chat__consultation-info">
          <h1 className="chat__title">
            {consultation.title || `Консультация с ${consultation.doctor_name}`}
          </h1>
          <div className="chat__meta">
            <span className="chat__doctor">{consultation.doctor_name}</span>
            <span className={`chat__status chat__status--${consultation.status}`}>
              {consultation.status_display}
            </span>
            {wsConnected && (
              <span className="chat__connection-status chat__connection-status--connected">
                ● Онлайн
              </span>
            )}
          </div>
        </div>

        {/* Кнопки действий для врача */}
        {isDoctor() && consultation.status === 'pending' && (
          <button 
            onClick={() => setShowAcceptModal(true)}
            disabled={actionLoading}
            className="chat__accept-btn"
          >
            {actionLoading ? 'Принятие...' : 'Принять консультацию'}
          </button>
        )}

        {isDoctor() && consultation.status === 'active' && (
          <button 
            onClick={() => setShowCompleteModal(true)}
            disabled={actionLoading}
            className="chat__complete-btn"
          >
            {actionLoading ? 'Завершение...' : 'Завершить консультацию'}
          </button>
        )}
      </div>

      <div className="chat__messages">
        {messages.length === 0 ? (
          <div className="chat__empty">
            <div className="chat__empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p>Сообщений пока нет</p>
                      {consultation.status === 'pending' && (
            <div className="chat__status-info chat__status-info--pending">
              <div className="chat__status-icon">⏳</div>
              <div className="chat__status-content">
                <h3>
                  {isDoctor() 
                    ? 'Ожидает вашего принятия'
                    : 'Ожидает принятия врачом'
                  }
                </h3>
                <p>
                  {isDoctor() 
                    ? 'Примите консультацию, чтобы начать общение с пациентом'
                    : 'Врач рассмотрит вашу заявку и примет консультацию. После этого вы сможете общаться в чате.'
                  }
                </p>
              </div>
            </div>
          )}
          
          {consultation.status === 'completed' && (
            <div className="chat__status-info chat__status-info--completed">
              <div className="chat__status-icon">✅</div>
              <div className="chat__status-content">
                <h3>Консультация завершена</h3>
                <p>Этот чат заархивирован. Вы можете просматривать историю сообщений, но не можете отправлять новые.</p>
              </div>
            </div>
          )}
          
          {consultation.status === 'cancelled' && (
            <div className="chat__status-info chat__status-info--cancelled">
              <div className="chat__status-icon">❌</div>
              <div className="chat__status-content">
                <h3>Консультация отменена</h3>
                <p>Эта консультация была отменена и недоступна для общения.</p>
              </div>
            </div>
          )}
          </div>
        ) : (
          <div className="chat__messages-list">
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`chat__message chat__message--${message.sender.id === consultation.patient.id ? 'patient' : 'doctor'}`}
              >
                <div className="chat__message-avatar">
                  {message.sender.initials}
                </div>
                <div className="chat__message-content">
                  <div className="chat__message-header">
                    <span className="chat__message-sender">{message.sender.full_name}</span>
                    <span className="chat__message-time">{formatDate(message.created_at)}</span>
                  </div>
                  <div className="chat__message-text">{message.content}</div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {canWrite() ? (
        <form className="chat__input-form" onSubmit={handleSendMessage}>
          <div className="chat__input-container">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Введите сообщение..."
              className="chat__input"
              disabled={sending}
            />
            <button 
              type="submit" 
              className="chat__send-btn"
              disabled={!newMessage.trim() || sending}
            >
              {sending ? (
                <div className="chat__send-spinner"></div>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          </div>
        </form>
      ) : (
        <div className={`chat__disabled chat__disabled--${consultation.status}`}>
          <div className="chat__disabled-content">
            {consultation.status === 'pending' && (
              <>
                <span className="chat__disabled-icon">🔒</span>
                <p>
                  {isDoctor() 
                    ? 'Примите консультацию выше, чтобы разблокировать чат'
                    : 'Чат будет разблокирован после принятия консультации врачом'
                  }
                </p>
              </>
            )}
            {consultation.status === 'completed' && (
              <>
                <span className="chat__disabled-icon">🔐</span>
                <p>Консультация завершена. Чат заархивирован.</p>
              </>
            )}
            {consultation.status === 'cancelled' && (
              <>
                <span className="chat__disabled-icon">⛔</span>
                <p>Консультация отменена. Чат недоступен.</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Модальное окно принятия консультации */}
      {showAcceptModal && (
        <div className="chat__modal-overlay" onClick={() => setShowAcceptModal(false)}>
          <div className="chat__modal" onClick={(e) => e.stopPropagation()}>
            <div className="chat__modal-header">
              <h3>Принять консультацию</h3>
              <button 
                className="chat__modal-close"
                onClick={() => setShowAcceptModal(false)}
              >
                ×
              </button>
            </div>
            <div className="chat__modal-content">
              <p>Вы уверены, что хотите принять эту консультацию?</p>
              <p>После принятия вы сможете общаться с пациентом.</p>
            </div>
            <div className="chat__modal-actions">
              <button 
                className="chat__modal-btn chat__modal-btn--secondary"
                onClick={() => setShowAcceptModal(false)}
                disabled={actionLoading}
              >
                Отмена
              </button>
              <button 
                className="chat__modal-btn chat__modal-btn--primary"
                onClick={handleAcceptConsultation}
                disabled={actionLoading}
              >
                {actionLoading ? 'Принятие...' : 'Принять'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно завершения консультации */}
      {showCompleteModal && (
        <div className="chat__modal-overlay" onClick={() => setShowCompleteModal(false)}>
          <div className="chat__modal" onClick={(e) => e.stopPropagation()}>
            <div className="chat__modal-header">
              <h3>Завершить консультацию</h3>
              <button 
                className="chat__modal-close"
                onClick={() => setShowCompleteModal(false)}
              >
                ×
              </button>
            </div>
            <div className="chat__modal-content">
              <p>Вы уверены, что хотите завершить эту консультацию?</p>
              <p>После завершения новые сообщения будут недоступны.</p>
            </div>
            <div className="chat__modal-actions">
              <button 
                className="chat__modal-btn chat__modal-btn--secondary"
                onClick={() => setShowCompleteModal(false)}
                disabled={actionLoading}
              >
                Отмена
              </button>
              <button 
                className="chat__modal-btn chat__modal-btn--danger"
                onClick={handleCompleteConsultation}
                disabled={actionLoading}
              >
                {actionLoading ? 'Завершение...' : 'Завершить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chat; 