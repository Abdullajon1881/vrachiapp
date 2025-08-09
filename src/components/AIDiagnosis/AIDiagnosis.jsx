import React, { useState, useRef, useEffect } from 'react';
import './AIDiagnosis.scss';
import { useTranslation } from 'react-i18next';

const AIDiagnosis = () => {
  const { t } = useTranslation();
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
       content: t('ai.welcome', 'Привет! 😊 Я Healzy AI - ваша медицинская помощница! Я женщина-врач с естественным голосом. Можете спросить меня о здоровье, симптомах или медицинских вопросах. Говорите голосом или пишите текст - я всегда рада помочь! ✨'),
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
      setIsSupported(true);
      
      const recognition = new SpeechRecognition();
      
      // Настройки распознавания
      recognition.continuous = true; // Непрерывное распознавание
      recognition.interimResults = true; // Промежуточные результаты
       const lng = (localStorage.getItem('i18nextLng') || 'ru').startsWith('uz') ? 'uz-UZ' : (localStorage.getItem('i18nextLng') || 'ru');
       recognition.lang = lng; // язык распознавания
      recognition.maxAlternatives = 1;
      
      setSpeechRecognition(recognition);
      
      // Предзагружаем голоса для лучшего выбора
      if ('speechSynthesis' in window) {
        const loadVoices = () => {
          const voices = window.speechSynthesis.getVoices();
          
          // Сортируем голоса по качеству (женские голоса сначала)
          const russianVoices = voices
            .filter(voice => voice.lang.startsWith('ru'))
            .sort((a, b) => {
              // Приоритет женским голосам
              const aIsFemale = isFemaleVoice(a.name);
              const bIsFemale = isFemaleVoice(b.name);
              if (aIsFemale && !bIsFemale) return -1;
              if (!aIsFemale && bIsFemale) return 1;
              
              // Приоритет облачным голосам
              if (!a.localService && b.localService) return -1;
              if (a.localService && !b.localService) return 1;
              
              // Приоритет качественным голосам
              const qualityA = getVoiceQuality(a.name);
              const qualityB = getVoiceQuality(b.name);
              return qualityB - qualityA;
            });
          
          setAvailableVoices(russianVoices);
        };
        
        // Принудительно загружаем голоса
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = loadVoices;
        setTimeout(loadVoices, 100);
      }
      
      // Обработчики событий
      recognition.onstart = () => {
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
          handleVoiceInput(finalTranscript.trim());
        }
      };
      
      recognition.onerror = (event) => {
        setIsListening(false);
        
        if (event.error === 'not-allowed') {
          alert(t('ai.allowMic', 'Разрешите доступ к микрофону в настройках браузера'));
        }
      };
      
      recognition.onend = () => {
        setIsListening(false);
      };
      
    } else {
      setIsSupported(false);
    }
    
    // Инициализация голосов для синтеза
    if ('speechSynthesis' in window) {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
        }
      };
      
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Новая система: Speech Recognition API (как в ChatGPT Voice)
  const startSmartListening = () => {
    if (!isSupported) {
      alert(t('ai.noSpeech', 'Speech Recognition не поддерживается в этом браузере. Попробуйте Chrome.'));
      return;
    }
    
    if (isListening) {
      speechRecognition.stop();
      setIsListening(false);
      return;
    }

    
      try {
      speechRecognition.start();
    } catch (error) {
      alert(t('ai.cannotStart', 'Не удалось запустить распознавание речи. Убедитесь что микрофон доступен.'));
    }
  };

  // Обработка голосового ввода от Speech Recognition
  const handleVoiceInput = async (transcript) => {
    
    // Добавляем голосовое сообщение пользователя в чат (показываем как аудио)
    const userMessage = {
      id: Date.now(),
      type: 'user', 
      content: transcript, // Сохраняем текст, но не показываем
      isVoiceMessage: true,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('https://healzy.uz/api/auth/ai/diagnosis/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)')||[]).pop() || ''
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
          isVoiceResponse: data.has_voice,
          audioUrl: data.audio_url,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // Автоматически воспроизводим голосовой ответ
        if (data.has_voice && data.audio_url) {
          setTimeout(() => playAudioResponse(data.audio_url), 300); // Небольшая задержка для лучшего UX
        } else {
          // Fallback к встроенному TTS
          setTimeout(() => speakText(data.response), 300);
        }
        
      } else {
        throw new Error('server');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: t('ai.voiceProcessError', 'Извините, не удалось обработать голосовое сообщение. Попробуйте ещё раз.'),
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      speakText(t('ai.genericError', 'Извините, произошла ошибка. Попробуйте ещё раз.'));
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

  // Воспроизводим голосовой ответ от сервера
  const playAudioResponse = (audioUrl) => {
    try {
      // Останавливаем текущую речь
      window.speechSynthesis.cancel();
      
      // Приостанавливаем прослушивание во время речи AI
      const wasListening = isListening;
      if (wasListening) {
        speechRecognition.stop();
      }

      // Создаем и воспроизводим аудио
      const audio = new Audio(audioUrl);
      audio.preload = 'auto';
      
      setIsSpeaking(true);
      
      audio.onended = () => {
        setIsSpeaking(false);
        
        // Возобновляем прослушивание после речи AI
        if (wasListening) {
          setTimeout(() => {
            if (speechRecognition) {
              speechRecognition.start();
            }
          }, 500);
        }
      };

      audio.onerror = (error) => {
        console.error('Ошибка воспроизведения аудио:', error);
        setIsSpeaking(false);
        
        // Fallback к TTS
        speakText(document.querySelector('.ai-diagnosis__message--ai:last-child .ai-diagnosis__message-text')?.textContent || 'Извините, не удалось воспроизвести ответ');
      };

      audio.play().catch(error => {
        console.error('Не удалось воспроизвести аудио:', error);
        setIsSpeaking(false);
        
        // Fallback к TTS
        speakText(document.querySelector('.ai-diagnosis__message--ai:last-child .ai-diagnosis__message-text')?.textContent || 'Извините, не удалось воспроизвести ответ');
      });
      
    } catch (error) {
      console.error('Ошибка при настройке воспроизведения аудио:', error);
      setIsSpeaking(false);
    }
  };

  // Озвучиваем текст с помощью Web Speech API
  const speakText = (text) => {
    if (!('speechSynthesis' in window)) {
      return;
    }

    // Очищаем текст от всех нежелательных символов
    const cleanText = cleanTextForSpeech(text);
    
        if (!cleanText.trim()) {
      return;
    }


    // Останавливаем текущую речь
    window.speechSynthesis.cancel();
    
    // Приостанавливаем прослушивание во время речи AI
    const wasListening = isListening;
    if (wasListening) {
      speechRecognition.stop();
    }

    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    // Настройки для женского голоса
    utterance.rate = 0.85; // Медленнее для более приятного звучания
    utterance.pitch = 1.4; // Выше для женского голоса
    utterance.volume = 0.9; // Громче
    utterance.lang = 'ru-RU'; // Русский язык
    
    // Используем выбранный пользователем голос или лучший женский голос
    let selectedVoice = null;
    
    if (availableVoices.length > 0) {
      selectedVoice = availableVoices[currentVoiceIndex % availableVoices.length];
    } else {
      // Fallback к автоматическому поиску лучшего женского голоса
      const voices = window.speechSynthesis.getVoices();
      const russianVoices = voices.filter(voice => voice.lang.startsWith('ru'));
      
      // Ищем лучший женский голос
      selectedVoice = russianVoices.find(voice => isFemaleVoice(voice.name)) || 
                     russianVoices.find(voice => voice.name.includes('female')) ||
                     russianVoices[0]; // Первый русский голос как fallback
    }
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;

      
      // Индивидуальные настройки для женских голосов
      const voiceName = selectedVoice.name.toLowerCase();
      const isFemaleName = isFemaleVoice(selectedVoice.name);
      
      if (isFemaleName) {
        // Настройки для женских голосов
        utterance.pitch = 1.3; // Высокий женский тон
        utterance.rate = 0.8;   // Медленнее для более приятного звучания
        utterance.volume = 0.95; // Громче
        
        // Особые настройки для конкретных женских голосов
        if (voiceName.includes('elena')) {
          utterance.pitch = 1.4;
          utterance.rate = 0.85;
        } else if (voiceName.includes('irina')) {
          utterance.pitch = 1.35;
          utterance.rate = 0.8;
        } else if (voiceName.includes('anna') || voiceName.includes('anya')) {
          utterance.pitch = 1.3;
          utterance.rate = 0.85;
        } else if (voiceName.includes('svetlana')) {
          utterance.pitch = 1.25;
          utterance.rate = 0.82;
        } else if (voiceName.includes('maria')) {
          utterance.pitch = 1.35;
          utterance.rate = 0.88;
        }
      } else {
        // Настройки для мужских голосов (делаем их более женственными)
        utterance.pitch = 1.5; // Очень высокий тон для имитации женского голоса
        utterance.rate = 0.75;  // Медленно
        utterance.volume = 0.9;
      }
      
      // Дополнительные настройки для премиальных голосов
      if (voiceName.includes('neural') || voiceName.includes('premium') || voiceName.includes('wavenet')) {
        utterance.rate *= 0.95; // Немного медленнее для лучшего качества
        utterance.volume = Math.min(utterance.volume + 0.05, 1.0);
      }
    } else {
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      
      // Возобновляем прослушивание после речи AI
      if (wasListening) {
        setTimeout(() => {
          if (speechRecognition) {
            speechRecognition.start();
          }
        }, 500);
      }
    };

    utterance.onerror = (event) => {
      setIsSpeaking(false);
    };

    try {
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      setIsSpeaking(false);
    }
  };

  // Функция определения женских голосов
  const isFemaleVoice = (voiceName) => {
    const name = voiceName.toLowerCase();
    
    // Женские имена
    const femaleNames = [
      'elena', 'irina', 'anna', 'anya', 'svetlana', 'maria', 'masha', 
      'katarina', 'kate', 'olga', 'natasha', 'yulia', 'daria', 'victoria',
      'tatiana', 'milena', 'vera', 'nina', 'alexandra', 'alina'
    ];
    
    // Проверяем по именам
    for (const femaleName of femaleNames) {
      if (name.includes(femaleName)) return true;
    }
    
    // Проверяем по стандартным обозначениям
    if (name.includes('female')) return true;
    if (name.includes('woman')) return true;
    if (name.includes('girl')) return true;
    
    // Русские голоса - обычно A и C женские, B и D мужские
    if (name.includes('ru-ru') && (name.includes('-a') || name.includes('-c'))) return true;
    
    return false;
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
      
      // Тестируем новый женский голос
      const testText = isFemaleVoice(newVoice.name) 
        ? 'Привет! Меня зовут Healzy. Я ваша медицинская помощница. Как мой женский голос?'
        : 'Привет! Меня зовут Healzy. Я настроила этот голос как можно более женственно. Как звучу?';
      speakText(testText);
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
          'X-CSRFToken': (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)')||[]).pop() || ''
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
        
        // Если есть голосовой ответ, воспроизводим его, или если активно прослушивание
        if (data.has_voice && data.audio_url) {
          playAudioResponse(data.audio_url);
        } else if (isListening) {
          speakText(data.response);
        }
        
      } else {
        throw new Error(data.error || 'server');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: t('ai.genericError', 'Извините, произошла ошибка. Попробуйте еще раз.'),
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
      alert(t('ai.uploadImageOrVideo', 'Пожалуйста, загрузите изображение или видео'));
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
        throw new Error(data.error || 'server');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: t('ai.fileAnalyzeError', 'Извините, не удалось проанализировать файл. Попробуйте еще раз.'),
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
      alert(t('ai.micAccessError', 'Не удалось получить доступ к микрофону'));
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
    // Добавляем голосовое сообщение пользователя (показываем как аудио)
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: 'Голосовое сообщение',
      isVoiceMessage: true,
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
        // Обновляем пользовательское сообщение с расшифровкой, если она есть
        if (data.transcription) {
          setMessages(prev => prev.map(msg => 
            msg.id === userMessage.id 
              ? { ...msg, content: data.transcription }
              : msg
          ));
        }

        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: data.response,
          isVoiceResponse: data.has_voice,
          audioUrl: data.audio_url,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // Автоматически воспроизводим голосовой ответ
        if (data.has_voice && data.audio_url) {
          setTimeout(() => playAudioResponse(data.audio_url), 300);
        } else {
          setTimeout(() => speakText(data.response), 300);
        }
        
      } else {
        throw new Error(data.error || 'server');
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: t('ai.voiceProcessError', 'Извините, не удалось обработать голосовое сообщение. Попробуйте еще раз.'),
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Форматирование времени
  const formatTime = (date) => {
    const lng = (localStorage.getItem('i18nextLng') || 'ru').startsWith('uz') ? 'uz-UZ' : (localStorage.getItem('i18nextLng') || 'ru');
    return date.toLocaleTimeString(lng, { 
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
              <h1>{t('ai.title', 'Healzy AI Диагностика')}</h1>
              <p>{t('ai.subtitle', 'Персональный медицинский ассистент')}</p>
            </div>
          </div>
          <div className="ai-diagnosis__status">
            <span className="ai-diagnosis__status-indicator"></span>
            {t('ai.online', 'Онлайн')}
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
                {message.isVoiceMessage ? (
                  // Голосовое сообщение пользователя
                  <div className="ai-diagnosis__voice-message">
                    <div className="ai-diagnosis__voice-indicator">
                      🎤 <span className="ai-diagnosis__voice-text">Голосовое сообщение</span>
                      <div className="ai-diagnosis__voice-waves">
                        <span></span><span></span><span></span><span></span>
                      </div>
                    </div>
                  </div>
                ) : message.isVoiceResponse && message.audioUrl ? (
                  // Голосовой ответ AI
                  <div className="ai-diagnosis__voice-response">
                    <div className="ai-diagnosis__voice-indicator ai-diagnosis__voice-indicator--ai">
                      🗣️ <span className="ai-diagnosis__voice-text">Healzy отвечает голосом</span>
                      <div className="ai-diagnosis__voice-waves ai-diagnosis__voice-waves--playing">
                        <span></span><span></span><span></span><span></span>
                      </div>
                    </div>
                    <audio 
                      controls 
                      src={message.audioUrl}
                      className="ai-diagnosis__audio-player"
                      style={{marginTop: '8px', width: '100%', maxWidth: '300px'}}
                    />
                  </div>
                ) : (
                  // Обычное текстовое сообщение
                  <div className="ai-diagnosis__message-text">
                    {message.content}
                  </div>
                )}
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
                    {t('ai.speaking', '🗣️ Говорю...')}
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
              title={t('ai.uploadTitle', 'Загрузить изображение или видео')}
            >
              📷
            </button>
            
            <button
              className={`ai-diagnosis__action-btn ${isListening ? 'ai-diagnosis__action-btn--listening' : ''}`}
              onClick={startSmartListening}
              disabled={!isSupported}
              title={isListening ? t('ai.voiceActive', 'Говорю... (нажмите для остановки)') : t('ai.startVoice', 'Начать голосовой диалог с Healzy AI')}
            >
              {isListening ? '🔴' : '🎤'}
            </button>

            {availableVoices.length > 1 && (
              <button
                className="ai-diagnosis__action-btn"
                onClick={switchVoice}
                disabled={isSpeaking}
                title={
                  availableVoices[currentVoiceIndex] && isFemaleVoice(availableVoices[currentVoiceIndex].name)
                    ? `Женский голос (${currentVoiceIndex + 1}/${availableVoices.length})`
                    : `Голос настроен женственно (${currentVoiceIndex + 1}/${availableVoices.length})`
                }
              >
                👩‍⚕️
              </button>
            )}


          </div>

          <div className="ai-diagnosis__input-container">
            <input
              type="text"
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder={t('ai.placeholder', 'Опишите ваши симптомы или задайте медицинский вопрос...')}
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
          ⚠️ {t('ai.disclaimer1', 'Внимание: AI диагностика не заменяет консультацию врача.')} 
          {t('ai.disclaimer2', 'При серьезных симптомах обратитесь к специалисту.')}
          
          {isSupported && availableVoices.length > 0 && (
            <>
              <br />
              👩‍⚕️ {availableVoices[currentVoiceIndex] && isFemaleVoice(availableVoices[currentVoiceIndex].name)
                ? 'Используется женский голос для ответов'
                : 'Голос настроен максимально женственно'
              }
            </>
          )}
          
          {!isSupported && (
            <>
              <br />
              ❌ {t('ai.voiceUnavailable', 'Голосовые функции недоступны в этом браузере. Попробуйте Chrome.')}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AIDiagnosis;
