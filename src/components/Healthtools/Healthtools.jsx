import React, { useState } from 'react';
import './HealthTools.scss';

// ─── BMI Calculator ───────────────────────────────────────────────────────────
const BMICalculator = () => {
  const [form, setForm] = useState({ weight: '', height: '', age: '', gender: 'male' });
  const [result, setResult] = useState(null);

  const calc = () => {
    const w = parseFloat(form.weight);
    const h = parseFloat(form.height) / 100;
    if (!w || !h || h <= 0) return;
    const bmi = w / (h * h);
    let category, color, advice;
    if (bmi < 18.5) { category = 'Недовес'; color = '#2196f3'; advice = 'Рекомендуется увеличить калорийность питания и проконсультироваться с врачом.'; }
    else if (bmi < 25) { category = 'Норма'; color = '#4caf50'; advice = 'Отличный результат! Поддерживайте здоровый образ жизни.'; }
    else if (bmi < 30) { category = 'Избыточный вес'; color = '#ff9800'; advice = 'Рекомендуется умеренная физическая активность и сбалансированное питание.'; }
    else { category = 'Ожирение'; color = '#f44336'; advice = 'Обратитесь к врачу для составления плана по снижению веса.'; }
    const idealMin = (18.5 * h * h).toFixed(1);
    const idealMax = (24.9 * h * h).toFixed(1);
    setResult({ bmi: bmi.toFixed(1), category, color, advice, idealMin, idealMax });
  };

  return (
    <div className="health-tools__tool">
      <h2>⚖️ Индекс массы тела (ИМТ)</h2>
      <p className="health-tools__tool-desc">Рассчитайте свой ИМТ и узнайте, соответствует ли ваш вес норме</p>
      <div className="health-tools__form">
        <div className="health-tools__form-row">
          <div className="health-tools__field">
            <label>Вес (кг)</label>
            <input type="number" placeholder="70" value={form.weight} onChange={e => setForm({...form, weight: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Рост (см)</label>
            <input type="number" placeholder="175" value={form.height} onChange={e => setForm({...form, height: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Возраст</label>
            <input type="number" placeholder="30" value={form.age} onChange={e => setForm({...form, age: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Пол</label>
            <select value={form.gender} onChange={e => setForm({...form, gender: e.target.value})}>
              <option value="male">Мужской</option>
              <option value="female">Женский</option>
            </select>
          </div>
        </div>
        <button className="health-tools__calc-btn" onClick={calc}>Рассчитать</button>
      </div>
      {result && (
        <div className="health-tools__result" style={{'--res-color': result.color}}>
          <div className="health-tools__result-main">
            <span className="health-tools__result-value">{result.bmi}</span>
            <span className="health-tools__result-label" style={{color: result.color}}>{result.category}</span>
          </div>
          <div className="health-tools__bmi-scale">
            <div className="health-tools__bmi-bar">
              <div className="health-tools__bmi-fill" style={{left: `${Math.min(Math.max((result.bmi - 10) / 30 * 100, 0), 100)}%`}} />
              {[{v:18.5,l:'18.5'},{v:25,l:'25'},{v:30,l:'30'}].map(m => (
                <div key={m.v} className="health-tools__bmi-mark" style={{left: `${(m.v - 10) / 30 * 100}%`}}>
                  <span>{m.l}</span>
                </div>
              ))}
            </div>
            <div className="health-tools__bmi-zones">
              <span style={{color:'#2196f3'}}>Недовес</span>
              <span style={{color:'#4caf50'}}>Норма</span>
              <span style={{color:'#ff9800'}}>Избыток</span>
              <span style={{color:'#f44336'}}>Ожирение</span>
            </div>
          </div>
          <p className="health-tools__result-advice">{result.advice}</p>
          <p className="health-tools__result-ideal">Идеальный вес для вашего роста: <strong>{result.idealMin} – {result.idealMax} кг</strong></p>
        </div>
      )}
    </div>
  );
};

// ─── Water Tracker ────────────────────────────────────────────────────────────
const WaterTracker = () => {
  const [glasses, setGlasses] = useState(0);
  const [weight, setWeight] = useState('');
  const goal = weight ? Math.round(parseFloat(weight) * 35) : 2000;
  const pct = Math.min((glasses * 250) / goal * 100, 100);

  return (
    <div className="health-tools__tool">
      <h2>💧 Трекер воды</h2>
      <p className="health-tools__tool-desc">Отслеживайте суточное потребление воды</p>
      <div className="health-tools__form">
        <div className="health-tools__field" style={{maxWidth: 200}}>
          <label>Ваш вес (кг) — для расчёта нормы</label>
          <input type="number" placeholder="70" value={weight} onChange={e => setWeight(e.target.value)} />
        </div>
      </div>
      <div className="health-tools__water">
        <div className="health-tools__water-circle">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#e3f2fd" strokeWidth="10" />
            <circle cx="60" cy="60" r="54" fill="none" stroke="#095880" strokeWidth="10"
              strokeDasharray={`${2 * Math.PI * 54}`}
              strokeDashoffset={`${2 * Math.PI * 54 * (1 - pct / 100)}`}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
              style={{transition: 'stroke-dashoffset 0.5s ease'}}
            />
          </svg>
          <div className="health-tools__water-text">
            <span className="health-tools__water-ml">{glasses * 250}</span>
            <span className="health-tools__water-total">/ {goal} мл</span>
          </div>
        </div>
        <div className="health-tools__water-controls">
          <p className="health-tools__water-pct">{Math.round(pct)}% от нормы</p>
          <div className="health-tools__water-btns">
            <button className="health-tools__water-btn health-tools__water-btn--minus" onClick={() => setGlasses(Math.max(0, glasses - 1))}>− Стакан</button>
            <button className="health-tools__water-btn health-tools__water-btn--plus" onClick={() => setGlasses(glasses + 1)}>+ Стакан (250мл)</button>
          </div>
          <div className="health-tools__water-glasses">
            {Array.from({length: Math.max(8, glasses)}, (_, i) => (
              <span key={i} className={`health-tools__glass ${i < glasses ? 'health-tools__glass--filled' : ''}`}>🥛</span>
            ))}
          </div>
          <button className="health-tools__reset-btn" onClick={() => setGlasses(0)}>Сбросить</button>
        </div>
      </div>
    </div>
  );
};

// ─── Calorie Calculator ───────────────────────────────────────────────────────
const CalorieCalculator = () => {
  const [form, setForm] = useState({ weight: '', height: '', age: '', gender: 'male', activity: '1.55' });
  const [result, setResult] = useState(null);

  const ACTIVITIES = [
    { value: '1.2', label: 'Сидячий образ жизни' },
    { value: '1.375', label: 'Лёгкая активность (1-3 раза/нед)' },
    { value: '1.55', label: 'Умеренная активность (3-5 раз/нед)' },
    { value: '1.725', label: 'Высокая активность (6-7 раз/нед)' },
    { value: '1.9', label: 'Очень высокая активность' },
  ];

  const calc = () => {
    const w = parseFloat(form.weight), h = parseFloat(form.height), a = parseFloat(form.age), act = parseFloat(form.activity);
    if (!w || !h || !a) return;
    let bmr = form.gender === 'male'
      ? 10 * w + 6.25 * h - 5 * a + 5
      : 10 * w + 6.25 * h - 5 * a - 161;
    const tdee = Math.round(bmr * act);
    setResult({
      bmr: Math.round(bmr),
      maintenance: tdee,
      loss: tdee - 500,
      gain: tdee + 500,
      protein: Math.round(w * 2),
      fat: Math.round(tdee * 0.25 / 9),
      carbs: Math.round((tdee - w * 2 * 4 - (tdee * 0.25)) / 4),
    });
  };

  return (
    <div className="health-tools__tool">
      <h2>🔥 Калькулятор калорий</h2>
      <p className="health-tools__tool-desc">Узнайте суточную норму калорий и макронутриентов</p>
      <div className="health-tools__form">
        <div className="health-tools__form-row">
          <div className="health-tools__field">
            <label>Вес (кг)</label>
            <input type="number" placeholder="70" value={form.weight} onChange={e => setForm({...form, weight: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Рост (см)</label>
            <input type="number" placeholder="175" value={form.height} onChange={e => setForm({...form, height: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Возраст</label>
            <input type="number" placeholder="30" value={form.age} onChange={e => setForm({...form, age: e.target.value})} />
          </div>
          <div className="health-tools__field">
            <label>Пол</label>
            <select value={form.gender} onChange={e => setForm({...form, gender: e.target.value})}>
              <option value="male">Мужской</option>
              <option value="female">Женский</option>
            </select>
          </div>
        </div>
        <div className="health-tools__field">
          <label>Уровень активности</label>
          <select value={form.activity} onChange={e => setForm({...form, activity: e.target.value})}>
            {ACTIVITIES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>
        <button className="health-tools__calc-btn" onClick={calc}>Рассчитать</button>
      </div>
      {result && (
        <div className="health-tools__calories-result">
          <div className="health-tools__calorie-cards">
            {[
              { label: 'Для похудения', val: result.loss, color: '#2196f3', icon: '📉' },
              { label: 'Для поддержания', val: result.maintenance, color: '#4caf50', icon: '⚖️' },
              { label: 'Для набора', val: result.gain, color: '#ff9800', icon: '📈' },
            ].map(c => (
              <div key={c.label} className="health-tools__calorie-card" style={{'--c': c.color}}>
                <span className="health-tools__calorie-icon">{c.icon}</span>
                <span className="health-tools__calorie-val">{c.val}</span>
                <span className="health-tools__calorie-unit">ккал/день</span>
                <span className="health-tools__calorie-label">{c.label}</span>
              </div>
            ))}
          </div>
          <div className="health-tools__macros">
            <h4>Рекомендуемые макронутриенты (для поддержания)</h4>
            <div className="health-tools__macro-bars">
              {[
                { label: 'Белки', val: result.protein, unit: 'г', color: '#f44336', pct: 30 },
                { label: 'Жиры', val: result.fat, unit: 'г', color: '#ff9800', pct: 25 },
                { label: 'Углеводы', val: result.carbs, unit: 'г', color: '#4caf50', pct: 45 },
              ].map(m => (
                <div key={m.label} className="health-tools__macro-row">
                  <span className="health-tools__macro-label">{m.label}</span>
                  <div className="health-tools__macro-bar-wrap">
                    <div className="health-tools__macro-bar-fill" style={{width: `${m.pct}%`, background: m.color}} />
                  </div>
                  <span className="health-tools__macro-val">{m.val}{m.unit}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Symptom Checker ──────────────────────────────────────────────────────────
const SYMPTOMS = [
  { id: 'headache', label: '🤕 Головная боль' },
  { id: 'fever', label: '🌡️ Температура' },
  { id: 'cough', label: '😮‍💨 Кашель' },
  { id: 'fatigue', label: '😴 Усталость' },
  { id: 'nausea', label: '🤢 Тошнота' },
  { id: 'chest_pain', label: '💔 Боль в груди' },
  { id: 'back_pain', label: '🦴 Боль в спине' },
  { id: 'sore_throat', label: '🗣️ Боль в горле' },
  { id: 'runny_nose', label: '🤧 Насморк' },
  { id: 'dizziness', label: '😵 Головокружение' },
  { id: 'shortness_of_breath', label: '😤 Одышка' },
  { id: 'stomach_pain', label: '🤢 Боль в животе' },
  { id: 'joint_pain', label: '🦵 Боль в суставах' },
  { id: 'skin_rash', label: '🔴 Сыпь на коже' },
  { id: 'insomnia', label: '🌙 Бессонница' },
  { id: 'loss_of_appetite', label: '🍽️ Потеря аппетита' },
];

const ADVICE = {
  headache: { spec: 'Невролог', urgency: 'low', tip: 'Выпейте воды, отдохните в тёмной комнате. При сильной боли — обратитесь к врачу.' },
  fever: { spec: 'Терапевт', urgency: 'medium', tip: 'При температуре выше 38.5°C примите жаропонижающее. При 39°C+ — вызовите врача.' },
  cough: { spec: 'Терапевт / Пульмонолог', urgency: 'low', tip: 'Пейте тёплые жидкости. При влажном кашле с кровью — срочно к врачу.' },
  chest_pain: { spec: 'Кардиолог', urgency: 'high', tip: '⚠️ Боль в груди требует немедленной медицинской помощи!' },
  shortness_of_breath: { spec: 'Кардиолог / Пульмонолог', urgency: 'high', tip: '⚠️ Одышка в покое — срочно вызовите скорую помощь!' },
  dizziness: { spec: 'Невролог', urgency: 'medium', tip: 'Сядьте или лягте. Если головокружение сопровождается рвотой — обратитесь к врачу.' },
  default: { spec: 'Терапевт', urgency: 'low', tip: 'Запишитесь к терапевту для общего осмотра.' },
};

const URGENCY_COLORS = { low: '#4caf50', medium: '#ff9800', high: '#f44336' };
const URGENCY_LABELS = { low: 'Плановый приём', medium: 'В течение 1-2 дней', high: '🚨 Срочно!' };

const SymptomChecker = () => {
  const [selected, setSelected] = useState([]);
  const [duration, setDuration] = useState('');
  const [result, setResult] = useState(null);

  const toggle = (id) => setSelected(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);

  const check = () => {
    if (selected.length === 0) return;
    const urgentSymptoms = selected.filter(s => ADVICE[s]?.urgency === 'high');
    const specialists = [...new Set(selected.map(s => (ADVICE[s] || ADVICE.default).spec))];
    const topUrgency = urgentSymptoms.length > 0 ? 'high' : selected.some(s => ADVICE[s]?.urgency === 'medium') ? 'medium' : 'low';
    const tips = selected.map(s => ADVICE[s]?.tip).filter(Boolean);
    setResult({ specialists, urgency: topUrgency, tips, count: selected.length });
  };

  return (
    <div className="health-tools__tool">
      <h2>🔍 Проверка симптомов</h2>
      <p className="health-tools__tool-desc">Выберите симптомы — узнайте к какому врачу обратиться</p>
      <div className="health-tools__symptoms-grid">
        {SYMPTOMS.map(s => (
          <button
            key={s.id}
            className={`health-tools__symptom-btn ${selected.includes(s.id) ? 'health-tools__symptom-btn--active' : ''}`}
            onClick={() => toggle(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="health-tools__form" style={{marginTop: 16}}>
        <div className="health-tools__field" style={{maxWidth: 280}}>
          <label>Как давно беспокоят симптомы?</label>
          <select value={duration} onChange={e => setDuration(e.target.value)}>
            <option value="">Выберите...</option>
            <option value="today">Сегодня</option>
            <option value="2-3days">2-3 дня</option>
            <option value="week">Неделю</option>
            <option value="month">Больше месяца</option>
          </select>
        </div>
        <button className="health-tools__calc-btn" onClick={check} disabled={selected.length === 0}>
          Проверить ({selected.length} симптомов)
        </button>
        {selected.length > 0 && (
          <button className="health-tools__reset-btn" onClick={() => { setSelected([]); setResult(null); }}>Сбросить</button>
        )}
      </div>
      {result && (
        <div className="health-tools__symptom-result" style={{'--urgency': URGENCY_COLORS[result.urgency]}}>
          <div className="health-tools__urgency-badge" style={{background: URGENCY_COLORS[result.urgency]}}>
            {URGENCY_LABELS[result.urgency]}
          </div>
          <div className="health-tools__specialists">
            <h4>Рекомендуемые специалисты:</h4>
            <div className="health-tools__specialist-list">
              {result.specialists.map((s, i) => <span key={i} className="health-tools__specialist-tag">{s}</span>)}
            </div>
          </div>
          <div className="health-tools__tips">
            <h4>Рекомендации:</h4>
            {result.tips.map((tip, i) => <p key={i} className="health-tools__tip">• {tip}</p>)}
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
const TOOLS = [
  { id: 'bmi', label: '⚖️ ИМТ', component: BMICalculator },
  { id: 'water', label: '💧 Вода', component: WaterTracker },
  { id: 'calories', label: '🔥 Калории', component: CalorieCalculator },
  { id: 'symptoms', label: '🔍 Симптомы', component: SymptomChecker },
];

const HealthTools = () => {
  const [activeTool, setActiveTool] = useState('bmi');
  const ActiveComponent = TOOLS.find(t => t.id === activeTool)?.component || BMICalculator;

  return (
    <div className="health-tools">
      <div className="health-tools__header">
        <h1 className="health-tools__title">🛠️ Инструменты здоровья</h1>
        <p className="health-tools__subtitle">Калькуляторы и помощники для контроля здоровья</p>
      </div>
      <div className="health-tools__tabs">
        {TOOLS.map(t => (
          <button
            key={t.id}
            className={`health-tools__tab ${activeTool === t.id ? 'health-tools__tab--active' : ''}`}
            onClick={() => setActiveTool(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <ActiveComponent />
    </div>
  );
};

export default HealthTools;