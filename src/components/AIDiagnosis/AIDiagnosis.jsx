import React, { useState, useRef, useEffect } from 'react';
import './AIDiagnosis.scss';

const AIDiagnosis = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: 'Привет! Я Healzy AI, созданная CTO компании Healzy App. Я помогу вам с медицинскими вопросами. Вы можете показать мне фото/видео проблемной области или описать симптомы голосом или текстом. Что вас беспокоит?',
      timestamp: new Date()
    }
  ]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isVideoMode, setIsVideoMode] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Автопрокрутка к последнему сообщению
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Отправка текстового сообщения
  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: currentMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/ai/diagnosis/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: currentMessage,
          type: 'text'
        })
      });

      const data = await response.json();
      
      if (response.ok) {
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(data.error || 'Ошибка при получении ответа');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Извините, произошла ошибка. Попробуйте еще раз.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Обработка загрузки файла
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Проверяем тип файла
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    
    if (!isImage && !isVideo) {
      alert('Пожалуйста, загрузите изображение или видео');
      return;
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: isImage ? '📷 Изображение загружено' : '🎥 Видео загружено',
      file: file,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', isImage ? 'image' : 'video');

      const response = await fetch('http://localhost:8000/api/auth/ai/diagnosis/', {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      const data = await response.json();
      
      if (response.ok) {
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(data.error || 'Ошибка при анализе файла');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Извините, не удалось проанализировать файл. Попробуйте еще раз.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Запись голоса
  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          setRecordedChunks(prev => [...prev, event.data]);
        }
      };

      recorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
      };

      setMediaRecorder(recorder);
      recorder.start();
      setIsRecording(true);
    } catch (error) {
      alert('Не удалось получить доступ к микрофону');
    }
  };

  const stopVoiceRecording = async () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      
      // Обработка записанного аудио
      setTimeout(async () => {
        if (recordedChunks.length > 0) {
          const audioBlob = new Blob(recordedChunks, { type: 'audio/wav' });
          await sendAudioMessage(audioBlob);
          setRecordedChunks([]);
        }
      }, 100);
    }
  };

  const sendAudioMessage = async (audioBlob) => {
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: '🎤 Голосовое сообщение',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'voice.wav');
      formData.append('type', 'audio');

      const response = await fetch('http://localhost:8000/api/auth/ai/diagnosis/', {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      const data = await response.json();
      
      if (response.ok) {
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(data.error || 'Ошибка при обработке аудио');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Извините, не удалось обработать голосовое сообщение. Попробуйте еще раз.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Форматирование времени
  const formatTime = (date) => {
    return date.toLocaleTimeString('ru-RU', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="ai-diagnosis">
      <div className="ai-diagnosis__container">
        <div className="ai-diagnosis__header">
          <div className="ai-diagnosis__title">
            <div className="ai-diagnosis__icon">
              🤖
            </div>
            <div>
              <h1>Healzy AI Диагностика</h1>
              <p>Персональный медицинский ассистент</p>
            </div>
          </div>
          <div className="ai-diagnosis__status">
            <span className="ai-diagnosis__status-indicator"></span>
            Онлайн
          </div>
        </div>

        <div className="ai-diagnosis__messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`ai-diagnosis__message ai-diagnosis__message--${message.type}`}
            >
              <div className="ai-diagnosis__message-avatar">
                {message.type === 'ai' ? '🤖' : '👤'}
              </div>
              <div className="ai-diagnosis__message-content">
                <div className="ai-diagnosis__message-text">
                  {message.content}
                </div>
                <div className="ai-diagnosis__message-time">
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="ai-diagnosis__message ai-diagnosis__message--ai">
              <div className="ai-diagnosis__message-avatar">🤖</div>
              <div className="ai-diagnosis__message-content">
                <div className="ai-diagnosis__loading">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="ai-diagnosis__input">
          <div className="ai-diagnosis__actions">
            <button
              className="ai-diagnosis__action-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Загрузить изображение или видео"
            >
              📷
            </button>
            
            <button
              className={`ai-diagnosis__action-btn ${isRecording ? 'ai-diagnosis__action-btn--recording' : ''}`}
              onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
              title={isRecording ? 'Остановить запись' : 'Записать голосовое сообщение'}
            >
              {isRecording ? '⏹️' : '🎤'}
            </button>
          </div>

          <div className="ai-diagnosis__input-container">
            <input
              type="text"
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Опишите ваши симптомы или задайте медицинский вопрос..."
              className="ai-diagnosis__text-input"
              disabled={isLoading}
            />
            
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !currentMessage.trim()}
              className="ai-diagnosis__send-btn"
            >
              ➤
            </button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            onChange={handleFileUpload}
            className="ai-diagnosis__file-input"
            hidden
          />
        </div>

        <div className="ai-diagnosis__disclaimer">
          ⚠️ Внимание: AI диагностика не заменяет консультацию врача. 
          При серьезных симптомах обратитесь к специалисту.
        </div>
      </div>
    </div>
  );
};

export default AIDiagnosis;
