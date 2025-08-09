// Helper translations for domain data coming from backend in Russian

const specializationMap = {
  'Терапевт': { en: 'Therapist', uz: 'Terapevt' },
  'Кардиолог': { en: 'Cardiologist', uz: 'Kardiolog' },
  'Невролог': { en: 'Neurologist', uz: 'Nevrolog' },
  'Офтальмолог': { en: 'Ophthalmologist', uz: 'Oftalmolog' },
  'Дерматолог': { en: 'Dermatologist', uz: 'Dermatolog' },
  'Ортопед': { en: 'Orthopedist', uz: 'Ortoped' },
  'Ревматолог': { en: 'Rheumatologist', uz: 'Revmatolog' },
  'Педиатр': { en: 'Pediatrician', uz: 'Pediatr' },
  'Гинеколог': { en: 'Gynecologist', uz: 'Ginekolog' },
  'Уролог': { en: 'Urologist', uz: 'Urolog' },
  'Эндокринолог': { en: 'Endocrinologist', uz: 'Endokrinolog' },
  'Психиатр': { en: 'Psychiatrist', uz: 'Psixiatr' },
  'Хирург': { en: 'Surgeon', uz: 'Jarroh' },
  'Стоматолог': { en: 'Dentist', uz: 'Stomatolog' },
  'Онколог': { en: 'Oncologist', uz: 'Onkolog' },
  'Аллерголог': { en: 'Allergist', uz: 'Allergolog' },
  'Иммунолог': { en: 'Immunologist', uz: 'Immunolog' },
  'Гастроэнтеролог': { en: 'Gastroenterologist', uz: 'Gastroenterolog' },
  'Пульмонолог': { en: 'Pulmonologist', uz: 'Pulmonolog' },
  'Нефролог': { en: 'Nephrologist', uz: 'Nefrolog' },
  'Гематолог': { en: 'Hematologist', uz: 'Gematolog' },
  'Инфекционист': { en: 'Infectious disease specialist', uz: 'Infeksionist' },
  'Травматолог': { en: 'Traumatologist', uz: 'Travmatolog' },
  'Анестезиолог': { en: 'Anesthesiologist', uz: 'Anesteziolog' },
  'Реаниматолог': { en: 'Intensivist', uz: 'Reanimatolog' },
  'Физиотерапевт': { en: 'Physiotherapist', uz: 'Fizioterapevt' },
  'Массажист': { en: 'Masseur', uz: 'Massajchi' },
  'Психолог': { en: 'Psychologist', uz: 'Psixolog' },
  'Диетолог': { en: 'Dietitian', uz: 'Diyetolog' },
  'Спортивный врач': { en: 'Sports physician', uz: 'Sport shifokori' },
  'Гериатр': { en: 'Geriatrician', uz: 'Geriatr' },
  'Другое': { en: 'Other', uz: 'Boshqa' }
};

const locationMap = {
  // Regions
  'Ташкентская область': { en: 'Tashkent Region', uz: 'Toshkent viloyati' },
  'Город Ташкент': { en: 'Tashkent City', uz: 'Toshkent shahri' },
  'Самаркандская область': { en: 'Samarkand Region', uz: 'Samarqand viloyati' },
  'Город Самарканд': { en: 'Samarkand City', uz: 'Samarqand shahri' },
  'Бухарская область': { en: 'Bukhara Region', uz: 'Buxoro viloyati' },
  'Город Бухара': { en: 'Bukhara City', uz: 'Buxoro shahri' },
  'Ферганская область': { en: 'Fergana Region', uz: 'Fargʻona viloyati' },
  'Андижанская область': { en: 'Andijan Region', uz: 'Andijon viloyati' },
  'Наманганская область': { en: 'Namangan Region', uz: 'Namangan viloyati' },
  'Кашкадарьинская область': { en: 'Kashkadarya Region', uz: 'Qashqadaryo viloyati' },
  'Сурхандарьинская область': { en: 'Surxondaryo Region', uz: 'Surxondaryo viloyati' },
  'Сырдарьинская область': { en: 'Sirdarya Region', uz: 'Sirdaryo viloyati' },
  'Джизакская область': { en: 'Jizzakh Region', uz: 'Jizzax viloyati' },
  'Навоийская область': { en: 'Navoi Region', uz: 'Navoiy viloyati' },
  'Хорезмская область': { en: 'Khorezm Region', uz: 'Xorazm viloyati' },
  'Республика Каракалпакстан': { en: 'Karakalpakstan Republic', uz: 'Qoraqalpogʻiston Respublikasi' },

  // Major cities
  'Ташкент': { en: 'Tashkent', uz: 'Toshkent' },
  'Самарканд': { en: 'Samarkand', uz: 'Samarqand' },
  'Бухара': { en: 'Bukhara', uz: 'Buxoro' },
  'Фергана': { en: 'Fergana', uz: 'Fargʻona' },
  'Андижан': { en: 'Andijan', uz: 'Andijon' },
  'Наманган': { en: 'Namangan', uz: 'Namangan' },
  'Навои': { en: 'Navoi', uz: 'Navoiy' },
  'Джизак': { en: 'Jizzakh', uz: 'Jizzax' },
  'Гулистан': { en: 'Gulistan', uz: 'Guliston' },
  'Ургенч': { en: 'Urgench', uz: 'Urganch' },
  'Нукус': { en: 'Nukus', uz: 'Nukus' },
  'Карши': { en: 'Karshi', uz: 'Qarshi' },
  'Термез': { en: 'Termez', uz: 'Termiz' },

  // Tashkent districts (examples)
  'Яшнабадский район': { en: 'Yashnabad district', uz: 'Yashnobod tumani' },
  'Чилонзарский район': { en: 'Chilanzar district', uz: 'Chilonzor tumani' },
  'Мирзо-Улугбекский район': { en: 'Mirzo Ulugbek district', uz: 'Mirzo Ulugʻbek tumani' },
  'Шайхантахурский район': { en: 'Shaykhantakhur district', uz: 'Shayxontohur tumani' },
  'Сергелийский район': { en: 'Sergeli district', uz: 'Sergeli tumani' },
  'Юнусабадский район': { en: 'Yunusabad district', uz: 'Yunusobod tumani' },
  'Алмазарский район': { en: 'Almazar district', uz: 'Olmazor tumani' },
  'Учтепинский район': { en: 'Uchtepa district', uz: 'Uchtepa tumani' },
  'Бектемирский район': { en: 'Bektemir district', uz: 'Bektemir tumani' }
};

export function translateSpec(specialization, lng) {
  if (!specialization || !lng) return specialization;
  const lang = (lng || 'ru').slice(0, 2);
  if (lang === 'ru') return specialization;
  const mapped = specializationMap[specialization];
  return mapped?.[lang] || specialization;
}

export function translateLocation(name, lng) {
  if (!name || !lng) return name;
  const lang = (lng || 'ru').slice(0, 2);
  if (lang === 'ru') return name;
  const mapped = locationMap[name];
  if (mapped?.[lang]) return mapped[lang];

  // Heuristic fallback for unknown names
  let result = name;
  if (lang === 'en') {
    // City
    if (/^Город\s+/i.test(result)) {
      result = result.replace(/^Город\s+/i, '');
      result = `${result} City`;
    }
    // Region
    result = result.replace(/\s*область$/i, ' Region');
    // District
    result = result.replace(/\s*район$/i, ' district');
  } else if (lang === 'uz') {
    if (/^Город\s+/i.test(result)) {
      result = result.replace(/^Город\s+/i, '');
      result = `${result} shahri`;
    }
    result = result.replace(/\s*область$/i, ' viloyati');
    result = result.replace(/\s*район$/i, ' tumani');
  }
  return result;
}


