import React, { useState, useRef, useEffect } from 'react';
import './AIDiagnosis.scss';

const AIDiagnosis = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: 'Привет! 😊 Я Healzy AI - ваш дружелюбный помощник! Можете спросить меня о чем угодно: здоровье, симптомы, или просто поболтать! Отправляйте текст, голосовые сообщения или фото - я всегда рада помочь! ✨',
      timestamp: new Date()
    }
  ]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false); // Голосовое прослушивание
  const [isSpeaking, setIsSpeaking] = useState(false); // AI говорит
  const [speechRecognition, setSpeechRecognition] = useState(null); // Распознавание речи
  const [isSupported, setIsSupported] = useState(false); // Поддержка Speech API
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Автопрокрутка к последнему сообщению
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Инициализация Speech Recognition API
  useEffect(() => {
    // Проверяем поддержку Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
      console.log('✅ Speech Recognition поддерживается!');
      setIsSupported(true);
      
      const recognition = new SpeechRecognition();
      
      // Настройки распознавания
      recognition.continuous = true; // Непрерывное распознавание
      recognition.interimResults = true; // Промежуточные результаты
      recognition.lang = 'ru-RU'; // Русский язык
      recognition.maxAlternatives = 1;
      
      setSpeechRecognition(recognition);
      
      // Обработчики событий
      recognition.onstart = () => {
        console.log('🎤 Распознавание речи началось');
        setIsListening(true);
      };
      
      recognition.onresult = (event) => {
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          }
        }
        
        if (finalTranscript.trim()) {
          console.log('🗣️ Распознанная речь:', finalTranscript);
          handleVoiceInput(finalTranscript.trim());
        }
      };
      
      recognition.onerror = (event) => {
        console.error('❌ Ошибка распознавания речи:', event.error);
        setIsListening(false);
        
        if (event.error === 'not-allowed') {
          alert('Разрешите доступ к микрофону в настройках браузера');
        }
      };
      
      recognition.onend = () => {
        console.log('🔇 Распознавание речи завершено');
        setIsListening(false);
      };
      
    } else {
      console.log('❌ Speech Recognition не поддерживается');
      setIsSupported(false);
    }
    
    // Инициализация голосов для синтеза
    if ('speechSynthesis' in window) {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
          console.log('🎵 Голоса загружены:', voices.length);
        }
      };
      
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Новая система: Speech Recognition API (как в ChatGPT Voice)
  const startSmartListening = () => {
    if (!isSupported) {
      alert('Speech Recognition не поддерживается в этом браузере. Попробуйте Chrome.');
      return;
    }
    
    if (isListening) {
      console.log('🔴 Останавливаем голосовое прослушивание...');
      speechRecognition.stop();
      setIsListening(false);
      return;
    }

    console.log('🎤 Запускаем Speech Recognition...');
    
    try {
      speechRecognition.start();
    } catch (error) {
      console.error('❌ Ошибка запуска распознавания:', error);
      alert('Не удалось запустить распознавание речи. Убедитесь что микрофон доступен.');
    }
  };

  // Обработка голосового ввода от Speech Recognition
  const handleVoiceInput = async (transcript) => {
    console.log('💬 Обрабатываю голосовой ввод:', transcript);
    
    // Добавляем сообщение пользователя в чат
    const userMessage = {
      id: Date.now(),
      type: 'user', 
      content: `🎤 ${transcript}`,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/auth/ai/diagnosis/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: transcript,
          type: 'text'
        })
      });

      if (response.ok) {
        const data = await response.json();
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // Озвучиваем ответ AI
        speakText(data.response);
        
      } else {
        throw new Error('Ошибка сервера');
      }
    } catch (error) {
      console.error('❌ Ошибка при отправке голосового сообщения:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: 'Извините, не удалось обработать голосовое сообщение. Попробуйте ещё раз.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      speakText('Извините, произошла ошибка. Попробуйте ещё раз.');
    } finally {
      setIsLoading(false);
    }
  };

  // Убрал сложную систему анализа аудио - теперь все через Speech Recognition API

  // Функция для удаления эмодзи из текста
  const removeEmojis = (text) => {
    return text.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim();
  };

  // Озвучиваем текст с помощью Web Speech API
  const speakText = (text) => {
    if (!('speechSynthesis' in window)) {
      console.log('❌ Speech Synthesis не поддерживается в этом браузере');
      return;
    }

    // Убираем эмодзи из текста перед озвучиванием
    const cleanText = removeEmojis(text);
    
    if (!cleanText.trim()) {
      console.log('⚠️ Текст пустой после удаления эмодзи, пропускаем озвучивание');
      return;
    }

    console.log('🗣️ Озвучиваю текст:', cleanText.substring(0, 50) + '...');

    // Останавливаем текущую речь
    window.speechSynthesis.cancel();
    
    // Приостанавливаем прослушивание во время речи AI
    const wasListening = isListening;
    if (wasListening) {
      console.log('⏸️ Приостанавливаю прослушивание для речи AI');
      speechRecognition.stop();
    }

    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Улучшенные настройки голоса для более естественного звучания
    utterance.rate = 1.0; // Нормальная скорость речи
    utterance.pitch = 1.0; // Нормальная высота голоса
    utterance.volume = 0.9; // Хорошая громкость
    utterance.lang = 'ru-RU'; // Русский язык
    
    // Ищем лучший русский голос
    const voices = window.speechSynthesis.getVoices();
    console.log('🎵 Поиск качественного русского голоса...');
    
    // Приоритет голосам с лучшим качеством
    const bestRussianVoice = voices.find(voice => 
      voice.lang.startsWith('ru') && 
      (voice.name.toLowerCase().includes('elena') || 
       voice.name.toLowerCase().includes('anna') ||
       voice.name.toLowerCase().includes('maria') ||
       voice.name.toLowerCase().includes('premium') ||
       voice.name.toLowerCase().includes('neural'))
    ) || voices.find(voice => voice.lang.startsWith('ru'));
    
    if (bestRussianVoice) {
      utterance.voice = bestRussianVoice;
      console.log('✅ Выбран голос:', bestRussianVoice.name);
    } else {
      console.log('⚠️ Русский голос не найден, используем системный');
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      console.log('🗣️ AI начала говорить');
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      console.log('🔇 AI закончила говорить');
      
      // Возобновляем прослушивание после речи AI
      if (wasListening) {
        console.log('▶️ Возобновляю прослушивание через 0.5 сек...');
        setTimeout(() => {
          if (speechRecognition) {
            speechRecognition.start();
          }
        }, 500);
      }
    };

    utterance.onerror = (event) => {
      setIsSpeaking(false);
      console.error('❌ Ошибка синтеза речи:', event);
    };

    try {
      window.speechSynthesis.speak(utterance);
      console.log('🎤 Запустил синтез речи');
    } catch (error) {
      console.error('❌ Ошибка при запуске синтеза речи:', error);
      setIsSpeaking(false);
    }
  };

  // Убрал функцию тестирования - больше не нужна

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
        
        // Если активно прослушивание, озвучиваем ответ
        if (isListening) {
          speakText(data.response);
        }
        
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
          
          {(isLoading || isSpeaking) && (
            <div className="ai-diagnosis__message ai-diagnosis__message--ai">
              <div className="ai-diagnosis__message-avatar">🤖</div>
              <div className="ai-diagnosis__message-content">
                {isLoading ? (
                  <div className="ai-diagnosis__loading">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : (
                  <div className="ai-diagnosis__speaking">
                    🗣️ Говорю...
                  </div>
                )}
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
              className={`ai-diagnosis__action-btn ${isListening ? 'ai-diagnosis__action-btn--listening' : ''}`}
              onClick={startSmartListening}
              disabled={!isSupported}
              title={isListening ? 'Голосовое прослушивание активно - говорите! (нажмите для остановки)' : 'Начать голосовой диалог с AI'}
            >
              {isListening ? '🛑' : '🎤'}
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
          {!isSupported && (
            <>
              <br />
              ❌ Голосовые функции недоступны в этом браузере. Попробуйте Chrome.
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIDiagnosis;
