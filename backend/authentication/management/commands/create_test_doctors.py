from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.models import User, UserProfile


DOCTORS = [
    {
        "email": "karimov.doctor@healzy.com",
        "first_name": "Алишер",
        "last_name": "Каримов",
        "specialization": "Кардиолог",
        "experience": "10 лет опыта в кардиологии. Специалист по лечению ишемической болезни сердца, гипертонии и сердечной недостаточности.",
        "region": "Город Ташкент",
        "city": "Ташкент",
        "languages": ["Русский", "Узбекский"],
        "consultation_price": 150000,
    },
    {
        "email": "nazarova.doctor@healzy.com",
        "first_name": "Малика",
        "last_name": "Назарова",
        "specialization": "Невролог",
        "experience": "8 лет опыта в неврологии. Лечение мигрени, эпилепсии, инсульта и заболеваний периферической нервной системы.",
        "region": "Город Ташкент",
        "city": "Ташкент",
        "languages": ["Русский", "Узбекский", "Английский"],
        "consultation_price": 120000,
    },
    {
        "email": "rakhimov.doctor@healzy.com",
        "first_name": "Бобур",
        "last_name": "Рахимов",
        "specialization": "Терапевт",
        "experience": "15 лет опыта в терапии. Диагностика и лечение широкого спектра заболеваний внутренних органов.",
        "region": "Самаркандская область",
        "city": "Самарканд",
        "languages": ["Русский", "Узбекский"],
        "consultation_price": 80000,
    },
    {
        "email": "umarova.doctor@healzy.com",
        "first_name": "Дилноза",
        "last_name": "Умарова",
        "specialization": "Педиатр",
        "experience": "12 лет опыта в педиатрии. Лечение детских заболеваний, вакцинация, мониторинг развития ребёнка.",
        "region": "Город Ташкент",
        "city": "Ташкент",
        "languages": ["Русский", "Узбекский"],
        "consultation_price": 100000,
    },
    {
        "email": "yusupov.doctor@healzy.com",
        "first_name": "Санжар",
        "last_name": "Юсупов",
        "specialization": "Дерматолог",
        "experience": "7 лет опыта в дерматологии. Лечение акне, экземы, псориаза и других кожных заболеваний.",
        "region": "Ферганская область",
        "city": "Фергана",
        "languages": ["Русский", "Узбекский"],
        "consultation_price": 90000,
    },
    {
        "email": "toshmatova.doctor@healzy.com",
        "first_name": "Феруза",
        "last_name": "Тошматова",
        "specialization": "Гинеколог",
        "experience": "9 лет опыта в гинекологии. Ведение беременности, лечение гинекологических заболеваний.",
        "region": "Город Ташкент",
        "city": "Ташкент",
        "languages": ["Русский", "Узбекский", "Английский"],
        "consultation_price": 130000,
    },
    {
        "email": "mirzaev.doctor@healzy.com",
        "first_name": "Жасур",
        "last_name": "Мирзаев",
        "specialization": "Ортопед",
        "experience": "11 лет опыта в ортопедии. Лечение травм, артрита, остеохондроза и заболеваний опорно-двигательного аппарата.",
        "region": "Бухарская область",
        "city": "Бухара",
        "languages": ["Русский", "Узбекский"],
        "consultation_price": 110000,
    },
    {
        "email": "xasanov.doctor@healzy.com",
        "first_name": "Отабек",
        "last_name": "Хасанов",
        "specialization": "Психолог",
        "experience": "6 лет опыта в психологии. Когнитивно-поведенческая терапия, работа с тревогой, депрессией и стрессом.",
        "region": "Город Ташкент",
        "city": "Ташкент",
        "languages": ["Русский", "Узбекский", "Английский"],
        "consultation_price": 100000,
    },
]


class Command(BaseCommand):
    help = 'Create test doctor accounts for development'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        created = 0
        skipped = 0

        for doc in DOCTORS:
            email = doc['email']
            if User.objects.filter(email=email).exists():
                self.stdout.write(f'  Skipped (exists): {email}')
                skipped += 1
                continue

            user = User.objects.create_user(
                email=email,
                password='Doctor1234!',
                first_name=doc['first_name'],
                last_name=doc['last_name'],
                role='doctor',
                is_active=True,
            )

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.specialization = doc['specialization']
            profile.experience = doc['experience']
            profile.region = doc['region']
            profile.city = doc['city']
            profile.languages = doc['languages']
            profile.consultation_price = doc['consultation_price']
            profile.is_available = True
            profile.save()

            self.stdout.write(self.style.SUCCESS(f'  Created: Dr. {user.full_name} ({doc["specialization"]})'))
            created += 1

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created: {created}, Skipped: {skipped}'))
        self.stdout.write('Login password for all doctors: Doctor1234!')