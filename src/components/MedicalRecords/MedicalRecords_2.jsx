import React, { useState, useEffect } from 'react';
import './MedicalRecords.scss';

const API = 'https://vrachiapp-production.up.railway.app/api/auth';
const getCsrf = () =>
  (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)') || []).pop() || '';

const VITAL_ICONS = { blood_pressure: '🩸', heart_rate: '❤️', temperature: '🌡️', weight: '⚖️', height: '📏', glucose: '🍬', oxygen: '💨', default: '📊' };

const MedicalRecords = () => {
  const [tab, setTab] = useState('records');
  const [records, setRecords] = useState([]);
  const [vitals, setVitals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  // Vital signs form
  const [showVitalForm, setShowVitalForm] = useState(false);
  const [vitalForm, setVitalForm] = useState({ type: 'blood_pressure', value: '', unit: '', notes: '' });
  const [savingVital, setSavingVital] = useState(false);
  const [vitalError, setVitalError] = useState('');
  const [vitalSuccess, setVitalSuccess] = useState('');

  const VITAL_TYPES = [
    { value: 'blood_pressure', label: 'Давление', unit: 'мм рт. ст.' },
    { value: 'heart_rate', label: 'Пульс', unit: 'уд/мин' },
    { value: 'temperature', label: 'Температура', unit: '°C' },
    { value: 'weight', label: 'Вес', unit: 'кг' },
    { value: 'height', label: 'Рост', unit: 'см' },
    { value: 'glucose', label: 'Глюкоза', unit: 'ммоль/л' },
    { value: 'oxygen', label: 'Кислород', unit: '%' },
  ];

  useEffect(() => {
    if (tab === 'records') fetchRecords();
    else fetchVitals();
  }, [tab]);

  const fetchRecords = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/medical-records/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setRecords(Array.isArray(data) ? data : data.results || []);
      } else {
        setError('Не удалось загрузить медицинские записи');
      }
    } catch {
      setError('Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const fetchVitals = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/vital-signs/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setVitals(Array.isArray(data) ? data : data.results || []);
      } else {
        setError('Не удалось загрузить показатели');
      }
    } catch {
      setError('Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const handleSaveVital = async (e) => {
    e.preventDefault();
    if (!vitalForm.value) { setVitalError('Введите значение'); return; }
    setSavingVital(true);
    setVitalError('');
    setVitalSuccess('');
    try {
      const r = await fetch(`${API}/vital-signs/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({
          vital_type: vitalForm.type,
          value: vitalForm.value,
          unit: vitalForm.unit || VITAL_TYPES.find(v => v.value === vitalForm.type)?.unit || '',
          notes: vitalForm.notes,
        }),
      });
      if (r.ok) {
        setVitalSuccess('Показатель сохранён!');
        setShowVitalForm(false);
        setVitalForm({ type: 'blood_pressure', value: '', unit: '', notes: '' });
        fetchVitals();
      } else {
        const d = await r.json();
        setVitalError(d.error || d.detail || 'Ошибка сохранения');
      }
    } catch {
      setVitalError('Ошибка соединения');
    }
    setSavingVital(false);
  };

  const typeLabel = (t) => {
    const found = VITAL_TYPES.find(v => v.value === t);
    return found ? found.label : t;
  };

  const recordTypeLabel = (t) => {
    const map = {
      diagnosis: '🩺 Диагноз',
      prescription: '💊 Рецепт',
      lab_result: '🧪 Анализы',
      imaging: '🔬 Снимок',
      note: '📝 Заметка',
      vaccination: '💉 Вакцинация',
    };
    return map[t] || t;
  };

  return (
    <div className="medical-records">
      <div className="medical-records__header">
        <h1 className="medical-records__title">🏥 Медицинские записи</h1>
        <p className="medical-records__subtitle">История болезней, анализов и показателей здоровья</p>
      </div>

      <div className="medical-records__tabs">
        <button
          className={`medical-records__tab ${tab === 'records' ? 'medical-records__tab--active' : ''}`}
          onClick={() => setTab('records')}
        >
          📋 Медкарта
        </button>
        <button
          className={`medical-records__tab ${tab === 'vitals' ? 'medical-records__tab--active' : ''}`}
          onClick={() => setTab('vitals')}
        >
          📊 Показатели
        </button>
      </div>

      {tab === 'vitals' && (
        <div className="medical-records__vitals-actions">
          {vitalSuccess && <div className="medical-records__success">{vitalSuccess}</div>}
          <button className="medical-records__add-btn" onClick={() => { setShowVitalForm(true); setVitalError(''); setVitalSuccess(''); }}>
            + Добавить показатель
          </button>
        </div>
      )}

      {/* Vital form modal */}
      {showVitalForm && (
        <div className="medical-records__overlay" onClick={() => setShowVitalForm(false)}>
          <div className="medical-records__modal" onClick={(e) => e.stopPropagation()}>
            <div className="medical-records__modal-header">
              <h2>Добавить показатель</h2>
              <button onClick={() => setShowVitalForm(false)}>✕</button>
            </div>
            <form className="medical-records__form" onSubmit={handleSaveVital}>
              <div className="medical-records__form-group">
                <label>Тип показателя</label>
                <select
                  value={vitalForm.type}
                  onChange={(e) => setVitalForm({ ...vitalForm, type: e.target.value })}
                >
                  {VITAL_TYPES.map(v => (
                    <option key={v.value} value={v.value}>{v.label} ({v.unit})</option>
                  ))}
                </select>
              </div>
              <div className="medical-records__form-row">
                <div className="medical-records__form-group">
                  <label>Значение *</label>
                  <input
                    type="text"
                    placeholder="Например: 120/80"
                    value={vitalForm.value}
                    onChange={(e) => setVitalForm({ ...vitalForm, value: e.target.value })}
                    required
                  />
                </div>
                <div className="medical-records__form-group">
                  <label>Единица</label>
                  <input
                    type="text"
                    placeholder={VITAL_TYPES.find(v => v.value === vitalForm.type)?.unit || ''}
                    value={vitalForm.unit}
                    onChange={(e) => setVitalForm({ ...vitalForm, unit: e.target.value })}
                  />
                </div>
              </div>
              <div className="medical-records__form-group">
                <label>Заметка</label>
                <textarea
                  value={vitalForm.notes}
                  onChange={(e) => setVitalForm({ ...vitalForm, notes: e.target.value })}
                  rows={2}
                  placeholder="Дополнительная информация..."
                />
              </div>
              {vitalError && <div className="medical-records__form-error">{vitalError}</div>}
              <div className="medical-records__form-actions">
                <button type="button" className="medical-records__btn-cancel" onClick={() => setShowVitalForm(false)}>Отмена</button>
                <button type="submit" className="medical-records__btn-submit" disabled={savingVital}>
                  {savingVital ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="medical-records__loading">
          {[1, 2, 3].map(i => <div key={i} className="medical-records__skeleton" />)}
        </div>
      ) : error ? (
        <div className="medical-records__error"><span>⚠️</span><p>{error}</p></div>
      ) : tab === 'records' ? (
        records.length === 0 ? (
          <div className="medical-records__empty">
            <div className="medical-records__empty-icon">📋</div>
            <h3>Медкарта пуста</h3>
            <p>Ваши медицинские записи появятся здесь после консультаций с врачом</p>
          </div>
        ) : (
          <div className="medical-records__content">
            <div className="medical-records__list">
              {records.map(rec => (
                <div
                  key={rec.id}
                  className={`medical-records__item ${selected?.id === rec.id ? 'medical-records__item--active' : ''}`}
                  onClick={() => setSelected(selected?.id === rec.id ? null : rec)}
                >
                  <div className="medical-records__item-icon">
                    {recordTypeLabel(rec.record_type).split(' ')[0]}
                  </div>
                  <div className="medical-records__item-body">
                    <div className="medical-records__item-top">
                      <span className="medical-records__item-type">{recordTypeLabel(rec.record_type).split(' ').slice(1).join(' ')}</span>
                      <span className="medical-records__item-date">
                        {new Date(rec.created_at || rec.date).toLocaleDateString('ru')}
                      </span>
                    </div>
                    <p className="medical-records__item-title">{rec.title || rec.diagnosis || 'Без названия'}</p>
                    {rec.doctor_name && <p className="medical-records__item-doctor">👨‍⚕️ {rec.doctor_name}</p>}
                  </div>
                  <div className="medical-records__item-chevron">{selected?.id === rec.id ? '▲' : '▼'}</div>
                </div>
              ))}
            </div>

            {selected && (
              <div className="medical-records__detail">
                <h3>{selected.title || selected.diagnosis || 'Детали записи'}</h3>
                {selected.description && <p className="medical-records__detail-text">{selected.description}</p>}
                {selected.diagnosis && selected.title !== selected.diagnosis && (
                  <div className="medical-records__detail-row"><span>Диагноз:</span><span>{selected.diagnosis}</span></div>
                )}
                {selected.treatment && <div className="medical-records__detail-row"><span>Лечение:</span><span>{selected.treatment}</span></div>}
                {selected.prescriptions && <div className="medical-records__detail-row"><span>Рецепт:</span><span>{selected.prescriptions}</span></div>}
                {selected.notes && <div className="medical-records__detail-row"><span>Заметки:</span><span>{selected.notes}</span></div>}
                {selected.doctor_name && <div className="medical-records__detail-row"><span>Врач:</span><span>{selected.doctor_name}</span></div>}
                <div className="medical-records__detail-row">
                  <span>Дата:</span>
                  <span>{new Date(selected.created_at || selected.date).toLocaleString('ru')}</span>
                </div>
              </div>
            )}
          </div>
        )
      ) : (
        vitals.length === 0 ? (
          <div className="medical-records__empty">
            <div className="medical-records__empty-icon">📊</div>
            <h3>Нет показателей</h3>
            <p>Начните отслеживать своё здоровье — добавьте первый показатель</p>
          </div>
        ) : (
          <div className="medical-records__vitals-grid">
            {VITAL_TYPES.map(vtype => {
              const typeVitals = vitals
                .filter(v => v.vital_type === vtype.value)
                .sort((a, b) => new Date(b.recorded_at || b.date) - new Date(a.recorded_at || a.date));
              if (typeVitals.length === 0) return null;
              const latest = typeVitals[0];
              return (
                <div key={vtype.value} className="medical-records__vital-card">
                  <div className="medical-records__vital-icon">
                    {VITAL_ICONS[vtype.value] || VITAL_ICONS.default}
                  </div>
                  <div className="medical-records__vital-label">{vtype.label}</div>
                  <div className="medical-records__vital-value">
                    {latest.value}
                    <span className="medical-records__vital-unit">{latest.unit || vtype.unit}</span>
                  </div>
                  <div className="medical-records__vital-date">
                    {new Date(latest.recorded_at || latest.date).toLocaleDateString('ru')}
                  </div>
                  {typeVitals.length > 1 && (
                    <div className="medical-records__vital-history">
                      {typeVitals.slice(1, 4).map((v, i) => (
                        <div key={i} className="medical-records__vital-history-item">
                          <span>{v.value} {v.unit || vtype.unit}</span>
                          <span>{new Date(v.recorded_at || v.date).toLocaleDateString('ru')}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
};

export default MedicalRecords;
