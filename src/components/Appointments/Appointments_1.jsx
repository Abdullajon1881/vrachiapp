import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Appointments.scss';
import { useTranslation } from 'react-i18next';

const API = 'https://vrachiapp-production.up.railway.app/api/auth';

const getCsrf = () =>
  (document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)') || []).pop() || '';

const Appointments = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [tab, setTab] = useState('upcoming'); // upcoming | past | cancel
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [showBook, setShowBook] = useState(false);
  const [slots, setSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [form, setForm] = useState({
    doctor_id: '',
    date: '',
    slot: '',
    symptoms: '',
    appointment_type: 'online',
  });
  const [booking, setBooking] = useState(false);
  const [bookError, setBookError] = useState('');
  const [bookSuccess, setBookSuccess] = useState('');

  useEffect(() => {
    fetchAppointments();
    fetchDoctors();
  }, []);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/appointments/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setAppointments(Array.isArray(data) ? data : data.results || []);
      } else {
        setError('Не удалось загрузить записи');
      }
    } catch {
      setError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  const fetchDoctors = async () => {
    try {
      const r = await fetch(`${API}/doctors/`, { credentials: 'include' });
      if (r.ok) {
        const data = await r.json();
        setDoctors(Array.isArray(data) ? data : data.results || []);
      }
    } catch {}
  };

  const fetchSlots = async (doctorId, date) => {
    if (!doctorId || !date) return;
    setSlotsLoading(true);
    setSlots([]);
    try {
      const r = await fetch(
        `${API}/doctors/${doctorId}/available-slots/?date=${date}`,
        { credentials: 'include' }
      );
      if (r.ok) {
        const data = await r.json();
        setSlots(Array.isArray(data) ? data : data.slots || []);
      }
    } catch {}
    setSlotsLoading(false);
  };

  const handleFormChange = (field, value) => {
    const updated = { ...form, [field]: value };
    setForm(updated);
    if (field === 'doctor_id' || field === 'date') {
      fetchSlots(updated.doctor_id, updated.date);
    }
  };

  const handleBook = async (e) => {
    e.preventDefault();
    setBookError('');
    setBookSuccess('');
    if (!form.doctor_id || !form.date || !form.slot) {
      setBookError('Выберите врача, дату и время');
      return;
    }
    setBooking(true);
    try {
      const r = await fetch(`${API}/appointments/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({
          doctor: parseInt(form.doctor_id),
          appointment_date: `${form.date}T${form.slot}:00`,
          symptoms: form.symptoms,
          appointment_type: form.appointment_type,
        }),
      });
      if (r.ok) {
        setBookSuccess('Запись успешно создана!');
        setShowBook(false);
        setForm({ doctor_id: '', date: '', slot: '', symptoms: '', appointment_type: 'online' });
        fetchAppointments();
      } else {
        const d = await r.json();
        setBookError(d.error || d.detail || 'Ошибка при создании записи');
      }
    } catch {
      setBookError('Ошибка соединения');
    }
    setBooking(false);
  };

  const handleCancel = async (id) => {
    if (!window.confirm('Отменить запись?')) return;
    try {
      const r = await fetch(`${API}/appointments/${id}/cancel/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': getCsrf() },
      });
      if (r.ok) fetchAppointments();
    } catch {}
  };

  const now = new Date();
  const filtered = appointments.filter((a) => {
    const d = new Date(a.appointment_date || a.date);
    if (tab === 'upcoming') return d >= now && a.status !== 'cancelled';
    if (tab === 'past') return d < now || a.status === 'completed';
    return a.status === 'cancelled';
  });

  const statusLabel = (s) => {
    const map = {
      pending: { text: 'Ожидает', cls: 'pending' },
      confirmed: { text: 'Подтверждена', cls: 'confirmed' },
      completed: { text: 'Завершена', cls: 'completed' },
      cancelled: { text: 'Отменена', cls: 'cancelled' },
      scheduled: { text: 'Запланирована', cls: 'confirmed' },
    };
    return map[s] || { text: s, cls: 'pending' };
  };

  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 1);
  const minDateStr = minDate.toISOString().split('T')[0];

  return (
    <div className="appointments">
      <div className="appointments__header">
        <div className="appointments__header-left">
          <h1 className="appointments__title">📅 Мои записи</h1>
          <p className="appointments__subtitle">Управляйте своими визитами к врачу</p>
        </div>
        <button className="appointments__book-btn" onClick={() => { setShowBook(true); setBookError(''); setBookSuccess(''); }}>
          + Записаться к врачу
        </button>
      </div>

      {bookSuccess && <div className="appointments__success">{bookSuccess}</div>}

      {/* Booking modal */}
      {showBook && (
        <div className="appointments__modal-overlay" onClick={() => setShowBook(false)}>
          <div className="appointments__modal" onClick={(e) => e.stopPropagation()}>
            <div className="appointments__modal-header">
              <h2>Записаться к врачу</h2>
              <button className="appointments__modal-close" onClick={() => setShowBook(false)}>✕</button>
            </div>
            <form className="appointments__form" onSubmit={handleBook}>
              <div className="appointments__form-group">
                <label>Врач *</label>
                <select value={form.doctor_id} onChange={(e) => handleFormChange('doctor_id', e.target.value)} required>
                  <option value="">Выберите врача</option>
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.first_name} {d.last_name} — {d.specialization || d.specialization_display || ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="appointments__form-row">
                <div className="appointments__form-group">
                  <label>Дата *</label>
                  <input
                    type="date"
                    min={minDateStr}
                    value={form.date}
                    onChange={(e) => handleFormChange('date', e.target.value)}
                    required
                  />
                </div>
                <div className="appointments__form-group">
                  <label>Тип приёма</label>
                  <select value={form.appointment_type} onChange={(e) => handleFormChange('appointment_type', e.target.value)}>
                    <option value="online">Онлайн</option>
                    <option value="in_person">Очно</option>
                  </select>
                </div>
              </div>
              <div className="appointments__form-group">
                <label>Время *</label>
                {slotsLoading ? (
                  <p className="appointments__slots-loading">Загрузка слотов...</p>
                ) : slots.length > 0 ? (
                  <div className="appointments__slots">
                    {slots.map((s) => (
                      <button
                        key={s}
                        type="button"
                        className={`appointments__slot ${form.slot === s ? 'appointments__slot--active' : ''}`}
                        onClick={() => handleFormChange('slot', s)}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                ) : form.doctor_id && form.date ? (
                  <div className="appointments__slots">
                    {['09:00','09:30','10:00','10:30','11:00','11:30','14:00','14:30','15:00','15:30','16:00','16:30'].map((s) => (
                      <button
                        key={s}
                        type="button"
                        className={`appointments__slot ${form.slot === s ? 'appointments__slot--active' : ''}`}
                        onClick={() => handleFormChange('slot', s)}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="appointments__slots-hint">Сначала выберите врача и дату</p>
                )}
              </div>
              <div className="appointments__form-group">
                <label>Симптомы / причина визита</label>
                <textarea
                  value={form.symptoms}
                  onChange={(e) => handleFormChange('symptoms', e.target.value)}
                  placeholder="Опишите ваши симптомы..."
                  rows={3}
                />
              </div>
              {bookError && <div className="appointments__form-error">{bookError}</div>}
              <div className="appointments__form-actions">
                <button type="button" className="appointments__btn-cancel" onClick={() => setShowBook(false)}>Отмена</button>
                <button type="submit" className="appointments__btn-submit" disabled={booking}>
                  {booking ? 'Записываю...' : 'Записаться'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="appointments__tabs">
        {[
          { id: 'upcoming', label: 'Предстоящие' },
          { id: 'past', label: 'Прошедшие' },
          { id: 'cancelled', label: 'Отменённые' },
        ].map((t) => (
          <button
            key={t.id}
            className={`appointments__tab ${tab === t.id ? 'appointments__tab--active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="appointments__loading">
          {[1, 2, 3].map((i) => <div key={i} className="appointments__skeleton" />)}
        </div>
      ) : error ? (
        <div className="appointments__error">
          <span>⚠️</span>
          <p>{error}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="appointments__empty">
          <div className="appointments__empty-icon">📅</div>
          <h3>Нет записей</h3>
          <p>
            {tab === 'upcoming'
              ? 'У вас пока нет предстоящих визитов'
              : tab === 'past'
              ? 'История визитов пуста'
              : 'Нет отменённых записей'}
          </p>
          {tab === 'upcoming' && (
            <button className="appointments__book-btn" onClick={() => setShowBook(true)}>
              Записаться к врачу
            </button>
          )}
        </div>
      ) : (
        <div className="appointments__list">
          {filtered.map((a) => {
            const st = statusLabel(a.status);
            const dt = new Date(a.appointment_date || a.date);
            return (
              <div key={a.id} className="appointments__card">
                <div className="appointments__card-left">
                  <div className="appointments__card-date">
                    <span className="appointments__card-day">{dt.getDate()}</span>
                    <span className="appointments__card-month">
                      {dt.toLocaleString('ru', { month: 'short' })}
                    </span>
                  </div>
                </div>
                <div className="appointments__card-body">
                  <div className="appointments__card-top">
                    <h3 className="appointments__card-doctor">
                      {a.doctor_name || `Врач #${a.doctor}`}
                    </h3>
                    <span className={`appointments__status appointments__status--${st.cls}`}>{st.text}</span>
                  </div>
                  <p className="appointments__card-spec">{a.doctor_specialization || ''}</p>
                  <div className="appointments__card-meta">
                    <span>🕐 {dt.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}</span>
                    <span>📍 {a.appointment_type === 'online' ? 'Онлайн' : 'Очно'}</span>
                    {a.symptoms && <span>📋 {a.symptoms.slice(0, 40)}...</span>}
                  </div>
                </div>
                <div className="appointments__card-actions">
                  {a.consultation_id && (
                    <button
                      className="appointments__action-btn appointments__action-btn--chat"
                      onClick={() => navigate(`/consultations/${a.consultation_id}`)}
                    >
                      Чат
                    </button>
                  )}
                  {tab === 'upcoming' && a.status !== 'cancelled' && (
                    <button
                      className="appointments__action-btn appointments__action-btn--cancel"
                      onClick={() => handleCancel(a.id)}
                    >
                      Отменить
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Appointments;
