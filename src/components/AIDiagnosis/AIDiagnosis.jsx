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
  const [availableVoices, setAvailableVoices] = useState([]); // Доступные голоса
  const [currentVoiceIndex, setCurrentVoiceIndex] = useState(0); // Текущий голос
  
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
      
      // Предзагружаем голоса для лучшего выбора
      if ('speechSynthesis' in window) {
        const loadVoices = () => {
          const voices = window.speechSynthesis.getVoices();
          
          // Сортируем голоса по качеству (облачные и премиальные сначала)
          const russianVoices = voices
            .filter(voice => voice.lang.startsWith('ru'))
            .sort((a, b) => {
              // Приоритет облачным голосам
              if (!a.localService && b.localService) return -1;
              if (a.localService && !b.localService) return 1;
              
              // Приоритет качественным голосам
              const qualityA = getVoiceQuality(a.name);
              const qualityB = getVoiceQuality(b.name);
              return qualityB - qualityA;
            });
          
          setAvailableVoices(russianVoices);
          console.log('🎵 Голоса загружены и отсортированы:', voices.length, 'всего, русских:', russianVoices.length);
          console.log('🎯 Топ-3 голоса:', russianVoices.slice(0, 3).map(v => `${v.name} (${v.localService ? 'локальный' : 'облачный'})`));
        };
        
        // Принудительно загружаем голоса
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = loadVoices;
        setTimeout(loadVoices, 100);
      }
      
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
      const response = await fetch('https://healzy.uz/api/auth/ai/diagnosis/', {
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

  // Функция для очистки текста от всех нежелательных символов
  const cleanTextForSpeech = (text) => {
    let cleanText = text;
    
    // Убираем эмодзи
    cleanText = cleanText.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '');
    
    // Убираем специальные символы и знаки препинания которые плохо произносятся
    cleanText = cleanText.replace(/[*#@$%^&()[\]{}|\\<>+=_~`]/g, ' ');
    
    // Убираем множественные пробелы
    cleanText = cleanText.replace(/\s+/g, ' ');
    
    // Заменяем некоторые символы на слова для лучшего произношения
    cleanText = cleanText.replace(/\b\d+\.\s/g, '. '); // "1. текст" -> ". текст"
    cleanText = cleanText.replace(/\bвр\./gi, 'врач'); 
    cleanText = cleanText.replace(/\bдр\./gi, 'доктор');
    cleanText = cleanText.replace(/\bмин\./gi, 'минут');
    cleanText = cleanText.replace(/\bчас\./gi, 'часов');
    
    // Убираем лишние знаки препинания
    cleanText = cleanText.replace(/[,.!?;:]{2,}/g, '. ');
    
    return cleanText.trim();
  };

  // Озвучиваем текст с помощью Web Speech API
  const speakText = (text) => {
    if (!('speechSynthesis' in window)) {
      console.log('❌ Speech Synthesis не поддерживается в этом браузере');
      return;
    }

    // Очищаем текст от всех нежелательных символов
    const cleanText = cleanTextForSpeech(text);
    
        if (!cleanText.trim()) {
      console.log('⚠️ Текст пустой после очистки, пропускаем озвучивание');
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
    
    // Более человеческие настройки голоса
    utterance.rate = 0.9; // Естественная скорость
    utterance.pitch = 1.0; // Нормальная высота
    utterance.volume = 0.85; // Комфортная громкость
    utterance.lang = 'ru-RU'; // Русский язык
    
    // Используем выбранный пользователем голос или автоматический
    let selectedVoice = null;
    
    if (availableVoices.length > 0) {
      selectedVoice = availableVoices[currentVoiceIndex % availableVoices.length];
      console.log(`🎵 Используем голос ${currentVoiceIndex + 1}/${availableVoices.length}:`, selectedVoice.name);
    } else {
      // Fallback к автоматическому поиску
      const voices = window.speechSynthesis.getVoices();
      selectedVoice = voices.find(voice => voice.lang.startsWith('ru'));
      console.log('⚠️ Fallback к автоматическому поиску голоса');
    }
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
      console.log('✅ Выбран голос:', selectedVoice.name, 
                  selectedVoice.localService ? '(локальный)' : '(облачный)');
      
      // Индивидуальные настройки для каждого голоса
      const voiceName = selectedVoice.name.toLowerCase();
      
      if (voiceName.includes('elena')) {
        utterance.rate = 0.92;
        utterance.pitch = 1.0;
        utterance.volume = 0.9;
      } else if (voiceName.includes('irina')) {
        utterance.rate = 0.88;
        utterance.pitch = 0.95;
        utterance.volume = 0.85;
      } else if (voiceName.includes('anna') || voiceName.includes('anya')) {
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        utterance.volume = 0.87;
      } else if (voiceName.includes('svetlana')) {
        utterance.rate = 0.85;
        utterance.pitch = 0.98;
        utterance.volume = 0.88;
      } else if (voiceName.includes('maria')) {
        utterance.rate = 0.9;
        utterance.pitch = 1.02;
        utterance.volume = 0.85;
      } else if (voiceName.includes('pavel') || voiceName.includes('paul')) {
        utterance.rate = 0.88;
        utterance.pitch = 0.9;
        utterance.volume = 0.9;
      } else if (voiceName.includes('alexei') || voiceName.includes('alex')) {
        utterance.rate = 0.9;
        utterance.pitch = 0.92;
        utterance.volume = 0.88;
      }
      
      // Дополнительные настройки для премиальных голосов
      if (voiceName.includes('neural') || voiceName.includes('premium')) {
        utterance.rate *= 0.95; // Немного медленнее для лучшего качества
        utterance.volume = Math.min(utterance.volume + 0.05, 1.0);
      }
    } else {
      console.log('⚠️ Русские голоса не найдены');
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

  // Функция оценки качества голоса
  const getVoiceQuality = (voiceName) => {
    const name = voiceName.toLowerCase();
    let score = 0;
    
    // Премиальные и нейронные голоса
    if (name.includes('neural') || name.includes('wavenet') || name.includes('premium')) score += 50;
    if (name.includes('enhanced') || name.includes('natural')) score += 40;
    
    // Качественные женские голоса (часто звучат естественнее)
    if (name.includes('elena')) score += 30;
    if (name.includes('irina')) score += 25;
    if (name.includes('anna') || name.includes('anya')) score += 25;
    if (name.includes('svetlana')) score += 20;
    if (name.includes('maria') || name.includes('masha')) score += 20;
    if (name.includes('katarina') || name.includes('kate')) score += 15;
    
    // Качественные мужские голоса
    if (name.includes('pavel') || name.includes('paul')) score += 20;
    if (name.includes('alexei') || name.includes('alex')) score += 15;
    if (name.includes('vladimir') || name.includes('vlad')) score += 15;
    
    // Бренды с хорошим качеством
    if (name.includes('microsoft')) score += 10;
    if (name.includes('google')) score += 15;
    if (name.includes('amazon')) score += 12;
    if (name.includes('apple')) score += 8;
    
    return score;
  };

  // Переключение голоса
  const switchVoice = () => {
    if (availableVoices.length > 0) {
      const newIndex = (currentVoiceIndex + 1) % availableVoices.length;
      setCurrentVoiceIndex(newIndex);
      const newVoice = availableVoices[newIndex];
      const quality = getVoiceQuality(newVoice.name);
      console.log(`🔄 Голос ${newIndex + 1}/${availableVoices.length}:`, newVoice.name, `(качество: ${quality})`);
      
      // Тестируем новый голос более естественным текстом
      speakText('Привет! Меня зовут Healzy. Я ваш медицинский помощник. Как этот голос?');
    }
  };

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
      const response = await fetch('https://healzy.uz/api/auth/ai/diagnosis/', {
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

      const response = await fetch('https://healzy.uz/api/auth/ai/diagnosis/', {
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

      const response = await fetch('https://healzy.uz/api/auth/ai/diagnosis/', {
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

            {availableVoices.length > 1 && (
              <button
                className="ai-diagnosis__action-btn"
                onClick={switchVoice}
                disabled={isSpeaking}
                title={`Сменить голос (${currentVoiceIndex + 1}/${availableVoices.length})`}
              >
                🎭
              </button>
            )}


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
