import React, { useState, useEffect } from 'react';
import './HealthNews.scss';

const API = 'https://vrachiapp-production.up.railway.app/api/auth';

const CATEGORIES = [
  { id: 'all', label: '📰 Все' },
  { id: 'cardiology', label: '❤️ Кардиология' },
  { id: 'nutrition', label: '🥗 Питание' },
  { id: 'mental_health', label: '🧠 Психология' },
  { id: 'fitness', label: '💪 Фитнес' },
  { id: 'prevention', label: '🛡️ Профилактика' },
  { id: 'medicine', label: '💊 Медицина' },
];

const FALLBACK_NEWS = [
  { id: 1, title: 'Как укрепить иммунитет в сезон простуд', category: 'prevention', date: '2026-03-10', read_time: 4, summary: 'Учёные выделили 5 ключевых привычек, которые значительно снижают риск заболеть в холодное время года. Регулярные прогулки, сбалансированное питание и достаточный сон — основа крепкого иммунитета.', image_emoji: '🛡️', source: 'HealthUz' },
  { id: 2, title: '10 продуктов, полезных для сердца', category: 'cardiology', date: '2026-03-09', read_time: 5, summary: 'Кардиологи составили список продуктов, регулярное употребление которых снижает риск сердечно-сосудистых заболеваний. На первом месте — жирная рыба, орехи и оливковое масло.', image_emoji: '❤️', source: 'Cardio Today' },
  { id: 3, title: 'Стресс и здоровье: как управлять эмоциями', category: 'mental_health', date: '2026-03-08', read_time: 6, summary: 'Хронический стресс влияет не только на психику, но и на физическое здоровье. Психологи рассказали о простых техниках управления стрессом, доступных каждому.', image_emoji: '🧠', source: 'Mind & Body' },
  { id: 4, title: 'Средиземноморская диета: научные доказательства', category: 'nutrition', date: '2026-03-07', read_time: 7, summary: 'Новое исследование подтвердило: средиземноморская диета снижает риск диабета второго типа на 30%. В основе — свежие овощи, рыба и цельнозерновые продукты.', image_emoji: '🥗', source: 'Nutrition Science' },
  { id: 5, title: '20 минут в день: минимум для здоровья', category: 'fitness', date: '2026-03-06', read_time: 3, summary: 'ВОЗ обновила рекомендации по физической активности. Выяснилось, что даже 20 минут умеренной нагрузки в день значительно снижают риск хронических заболеваний.', image_emoji: '💪', source: 'WHO Bulletin' },
  { id: 6, title: 'Новый метод ранней диагностики рака', category: 'medicine', date: '2026-03-05', read_time: 8, summary: 'Учёные разработали анализ крови, способный выявить до 50 видов рака на ранней стадии. Тест показал точность 92% в клинических испытаниях.', image_emoji: '🔬', source: 'Medical Tribune' },
  { id: 7, title: 'Сон и здоровье мозга: новые данные', category: 'mental_health', date: '2026-03-04', read_time: 5, summary: 'Нейробиологи выяснили, что качество сна напрямую влияет на очищение мозга от токсинов. 7–9 часов сна — ключ к профилактике болезни Альцгеймера.', image_emoji: '😴', source: 'Neuro Today' },
  { id: 8, title: 'Вакцинация взрослых: что нужно знать', category: 'prevention', date: '2026-03-03', read_time: 4, summary: 'Многие взрослые не знают, какие прививки им необходимо обновить. Инфекционисты составили чёткий список вакцин для разных возрастных групп.', image_emoji: '💉', source: 'HealthUz' },
];

const HEALTH_TIPS = [
  { icon: '💧', title: 'Пейте воду', text: 'Выпивайте минимум 8 стаканов (2 л) воды в день для поддержания всех функций организма.' },
  { icon: '🚶', title: 'Ходите пешком', text: 'Ежедневные прогулки по 30 минут снижают риск сердечно-сосудистых заболеваний на 35%.' },
  { icon: '🥦', title: 'Ешьте овощи', text: 'Употребляйте не менее 5 порций овощей и фруктов в день для получения витаминов и клетчатки.' },
  { icon: '😴', title: 'Спите 7–9 часов', text: 'Качественный сон укрепляет иммунитет, улучшает память и снижает риск ожирения.' },
  { icon: '🧘', title: 'Снижайте стресс', text: 'Медитация, дыхательные упражнения и йога помогают снизить уровень кортизола.' },
  { icon: '🚭', title: 'Откажитесь от курения', text: 'Курение — причина 30% онкологических заболеваний. Отказ от него снижает риск инфаркта вдвое.' },
];

const HealthNews = () => {
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/health-news/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        const items = Array.isArray(data) ? data : data.results || [];
        setNews(items.length > 0 ? items : FALLBACK_NEWS);
      } else {
        setNews(FALLBACK_NEWS);
      }
    } catch {
      setNews(FALLBACK_NEWS);
    }
    setLoading(false);
  };

  const filtered = news.filter(n => {
    const matchCat = category === 'all' || n.category === category;
    const matchSearch = !search || n.title.toLowerCase().includes(search.toLowerCase()) || n.summary?.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  const formatDate = (d) => {
    try { return new Date(d).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return d; }
  };

  if (selected) {
    return (
      <div className="health-news">
        <button className="health-news__back" onClick={() => setSelected(null)}>← Назад к новостям</button>
        <article className="health-news__article">
          <div className="health-news__article-emoji">{selected.image_emoji || '📰'}</div>
          <div className="health-news__article-meta">
            <span className="health-news__article-cat">{CATEGORIES.find(c => c.id === selected.category)?.label || selected.category}</span>
            <span className="health-news__article-date">{formatDate(selected.date)}</span>
            {selected.read_time && <span className="health-news__article-time">⏱ {selected.read_time} мин</span>}
          </div>
          <h1 className="health-news__article-title">{selected.title}</h1>
          {selected.source && <p className="health-news__article-source">Источник: {selected.source}</p>}
          <div className="health-news__article-body">
            <p>{selected.summary}</p>
            {selected.content && <div dangerouslySetInnerHTML={{ __html: selected.content }} />}
          </div>
        </article>
      </div>
    );
  }

  return (
    <div className="health-news">
      <div className="health-news__header">
        <h1 className="health-news__title">📰 Здоровье и новости</h1>
        <p className="health-news__subtitle">Актуальные статьи, советы и новости медицины</p>
      </div>

      {/* Tips strip */}
      <div className="health-news__tips">
        {HEALTH_TIPS.map((tip, i) => (
          <div key={i} className="health-news__tip-card">
            <span className="health-news__tip-icon">{tip.icon}</span>
            <strong className="health-news__tip-title">{tip.title}</strong>
            <p className="health-news__tip-text">{tip.text}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="health-news__filters">
        <div className="health-news__search-wrap">
          <span>🔍</span>
          <input
            type="text"
            placeholder="Поиск статей..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="health-news__search"
          />
        </div>
        <div className="health-news__categories">
          {CATEGORIES.map(c => (
            <button
              key={c.id}
              className={`health-news__cat-btn ${category === c.id ? 'health-news__cat-btn--active' : ''}`}
              onClick={() => setCategory(c.id)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* News grid */}
      {loading ? (
        <div className="health-news__grid">
          {[1,2,3,4,5,6].map(i => <div key={i} className="health-news__skeleton" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="health-news__empty">
          <div>📰</div>
          <h3>Ничего не найдено</h3>
          <p>Попробуйте другой запрос или категорию</p>
        </div>
      ) : (
        <div className="health-news__grid">
          {filtered.map(item => (
            <div
              key={item.id}
              className="health-news__card"
              onClick={() => setSelected(item)}
            >
              <div className="health-news__card-emoji">{item.image_emoji || '📰'}</div>
              <div className="health-news__card-body">
                <div className="health-news__card-meta">
                  <span className="health-news__card-cat">
                    {CATEGORIES.find(c => c.id === item.category)?.label || item.category}
                  </span>
                  {item.read_time && <span className="health-news__card-time">⏱ {item.read_time} мин</span>}
                </div>
                <h3 className="health-news__card-title">{item.title}</h3>
                <p className="health-news__card-summary">{item.summary}</p>
                <div className="health-news__card-footer">
                  <span className="health-news__card-date">{formatDate(item.date)}</span>
                  {item.source && <span className="health-news__card-source">{item.source}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HealthNews;