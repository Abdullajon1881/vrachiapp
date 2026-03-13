import React, { useState } from 'react';
import './DentalChart.scss';

// Universal numbering system (1-32 upper right→left, 17-32 lower left→right)
const UPPER_TEETH = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16];
const LOWER_TEETH = [32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17];

const TOOTH_NAMES = {
  1:'Верхний правый зуб мудрости', 2:'Верхний правый второй моляр', 3:'Верхний правый первый моляр',
  4:'Верхний правый второй премоляр', 5:'Верхний правый первый премоляр', 6:'Верхний правый клык',
  7:'Верхний правый боковой резец', 8:'Верхний правый центральный резец',
  9:'Верхний левый центральный резец', 10:'Верхний левый боковой резец', 11:'Верхний левый клык',
  12:'Верхний левый первый премоляр', 13:'Верхний левый второй премоляр', 14:'Верхний левый первый моляр',
  15:'Верхний левый второй моляр', 16:'Верхний левый зуб мудрости',
  17:'Нижний левый зуб мудрости', 18:'Нижний левый второй моляр', 19:'Нижний левый первый моляр',
  20:'Нижний левый второй премоляр', 21:'Нижний левый первый премоляр', 22:'Нижний левый клык',
  23:'Нижний левый боковой резец', 24:'Нижний левый центральный резец',
  25:'Нижний правый центральный резец', 26:'Нижний правый боковой резец', 27:'Нижний правый клык',
  28:'Нижний правый первый премоляр', 29:'Нижний правый второй премоляр', 30:'Нижний правый первый моляр',
  31:'Нижний правый второй моляр', 32:'Нижний правый зуб мудрости',
};

const CONDITIONS = [
  { id: 'healthy', label: 'Здоров', color: '#4caf50' },
  { id: 'caries', label: 'Кариес', color: '#ff9800' },
  { id: 'treated', label: 'Пролечен', color: '#2196f3' },
  { id: 'crown', label: 'Коронка', color: '#9c27b0' },
  { id: 'missing', label: 'Отсутствует', color: '#757575' },
  { id: 'implant', label: 'Имплант', color: '#00bcd4' },
  { id: 'extraction', label: 'К удалению', color: '#f44336' },
  { id: 'filling', label: 'Пломба', color: '#795548' },
];

const COND_COLOR = Object.fromEntries(CONDITIONS.map(c => [c.id, c.color]));

const getToothShape = (num) => {
  const incisors = [7,8,9,10,23,24,25,26];
  const canines = [6,11,22,27];
  const premolars = [4,5,12,13,20,21,28,29];
  if (incisors.includes(num)) return 'incisor';
  if (canines.includes(num)) return 'canine';
  if (premolars.includes(num)) return 'premolar';
  return 'molar';
};

const ToothSVG = ({ number, condition, isSelected, onClick }) => {
  const shape = getToothShape(number);
  const color = COND_COLOR[condition] || '#e8f5e9';
  const strokeColor = isSelected ? '#095880' : '#ccc';
  const strokeWidth = isSelected ? 2.5 : 1.5;

  const renderShape = () => {
    if (shape === 'incisor') {
      return (
        <>
          <rect x="4" y="3" width="16" height="20" rx="3" fill={color} stroke={strokeColor} strokeWidth={strokeWidth} />
          <rect x="7" y="6" width="10" height="2" rx="1" fill="white" opacity="0.5" />
        </>
      );
    }
    if (shape === 'canine') {
      return (
        <>
          <path d="M4 4 Q12 2 20 4 L22 18 Q12 26 2 18 Z" fill={color} stroke={strokeColor} strokeWidth={strokeWidth} />
          <ellipse cx="12" cy="8" rx="5" ry="2" fill="white" opacity="0.5" />
        </>
      );
    }
    if (shape === 'premolar') {
      return (
        <>
          <rect x="3" y="4" width="18" height="18" rx="4" fill={color} stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="12" y1="4" x2="12" y2="22" stroke="white" strokeWidth="1" opacity="0.4" />
        </>
      );
    }
    // molar
    return (
      <>
        <rect x="2" y="3" width="20" height="20" rx="5" fill={color} stroke={strokeColor} strokeWidth={strokeWidth} />
        <line x1="12" y1="3" x2="12" y2="23" stroke="white" strokeWidth="1" opacity="0.35" />
        <line x1="2" y1="13" x2="22" y2="13" stroke="white" strokeWidth="1" opacity="0.35" />
      </>
    );
  };

  return (
    <div
      className={`dental-chart__tooth ${isSelected ? 'dental-chart__tooth--selected' : ''} dental-chart__tooth--${shape}`}
      onClick={() => onClick(number)}
      title={`${number}. ${TOOTH_NAMES[number]}`}
    >
      <svg viewBox="0 0 24 26" fill="none" xmlns="http://www.w3.org/2000/svg">
        {renderShape()}
      </svg>
      <span className="dental-chart__tooth-num">{number}</span>
    </div>
  );
};

const DentalChart = () => {
  const [teethConditions, setTeethConditions] = useState({});
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState({});
  const [activeCondition, setActiveCondition] = useState('caries');
  const [view, setView] = useState('chart');

  const handleToothClick = (num) => {
    if (selected === num) {
      setSelected(null);
    } else {
      setSelected(num);
    }
  };

  const applyCondition = () => {
    if (!selected) return;
    setTeethConditions(prev => ({ ...prev, [selected]: activeCondition }));
  };

  const clearCondition = () => {
    if (!selected) return;
    setTeethConditions(prev => {
      const updated = { ...prev };
      delete updated[selected];
      return updated;
    });
  };

  const resetAll = () => {
    if (window.confirm('Сбросить все отметки?')) {
      setTeethConditions({});
      setNotes({});
      setSelected(null);
    }
  };

  const stats = CONDITIONS.map(c => ({
    ...c,
    count: Object.values(teethConditions).filter(v => v === c.id).length,
  })).filter(c => c.count > 0);

  const problemTeeth = Object.entries(teethConditions)
    .filter(([, v]) => !['healthy', 'treated'].includes(v))
    .map(([k, v]) => ({ num: parseInt(k), condition: v }));

  return (
    <div className="dental-chart">
      <div className="dental-chart__header">
        <div>
          <h1 className="dental-chart__title">🦷 Зубная карта</h1>
          <p className="dental-chart__subtitle">Интерактивная схема зубов — отмечайте состояние каждого зуба</p>
        </div>
        <div className="dental-chart__header-actions">
          <button className={`dental-chart__view-btn ${view === 'chart' ? 'dental-chart__view-btn--active' : ''}`} onClick={() => setView('chart')}>📊 Карта</button>
          <button className={`dental-chart__view-btn ${view === 'report' ? 'dental-chart__view-btn--active' : ''}`} onClick={() => setView('report')}>📋 Отчёт</button>
        </div>
      </div>

      {view === 'chart' ? (
        <div className="dental-chart__content">
          {/* Condition picker */}
          <div className="dental-chart__legend">
            {CONDITIONS.map(c => (
              <button
                key={c.id}
                className={`dental-chart__legend-item ${activeCondition === c.id ? 'dental-chart__legend-item--active' : ''}`}
                onClick={() => setActiveCondition(c.id)}
                style={{ '--cond-color': c.color }}
              >
                <span className="dental-chart__legend-dot" style={{ background: c.color }} />
                {c.label}
              </button>
            ))}
          </div>

          {/* Chart */}
          <div className="dental-chart__diagram">
            <div className="dental-chart__jaw-label">Верхняя челюсть (права → лева)</div>
            <div className="dental-chart__row">
              {UPPER_TEETH.map(num => (
                <ToothSVG
                  key={num}
                  number={num}
                  condition={teethConditions[num]}
                  isSelected={selected === num}
                  onClick={handleToothClick}
                />
              ))}
            </div>
            <div className="dental-chart__divider" />
            <div className="dental-chart__row">
              {LOWER_TEETH.map(num => (
                <ToothSVG
                  key={num}
                  number={num}
                  condition={teethConditions[num]}
                  isSelected={selected === num}
                  onClick={handleToothClick}
                />
              ))}
            </div>
            <div className="dental-chart__jaw-label">Нижняя челюсть (лева → права)</div>
          </div>

          {/* Selected tooth panel */}
          {selected ? (
            <div className="dental-chart__panel">
              <div className="dental-chart__panel-header">
                <h3>Зуб #{selected}</h3>
                <span className="dental-chart__panel-name">{TOOTH_NAMES[selected]}</span>
              </div>
              <div className="dental-chart__panel-current">
                Текущее состояние:&nbsp;
                <strong style={{ color: COND_COLOR[teethConditions[selected]] || '#4caf50' }}>
                  {CONDITIONS.find(c => c.id === (teethConditions[selected] || 'healthy'))?.label}
                </strong>
              </div>
              <div className="dental-chart__panel-actions">
                <button className="dental-chart__apply-btn" onClick={applyCondition}>
                  Применить: {CONDITIONS.find(c => c.id === activeCondition)?.label}
                </button>
                <button className="dental-chart__clear-btn" onClick={clearCondition}>
                  Сбросить
                </button>
              </div>
              <div className="dental-chart__panel-notes">
                <label>Заметка:</label>
                <textarea
                  value={notes[selected] || ''}
                  onChange={(e) => setNotes(prev => ({ ...prev, [selected]: e.target.value }))}
                  placeholder="Добавьте заметку к этому зубу..."
                  rows={2}
                />
              </div>
            </div>
          ) : (
            <div className="dental-chart__hint">
              👆 Нажмите на зуб, чтобы отметить его состояние
            </div>
          )}

          {/* Summary stats */}
          {stats.length > 0 && (
            <div className="dental-chart__stats">
              <h3>Сводка</h3>
              <div className="dental-chart__stats-grid">
                {stats.map(s => (
                  <div key={s.id} className="dental-chart__stat-item" style={{ '--c': s.color }}>
                    <span className="dental-chart__stat-count">{s.count}</span>
                    <span className="dental-chart__stat-label">{s.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="dental-chart__footer">
            <button className="dental-chart__reset-btn" onClick={resetAll}>🔄 Сбросить всё</button>
          </div>
        </div>
      ) : (
        /* Report view */
        <div className="dental-chart__report">
          <h2>Отчёт по зубной карте</h2>
          {Object.keys(teethConditions).length === 0 ? (
            <div className="dental-chart__report-empty">
              <p>Нет отмеченных зубов. Вернитесь к карте и отметьте состояние зубов.</p>
              <button className="dental-chart__apply-btn" onClick={() => setView('chart')}>Перейти к карте</button>
            </div>
          ) : (
            <>
              <div className="dental-chart__report-stats">
                {stats.map(s => (
                  <div key={s.id} className="dental-chart__report-stat">
                    <div className="dental-chart__report-stat-dot" style={{ background: s.color }} />
                    <span>{s.label}: <strong>{s.count}</strong></span>
                  </div>
                ))}
              </div>
              {problemTeeth.length > 0 && (
                <>
                  <h3>⚠️ Проблемные зубы</h3>
                  <div className="dental-chart__report-list">
                    {problemTeeth.map(({ num, condition }) => (
                      <div key={num} className="dental-chart__report-item">
                        <span className="dental-chart__report-num">#{num}</span>
                        <span className="dental-chart__report-tooth-name">{TOOTH_NAMES[num]}</span>
                        <span
                          className="dental-chart__report-cond"
                          style={{ background: COND_COLOR[condition] + '22', color: COND_COLOR[condition] }}
                        >
                          {CONDITIONS.find(c => c.id === condition)?.label}
                        </span>
                        {notes[num] && <span className="dental-chart__report-note">💬 {notes[num]}</span>}
                      </div>
                    ))}
                  </div>
                </>
              )}
              <p className="dental-chart__report-tip">
                💡 Показывайте эту карту своему стоматологу для более точной консультации
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default DentalChart;
