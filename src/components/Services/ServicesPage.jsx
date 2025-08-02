import React, { useState } from 'react';
import './ServicesPage.scss';

const ServicesPage = ({ userData }) => {
  const [selectedCategory, setSelectedCategory] = useState('Все');

  const services = [
    // Медицинские услуги
    {
      id: 1,
      title: 'Консультация врача',
      description: 'Онлайн и офлайн консультации с опытными специалистами',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M2 12h20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Медицинские услуги',
      price: 'от 2000 ₽'
    },
    {
      id: 2,
      title: 'Анализы',
      description: 'Лабораторные исследования с быстрыми результатами',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <polyline points="10,9 9,9 8,9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Медицинские услуги',
      price: 'от 1500 ₽'
    },
    {
      id: 3,
      title: 'УЗИ',
      description: 'Ультразвуковые исследования на современном оборудовании',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="9" y1="9" x2="9.01" y2="9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="15" y1="9" x2="15.01" y2="9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Медицинские услуги',
      price: 'от 3000 ₽'
    },
    {
      id: 4,
      title: 'Стоматология',
      description: 'Комплексные стоматологические услуги',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Медицинские услуги',
      price: 'от 5000 ₽'
    },
    // Спортивные и диетические услуги
    {
      id: 5,
      title: 'Спортивная медицина',
      description: 'Консультации и лечение спортивных травм',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M6 4h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 1h3v4H6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M15 1h3v4h-3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 10h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 14h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M6 18h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Спортивные и диетические',
      price: 'от 2500 ₽'
    },
    {
      id: 6,
      title: 'Диетология',
      description: 'Персональные планы питания и консультации диетолога',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M18 8h1a4 4 0 0 1 0 8h-1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="6" y1="1" x2="6" y2="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="10" y1="1" x2="10" y2="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="14" y1="1" x2="14" y2="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Спортивные и диетические',
      price: 'от 3000 ₽'
    },
    // Физиотерапия
    {
      id: 7,
      title: 'Физиотерапия',
      description: 'Современные методы физиотерапевтического лечения',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M12 2v20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Физиотерапия',
      price: 'от 2000 ₽'
    },
    // Массаж
    {
      id: 8,
      title: 'Массаж',
      description: 'Лечебный и расслабляющий массаж от профессионалов',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Массаж',
      price: 'от 2500 ₽'
    },
    // Психологические консультации
    {
      id: 9,
      title: 'Психологическая консультация',
      description: 'Профессиональная психологическая поддержка',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 9h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M8 13h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Психологические консультации',
      price: 'от 4000 ₽'
    },
    // Уход за пожилыми
    {
      id: 10,
      title: 'Уход за пожилыми',
      description: 'Комплексный уход и медицинское сопровождение',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M12 2v20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M2 12h20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      category: 'Уход за пожилыми',
      price: 'от 5000 ₽'
    }
  ];

  // Получаем уникальные категории
  const categories = ['Все', ...new Set(services.map(service => service.category))];

  // Фильтруем услуги по выбранной категории
  const filteredServices = selectedCategory === 'Все' 
    ? services 
    : services.filter(service => service.category === selectedCategory);

  return (
    <div className="services-page">
      <div className="container">
        <div className="services-page__header">
          <h1 className="services-page__title">Все услуги</h1>
          <p className="services-page__subtitle">
            Выберите категорию услуг для удобного поиска
          </p>
        </div>

        {/* Фильтр по категориям */}
        <div className="services-page__filters">
          <div className="category-filters">
            {categories.map((category) => (
              <button
                key={category}
                className={`category-filter ${selectedCategory === category ? 'active' : ''}`}
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Счетчик найденных услуг */}
        <div className="services-page__counter">
          Найдено услуг: {filteredServices.length}
        </div>

        {/* Сетка услуг */}
        <div className="services-page__grid">
          {filteredServices.map((service) => (
            <div key={service.id} className="service-card">
              {userData && userData.role !== 'doctor' && (
                <div className="service-card__icon">
                  {service.icon}
                </div>
              )}
              <div className="service-card__content">
                <div className="service-card__category">{service.category}</div>
                <h3 className="service-card__title">{service.title}</h3>
                <p className="service-card__description">{service.description}</p>
                <div className="service-card__price">{service.price}</div>
                {userData && userData.role !== 'doctor' && (
                  <button className="service-card__btn">
                    Записаться
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Сообщение если услуги не найдены */}
        {filteredServices.length === 0 && (
          <div className="services-page__empty">
            <div className="empty-state">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h3>Услуги не найдены</h3>
              <p>Попробуйте выбрать другую категорию</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ServicesPage; 