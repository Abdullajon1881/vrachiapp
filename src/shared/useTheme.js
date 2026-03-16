import { useEffect, useState } from 'react';

export function useTheme() {
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('darkTheme');
      return saved ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });

  useEffect(() => {
    localStorage.setItem('darkTheme', JSON.stringify(isDarkTheme));
    const appElement = document.querySelector('.app');
    const htmlElement = document.documentElement;
    const bodyElement = document.body;
    if (!appElement || !htmlElement || !bodyElement) return;

    if (isDarkTheme) {
      appElement.classList.add('dark-theme');
      htmlElement.classList.add('dark-theme');
      bodyElement.classList.add('dark-theme');
    } else {
      appElement.classList.remove('dark-theme');
      htmlElement.classList.remove('dark-theme');
      bodyElement.classList.remove('dark-theme');
    }
  }, [isDarkTheme]);

  const toggleTheme = () => setIsDarkTheme((prev) => !prev);

  return { isDarkTheme, toggleTheme };
}

