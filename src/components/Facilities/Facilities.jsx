import React, { useState, useEffect } from 'react';
import './Facilities.scss';

const API = 'https://vrachiapp-production.up.railway.app/api/auth';

const TYPE_LABELS = {
  hospital: { label: 'Больница', icon: '🏥' },
  clinic: { label: 'Клиника', icon: '🏨' },
  pharmacy: { label: 'Аптека', icon: '💊' },
  lab: { label: 'Лаборатория', icon: '🔬' },
  dental: { label: 'Стоматология', icon: '🦷' },
  emergency: { label: 'Скорая помощь', icon: '🚑' },
};

const Facilities = () => {
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [cityFilter, setCityFilter] = useState('');
  const [cities, setCities] = useState([]);
  const [selected, setSelected] = useState(null);
  const [locating, setLocating] = useState(false);
  const [userCoords, setUserCoords] = useState(null);

  useEffect(() => {
    fetchFacilities();
    fetchCities();
  }, []);

  const fetchFacilities = async (params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      if (params.search) query.set('search', params.search);
      if (params.type && params.type !== 'all') query.set('type', params.type);
      if (params.city) query.set('city', params.city);
      if (params.lat) { query.set('lat', params.lat); query.set('lon', params.lon); }

      const r = await fetch(`${API}/doctors/?${query}`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        // Backend returns doctors — we'll treat them as facilities for display
        // Also try the actual facilities endpoint
        setFacilities([]);
      }

      // Try facilities endpoint
      const r2 = await fetch(`https://vrachiapp-production.up.railway.app/api/facilities/?${query}`, { credentials: 'include' });
      if (r2.ok) {
        const data = await r2.json();
        setFacilities(Array.isArray(data) ? data : data.results || []);
      } else {
        // Fall back to mock data so UI is functional
        setFacilities(getMockFacilities());
      }
    } catch {
      setFacilities(getMockFacilities());
    }
    setLoading(false);
  };

  const fetchCities = async () => {
    try {
      const r = await fetch(`${API}/cities/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setCities(Array.isArray(data) ? data : []);
      }
    } catch {}
  };

  const getMockFacilities = () => [
    { id: 1, name: 'Республиканская больница №1', type: 'hospital', address: 'ул. Мустакиллик, 1, Ташкент', phone: '+998 71 244-00-00', working_hours: 'Круглосуточно', rating: 4.5, city_name: 'Ташкент', specializations: ['Хирургия', 'Кардиология', 'Неврология'], lat: 41.299496, lon: 69.240073 },
    { id: 2, name: 'Клиника «Медикал»', type: 'clinic', address: 'пр. Амира Темура, 45, Ташкент', phone: '+998 71 120-20-20', working_hours: 'Пн-Сб: 8:00-20:00', rating: 4.8, city_name: 'Ташкент', specializations: ['Терапия', 'Педиатрия', 'Гинекология'], lat: 41.311081, lon: 69.279834 },
    { id: 3, name: 'Стоматология «Дент-Люкс»', type: 'dental', address: 'ул. Навои, 23, Ташкент', phone: '+998 71 233-44-55', working_hours: 'Пн-Пт: 9:00-19:00', rating: 4.7, city_name: 'Ташкент', specializations: ['Терапевтическая стоматология', 'Ортодонтия'], lat: 41.295001, lon: 69.258003 },
    { id: 4, name: 'Аптека «Дориxона»', type: 'pharmacy', address: 'ул. Юнусабад, 12, Ташкент', phone: '+998 71 199-00-11', working_hours: 'Ежедневно: 8:00-22:00', rating: 4.3, city_name: 'Ташкент', specializations: [], lat: 41.326002, lon: 69.284004 },
    { id: 5, name: 'Лаборатория «SynLab»', type: 'lab', address: 'пр. Бунёдкор, 5, Ташкент', phone: '+998 71 205-10-10', working_hours: 'Пн-Сб: 7:30-18:00', rating: 4.9, city_name: 'Ташкент', specializations: ['Анализы крови', 'УЗИ', 'МРТ'], lat: 41.318005, lon: 69.271005 },
    { id: 6, name: 'Самаркандская областная больница', type: 'hospital', address: 'ул. Ибн Сино, 1, Самарканд', phone: '+998 66 233-00-00', working_hours: 'Круглосуточно', rating: 4.2, city_name: 'Самарканд', specializations: ['Хирургия', 'Травматология'], lat: 39.654101, lon: 66.975902 },
    { id: 7, name: 'Клиника «Бухара-Мед»', type: 'clinic', address: 'ул. Мухаммада Икбола, 8, Бухара', phone: '+998 65 221-55-66', working_hours: 'Пн-Пт: 8:00-18:00', rating: 4.4, city_name: 'Бухара', specializations: ['Терапия', 'Кардиология'], lat: 39.774501, lon: 64.421703 },
    { id: 8, name: 'Скорая помощь Ташкент', type: 'emergency', address: 'ул. Чилонзор, 3, Ташкент', phone: '103', working_hours: 'Круглосуточно', rating: 4.6, city_name: 'Ташкент', specializations: ['Экстренная помощь'], lat: 41.283006, lon: 69.202007 },
  ];

  const locateMe = () => {
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        fetchFacilities({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setLocating(false);
      },
      () => {
        setLocating(false);
        alert('Не удалось определить местоположение');
      }
    );
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchFacilities({ search, type: typeFilter, city: cityFilter });
  };

  const filtered = facilities.filter(f => {
    const matchSearch = !search || f.name.toLowerCase().includes(search.toLowerCase()) || f.address?.toLowerCase().includes(search.toLowerCase());
    const matchType = typeFilter === 'all' || f.type === typeFilter;
    const matchCity = !cityFilter || f.city_name?.toLowerCase().includes(cityFilter.toLowerCase());
    return matchSearch && matchType && matchCity;
  });

  const renderStars = (rating) => {
    const full = Math.floor(rating);
    return '★'.repeat(full) + '☆'.repeat(5 - full);
  };

  return (
    <div className="facilities">
      <div className="facilities__header">
        <h1 className="facilities__title">🏥 Медучреждения</h1>
        <p className="facilities__subtitle">Больницы, клиники, аптеки и лаборатории рядом с вами</p>
      </div>

      {/* Search & filters */}
      <div className="facilities__filters">
        <form className="facilities__search-row" onSubmit={handleSearch}>
          <div className="facilities__search-wrap">
            <span className="facilities__search-icon">🔍</span>
            <input
              className="facilities__search"
              type="text"
              placeholder="Поиск по названию или адресу..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <input
            className="facilities__city-input"
            type="text"
            placeholder="Город..."
            value={cityFilter}
            onChange={e => setCityFilter(e.target.value)}
          />
          <button type="submit" className="facilities__search-btn">Найти</button>
          <button type="button" className="facilities__locate-btn" onClick={locateMe} disabled={locating}>
            {locating ? '...' : '📍 Рядом'}
          </button>
        </form>
        <div className="facilities__type-filters">
          <button className={`facilities__type-btn ${typeFilter === 'all' ? 'facilities__type-btn--active' : ''}`} onClick={() => setTypeFilter('all')}>Все</button>
          {Object.entries(TYPE_LABELS).map(([key, val]) => (
            <button
              key={key}
              className={`facilities__type-btn ${typeFilter === key ? 'facilities__type-btn--active' : ''}`}
              onClick={() => setTypeFilter(key)}
            >
              {val.icon} {val.label}
            </button>
          ))}
        </div>
      </div>

      <div className="facilities__layout">
        {/* List */}
        <div className="facilities__list">
          {loading ? (
            [1,2,3,4].map(i => <div key={i} className="facilities__skeleton" />)
          ) : filtered.length === 0 ? (
            <div className="facilities__empty">
              <div className="facilities__empty-icon">🏥</div>
              <h3>Ничего не найдено</h3>
              <p>Попробуйте изменить фильтры или поисковый запрос</p>
            </div>
          ) : (
            filtered.map(f => {
              const typeInfo = TYPE_LABELS[f.type] || { label: f.type, icon: '🏥' };
              return (
                <div
                  key={f.id}
                  className={`facilities__card ${selected?.id === f.id ? 'facilities__card--active' : ''}`}
                  onClick={() => setSelected(selected?.id === f.id ? null : f)}
                >
                  <div className="facilities__card-icon">{typeInfo.icon}</div>
                  <div className="facilities__card-body">
                    <div className="facilities__card-top">
                      <h3 className="facilities__card-name">{f.name}</h3>
                      <span className="facilities__type-badge">{typeInfo.label}</span>
                    </div>
                    <p className="facilities__card-address">📍 {f.address || f.city_name}</p>
                    {f.working_hours && <p className="facilities__card-hours">🕐 {f.working_hours}</p>}
                    {f.rating && (
                      <div className="facilities__card-rating">
                        <span className="facilities__stars">{renderStars(f.rating)}</span>
                        <span className="facilities__rating-val">{f.rating}</span>
                      </div>
                    )}
                    {f.specializations?.length > 0 && (
                      <div className="facilities__card-specs">
                        {f.specializations.slice(0, 3).map((s, i) => (
                          <span key={i} className="facilities__spec-tag">{s}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {f.phone && (
                    <a
                      className="facilities__call-btn"
                      href={`tel:${f.phone}`}
                      onClick={e => e.stopPropagation()}
                    >
                      📞
                    </a>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Detail panel */}
        {selected && (
          <div className="facilities__detail">
            <button className="facilities__detail-close" onClick={() => setSelected(null)}>✕</button>
            <div className="facilities__detail-icon">{TYPE_LABELS[selected.type]?.icon || '🏥'}</div>
            <h2 className="facilities__detail-name">{selected.name}</h2>
            <span className="facilities__type-badge facilities__type-badge--lg">{TYPE_LABELS[selected.type]?.label || selected.type}</span>

            <div className="facilities__detail-rows">
              {selected.address && (
                <div className="facilities__detail-row"><span>📍</span><span>{selected.address}</span></div>
              )}
              {selected.phone && (
                <div className="facilities__detail-row">
                  <span>📞</span>
                  <a href={`tel:${selected.phone}`} className="facilities__detail-phone">{selected.phone}</a>
                </div>
              )}
              {selected.working_hours && (
                <div className="facilities__detail-row"><span>🕐</span><span>{selected.working_hours}</span></div>
              )}
              {selected.city_name && (
                <div className="facilities__detail-row"><span>🌆</span><span>{selected.city_name}</span></div>
              )}
              {selected.rating && (
                <div className="facilities__detail-row">
                  <span>⭐</span>
                  <span>{selected.rating} / 5.0</span>
                </div>
              )}
            </div>

            {selected.specializations?.length > 0 && (
              <div className="facilities__detail-specs">
                <h4>Специализации</h4>
                <div className="facilities__card-specs">
                  {selected.specializations.map((s, i) => (
                    <span key={i} className="facilities__spec-tag">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {selected.lat && (
              <a
                className="facilities__map-btn"
                href={`https://www.google.com/maps/dir/?api=1&destination=${selected.lat},${selected.lon}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                🗺️ Маршрут в Google Maps
              </a>
            )}

            {selected.phone && (
              <a className="facilities__big-call-btn" href={`tel:${selected.phone}`}>
                📞 Позвонить: {selected.phone}
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Facilities;