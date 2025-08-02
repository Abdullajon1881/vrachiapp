from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import requests
import json
from django.db import models
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse

from .models import User, UserProfile, Region, City, District, DoctorApplication
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, 
    GoogleAuthSerializer, PasswordResetSerializer, UserProfileSerializer, UserProfileReadSerializer,
    RegionSerializer, CitySerializer, DistrictSerializer,
    DoctorApplicationSerializer, DoctorApplicationCreateSerializer, DoctorApplicationUpdateSerializer
)
from .utils import create_user_with_verification, send_verification_email, verify_email_token, create_google_user


class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя с email верификацией"""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # Логируем данные для отладки
        print(f"Registration data: {request.data}")
        
        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем данные из сериализатора
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')
        username = serializer.validated_data.get('username', '')
        role = serializer.validated_data.get('role', 'patient')
        
        # Если username не указан, используем email
        if not username:
            username = email.split('@')[0]
        
        # Создаем пользователя с верификацией
        user = create_user_with_verification(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        
        # Если был указан username, обновляем его
        if username and username != user.username:
            # Проверяем уникальность
            if not User.objects.filter(username=username).exists():
                user.username = username
                user.save()
        
        # Создаем профиль пользователя
        UserProfile.objects.create(user=user)
        
        # Отправляем email для верификации
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': user.email_verification_token})
        )
        
        email_sent = send_verification_email(user, verification_url)
        
        if email_sent:
            return Response({
                'message': 'Регистрация успешна! Проверьте ваш email для подтверждения аккаунта.',
                'email': email,
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        else:
            # Если email не отправлен, удаляем пользователя
            user.delete()
            return Response({
                'error': 'Ошибка отправки email для подтверждения. Попробуйте позже.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(generics.GenericAPIView):
    """Вход пользователя"""
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Проверяем, подтвержден ли email (только для не-Google пользователей)
        # Если пользователь был создан до системы верификации, считаем его верифицированным
        if not user.google_id and not user.is_verified:
            # Проверяем, есть ли токен верификации (если нет, значит пользователь старый)
            if not user.email_verification_token:
                # Старый пользователь - автоматически верифицируем
                user.is_verified = True
                user.is_active = True
                user.save()
                print(f"Автоматически верифицирован старый пользователь: {user.email}")
            else:
                # Новый пользователь с токеном - требует подтверждения
                return Response({
                    'error': 'Пожалуйста, подтвердите ваш email перед входом в систему. Проверьте вашу почту или запросите повторную отправку.',
                    'needs_verification': True,
                    'email': user.email
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, активен ли пользователь
        if not user.is_active:
            return Response({
                'error': 'Ваш аккаунт неактивен. Обратитесь к администратору.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Входим в систему
        login(request, user)
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Успешный вход'
        })


class LogoutView(generics.GenericAPIView):
    """Выход пользователя"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response({'message': 'Успешный выход'})





class UserProfileView(generics.RetrieveUpdateAPIView):
    """Профиль пользователя"""
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthView(generics.GenericAPIView):
    """Google OAuth аутентификация"""
    permission_classes = (AllowAny,)
    serializer_class = GoogleAuthSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_token = serializer.validated_data['access_token']
        
        # Получаем информацию о пользователе от Google
        google_user_info = self.get_google_user_info(access_token)
        
        if not google_user_info:
            return Response(
                {'error': 'Не удалось получить информацию от Google'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем или получаем пользователя
        user = self.get_or_create_google_user(google_user_info)
        
        # Входим в систему
        login(request, user)
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Успешная аутентификация через Google'
        })

    def get_google_user_info(self, access_token):
        """Получает информацию о пользователе от Google"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка при получении данных от Google: {e}")
        return None

    def get_or_create_google_user(self, google_user_info):
        """Создает или получает пользователя по Google ID"""
        google_id = google_user_info.get('id')
        email = google_user_info.get('email')
        first_name = google_user_info.get('given_name', '')
        last_name = google_user_info.get('family_name', '')
        avatar = google_user_info.get('picture', '')
        
        # Создаем или получаем пользователя через утилиту
        user = create_google_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            google_id=google_id,
            avatar=avatar
        )
        
        # Создаем профиль, если его нет
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
        
        return user


class PasswordResetView(generics.GenericAPIView):
    """Сброс пароля"""
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            # Здесь будет отправка email для сброса пароля
            return Response({
                'message': 'Инструкции по сбросу пароля отправлены на email'
            })
        except User.DoesNotExist:
            return Response({
                'message': 'Инструкции по сбросу пароля отправлены на email'
            })


@api_view(['GET'])
@permission_classes([AllowAny])
def check_auth(request):
    """Проверка аутентификации"""
    return Response({
        'user': UserSerializer(request.user).data if request.user.is_authenticated else None,
        'is_authenticated': request.user.is_authenticated,
        'session_id': request.session.session_key,
        'user_id': request.session.get('_auth_user_id')
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Получение CSRF токена"""
    from django.middleware.csrf import get_token
    return Response({'csrfToken': get_token(request)})


@api_view(['GET'])
@permission_classes([AllowAny])
def list_users(request):
    """Список всех пользователей (только для разработки)"""
    users = User.objects.all()
    return Response({
        'users': UserSerializer(users, many=True).data,
        'count': users.count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_regions(request):
    """Получение списка регионов"""
    regions = Region.objects.all()
    return Response(RegionSerializer(regions, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    """Получение списка городов по региону"""
    region_id = request.GET.get('region_id')
    if region_id:
        cities = City.objects.filter(region_id=region_id)
    else:
        cities = City.objects.all()
    return Response(CitySerializer(cities, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_districts(request):
    """Получение списка районов по региону"""
    region_id = request.GET.get('region_id')
    if region_id:
        districts = District.objects.filter(region_id=region_id)
    else:
        districts = District.objects.all()
    return Response(DistrictSerializer(districts, many=True).data)

@api_view(['POST'])
@permission_classes([AllowAny])
def detect_location(request):
    """Определение местоположения по координатам"""
    
    import requests
    
    try:
        lat = float(request.data.get('latitude'))
        lng = float(request.data.get('longitude'))
        

        
        # Функции для извлечения адресов из разных API
        def extract_nominatim_address(data):
            """Извлекает детальный адрес из Nominatim API"""
            address = data.get('address', {})
            display_name = data.get('display_name', '')
            
            # Пытаемся собрать детальный адрес
            parts = []
            
            # Улица
            if address.get('road'):
                parts.append(f"ул. {address['road']}")
            
            # Номер дома
            if address.get('house_number'):
                parts.append(address['house_number'])
            
            # Район/микрорайон
            if address.get('suburb'):
                parts.append(address['suburb'])
            
            # Город
            if address.get('city'):
                parts.append(address['city'])
            elif address.get('town'):
                parts.append(address['town'])
            
            # Если собрали детальный адрес
            if parts:
                return ", ".join(parts)
            
            # Если нет деталей, используем display_name но убираем дублирование
            if display_name:
                # Убираем дублирование "Ташкент, Ташкент"
                parts = display_name.split(', ')
                unique_parts = []
                for part in parts:
                    if part not in unique_parts:
                        unique_parts.append(part)
                return ', '.join(unique_parts)
            
            return display_name
        
        def extract_bigdatacloud_address(data):
            """Извлекает детальный адрес из BigDataCloud API"""
            parts = []
            
            # Улица
            if data.get('street'):
                parts.append(f"ул. {data['street']}")
            
            # Номер дома
            if data.get('houseNumber'):
                parts.append(data['houseNumber'])
            
            # Район
            if data.get('locality'):
                parts.append(data['locality'])
            
            # Город
            if data.get('city'):
                parts.append(data['city'])
            
            # Область
            if data.get('principalSubdivision'):
                parts.append(data['principalSubdivision'])
            
            if parts:
                return ", ".join(parts)
            
            # Fallback
            return f"{data.get('locality', '')}, {data.get('city', '')}, {data.get('countryName', '')}".strip(', ')
        
        def extract_locationiq_address(data):
            """Извлекает детальный адрес из LocationIQ API"""
            address = data.get('address', {})
            display_name = data.get('display_name', '')
            
            parts = []
            
            # Улица
            if address.get('road'):
                parts.append(f"ул. {address['road']}")
            
            # Номер дома
            if address.get('house_number'):
                parts.append(address['house_number'])
            
            # Район
            if address.get('suburb'):
                parts.append(address['suburb'])
            
            # Город
            if address.get('city'):
                parts.append(address['city'])
            
            if parts:
                return ", ".join(parts)
            
            return display_name
        
        # Пытаемся получить реальный адрес через геокодирование
        real_address = None
        try:
            # Используем несколько надежных API для геокодирования
            apis_to_try = [
                # OpenStreetMap Nominatim с более точными параметрами
                {
                    'url': f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=16&addressdetails=1&accept-language=ru",
                    'extract': lambda data: extract_nominatim_address(data)
                },
                # BigDataCloud API с дополнительными параметрами
                {
                    'url': f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lng}&localityLanguage=ru",
                    'extract': lambda data: extract_bigdatacloud_address(data)
                }
            ]
            
            for api_config in apis_to_try:
                try:
                    response = requests.get(api_config['url'], timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        real_address = api_config['extract'](data)
                        
                        if real_address and len(real_address) > 10:  # Проверяем что адрес достаточно детальный
                            break
                except Exception as e:
                    continue
            
            # Если ни один API не сработал, используем координаты
            if not real_address or len(real_address) <= 10:
                real_address = f"Координаты: {lat:.6f}, {lng:.6f}"
                
        except Exception as e:
            real_address = f"Координаты: {lat:.6f}, {lng:.6f}"
        
        # Проверяем что координаты в пределах Узбекистана
        if not (37.0 <= lat <= 45.0 and 56.0 <= lng <= 73.0):
            return Response({
                'success': False,
                'message': 'Координаты находятся за пределами Узбекистана'
            }, status=400)
        
        # Определяем регион по координатам через геокодирование
        region_name = None
        
        # Пытаемся определить регион из полученного адреса
        if real_address and "Ташкент" in real_address:
            region_name = "Город Ташкент"
        elif real_address and "Самарканд" in real_address:
            region_name = "Город Самарканд"
        elif real_address and "Бухара" in real_address:
            region_name = "Город Бухара"
        elif real_address and "Андижан" in real_address:
            region_name = "Город Андижан"
        elif real_address and "Наманган" in real_address:
            region_name = "Город Наманган"
        elif real_address and "Фергана" in real_address:
            region_name = "Город Фергана"
        elif real_address and "Карши" in real_address:
            region_name = "Город Карши"
        elif real_address and "Нукус" in real_address:
            region_name = "Город Нукус"
        elif real_address and "Термез" in real_address:
            region_name = "Город Термез"
        elif real_address and "Ургенч" in real_address:
            region_name = "Город Ургенч"
        elif real_address and "Навои" in real_address:
            region_name = "Город Навои"
        elif real_address and "Джизак" in real_address:
            region_name = "Город Джизак"
        elif real_address and "Гулистан" in real_address:
            region_name = "Город Гулистан"
        else:
            # Если не удалось определить по адресу, используем координаты
            if 41.0 <= lat <= 42.0 and 69.0 <= lng <= 70.0:
                region_name = "Ташкентская область"
            elif 39.0 <= lat <= 40.0 and 66.0 <= lng <= 68.0:
                region_name = "Самаркандская область"
            elif 39.0 <= lat <= 40.0 and 64.0 <= lng <= 66.0:
                region_name = "Бухарская область"
            elif 40.0 <= lat <= 41.0 and 71.0 <= lng <= 73.0:
                region_name = "Ферганская область"
            elif 40.5 <= lat <= 41.5 and 71.0 <= lng <= 72.5:
                region_name = "Андижанская область"
            elif 40.5 <= lat <= 41.5 and 71.0 <= lng <= 72.0:
                region_name = "Наманганская область"
            elif 38.0 <= lat <= 39.0 and 65.0 <= lng <= 67.0:
                region_name = "Кашкадарьинская область"
            elif 37.0 <= lat <= 38.0 and 67.0 <= lng <= 68.0:
                region_name = "Сурхандарьинская область"
            elif 40.0 <= lat <= 41.0 and 68.0 <= lng <= 69.0:
                region_name = "Сырдарьинская область"
            elif 40.0 <= lat <= 41.0 and 67.0 <= lng <= 69.0:
                region_name = "Джизакская область"
            elif 40.0 <= lat <= 41.0 and 65.0 <= lng <= 66.0:
                region_name = "Навоийская область"
            elif 41.0 <= lat <= 42.0 and 60.0 <= lng <= 62.0:
                region_name = "Хорезмская область"
            elif 42.0 <= lat <= 44.0 and 58.0 <= lng <= 61.0:
                region_name = "Республика Каракалпакстан"
            else:
                region_name = "Ташкентская область"  # По умолчанию
        
        region = Region.objects.filter(name=region_name).first()
        
        if region:
            # Определяем только регион, остальные поля пользователь заполнит вручную
            message = f'Определен регион: {region.name}'
            
            return Response({
                'success': True,
                'region': RegionSerializer(region).data,
                'message': message
            })
        else:
            return Response({
                'success': False,
                'message': 'Регион не найден в базе данных'
            }, status=400)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Ошибка при определении местоположения: {str(e)}'
        }, status=500)


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def user_profile(request):
    """Профиль пользователя"""
    if not request.user.is_authenticated:
        return Response({
            'error': 'Пользователь не аутентифицирован',
            'is_authenticated': False,
            'session_id': request.session.session_key,
            'user_id': request.session.get('_auth_user_id')
        }, status=401)
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        print(f"Получаем профиль для пользователя {request.user.email}")
        print(f"Роль пользователя: {request.user.role}")
        print(f"Имя пользователя: first_name='{request.user.first_name}', last_name='{request.user.last_name}'")
        
        data = UserProfileReadSerializer(profile).data
        print(f"Данные профиля: specialization={data.get('specialization')}, experience={data.get('experience')}")
        print(f"Имя в данных: first_name='{data.get('first_name')}', last_name='{data.get('last_name')}'")
        
        return Response(data)
    
    elif request.method == 'PUT':
        if not request.user.is_authenticated:
            return Response({
                'error': 'Пользователь не аутентифицирован',
                'is_authenticated': False
            }, status=401)
        
        # Проверяем, что врач не может редактировать свой профиль
        if request.user.role == 'doctor':
            return Response({
                'error': 'Врачи не могут редактировать свой профиль. Обратитесь к администратору.'
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Обновляем данные пользователя
        user_data = {}
        if 'first_name' in request.data:
            user_data['first_name'] = request.data['first_name']
        if 'last_name' in request.data:
            user_data['last_name'] = request.data['last_name']
        
        if user_data:
            for field, value in user_data.items():
                setattr(request.user, field, value)
            request.user.save()
        
        # Обновляем данные профиля
        profile_data = {k: v for k, v in request.data.items() 
                       if k not in ['first_name', 'last_name', 'email', 'username']}
        
        # Преобразуем названия полей для сериализатора
        if 'region' in profile_data:
            profile_data['region_id'] = profile_data.pop('region')
        if 'city' in profile_data:
            profile_data['city_id'] = profile_data.pop('city')
        if 'district' in profile_data:
            profile_data['district_id'] = profile_data.pop('district')
        
        serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Профиль успешно обновлен!',
                'data': UserProfileReadSerializer(profile).data
            })
        else:
            return Response(serializer.errors, status=400) 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_doctor_application(request):
    """Подача заявки на роль врача"""
    print(f"=== ПОДАЧА ЗАЯВКИ ВРАЧА ===")
    print(f"Пользователь: {request.user.email}")
    print(f"Данные запроса: {request.data}")
    print(f"Файлы: {request.FILES}")
    print(f"Тип данных: {type(request.data)}")
    
    serializer = DoctorApplicationCreateSerializer(data=request.data)
    print(f"Сериализатор создан")
    
    if serializer.is_valid():
        print("Сериализатор валиден")
        print(f"Валидные данные: {serializer.validated_data}")
        # Привязываем заявку к текущему пользователю
        application = serializer.save(user=request.user)
        print(f"Заявка создана с ID: {application.id}")
        
        # Возвращаем полную информацию о заявке
        full_serializer = DoctorApplicationSerializer(application)
        return Response({
            'message': 'Заявка успешно отправлена! Мы рассмотрим её в течение 1-3 рабочих дней.',
            'application': full_serializer.data
        }, status=status.HTTP_201_CREATED)
    else:
        print(f"Ошибки валидации: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_applications(request):
    """Получение списка заявок (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    
    status_filter = request.query_params.get('status', None)
    
    queryset = DoctorApplication.objects.all()
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    serializer = DoctorApplicationSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_application_detail(request, application_id):
    """Получение детальной информации о заявке (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        application = DoctorApplication.objects.get(id=application_id)
        serializer = DoctorApplicationSerializer(application)
        return Response(serializer.data)
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_doctor_application(request, application_id):
    """Обновление статуса заявки на роль врача (одобрение/отклонение)"""
    try:
        application = DoctorApplication.objects.get(id=application_id)
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = DoctorApplicationUpdateSerializer(application, data=request.data, partial=True)
    if serializer.is_valid():
        # Обновляем заявку
        application = serializer.save(
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        
        # Если заявка одобрена, обновляем профиль пользователя
        if application.status == 'approved':
            print(f"=== ОДОБРЕНИЕ ЗАЯВКИ ===")
            user = application.user
            print(f"Пользователь: {user.email}")
            print(f"Текущее имя: first_name='{user.first_name}', last_name='{user.last_name}'")
            
            user.role = 'doctor'
            
            # Копируем имя из заявки
            if application.first_name:
                user.first_name = application.first_name
                print(f"Установлено first_name: '{user.first_name}'")
            
            if application.last_name:
                user.last_name = application.last_name
                print(f"Установлено last_name: '{user.last_name}'")
            
            user.save()
            print(f"Сохранено в базе: first_name='{user.first_name}', last_name='{user.last_name}'")
            
            # Проверяем, что сохранилось
            user.refresh_from_db()
            print(f"После refresh: first_name='{user.first_name}', last_name='{user.last_name}'")
            
            # Обновляем или создаем профиль пользователя
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            print(f"Одобряем заявку для пользователя {user.email}")
            print(f"Данные из заявки: specialization={application.specialization}, experience={application.experience}")
            print(f"Имя из заявки: first_name='{application.first_name}', last_name='{application.last_name}'")
            
            # Копируем все поля из заявки в профиль
            profile.specialization = application.specialization
            profile.experience = application.experience
            profile.education = application.education
            profile.license_number = application.license_number
            profile.languages = application.languages
            profile.additional_info = application.additional_info
            
            # Копируем поля профиля
            if application.date_of_birth:
                profile.date_of_birth = application.date_of_birth
            if application.gender:
                profile.gender = application.gender
            if application.phone:
                profile.phone = application.phone
            if application.address:
                profile.address = application.address
            if application.medical_info:
                profile.medical_info = application.medical_info
            if application.emergency_contact:
                profile.emergency_contact = application.emergency_contact
            
            profile.save()
            
            print(f"Профиль сохранен: specialization={profile.specialization}, experience={profile.experience}")
            print(f"Имя пользователя: {user.first_name} {user.last_name}")
        
        # Возвращаем обновленную заявку
        full_serializer = DoctorApplicationSerializer(application)
        return Response({
            'message': f'Заявка успешно {application.get_status_display().lower()}!',
            'application': full_serializer.data
        }, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_applications(request):
    """Получение заявок текущего пользователя"""
    applications = DoctorApplication.objects.filter(user=request.user)
    serializer = DoctorApplicationSerializer(applications, many=True)
    return Response(serializer.data) 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user_data(request):
    """Получение актуальных данных текущего пользователя"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    print(f"Получаем данные пользователя: {user.email}")
    print(f"Имя в базе: first_name='{user.first_name}', last_name='{user.last_name}'")
    print(f"Данные профиля: specialization='{profile.specialization}', experience='{profile.experience}'")
    
    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'full_name': user.full_name,
        'initials': user.initials,
        'avatar': user.avatar,
        # Данные профиля
        'profile': {
            'phone': profile.phone,
            'date_of_birth': profile.date_of_birth,
            'gender': profile.gender,
            'region': profile.region,
            'city': profile.city,
            'district': profile.district,
            'address': profile.address,
            'medical_info': profile.medical_info,
            'emergency_contact': profile.emergency_contact,
            'specialization': profile.specialization,
            'experience': profile.experience,
            'education': profile.education,
            'license_number': profile.license_number,
            'languages': profile.languages,
            'additional_info': profile.additional_info
        }
    }
    
    print(f"Отправляем данные: {user_data}")
    return Response(user_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctors(request):
    """Получение списка всех врачей (только для пациентов)"""
    if request.user.role != 'patient':
        return Response({'error': 'Доступ запрещен. Только пациенты могут просматривать список врачей'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Получаем только пользователей с ролью 'doctor'
        doctors = User.objects.filter(role='doctor').prefetch_related('profile')
        
        # Сериализуем данные врачей
        doctors_data = []
        for doctor in doctors:
            profile = getattr(doctor, 'profile', None)
            doctor_data = {
                'id': doctor.id,
                'first_name': doctor.first_name,
                'last_name': doctor.last_name,
                'email': doctor.email,
                'avatar': doctor.avatar,
                'full_name': doctor.full_name,
                'initials': doctor.initials,
                'specialization': profile.specialization if profile else '',
                'experience': profile.experience if profile else '',
                'education': profile.education if profile else '',
                'license_number': profile.license_number if profile else '',
                'languages': profile.languages if profile else [],
                'additional_info': profile.additional_info if profile else '',
                'region': profile.region.name if profile and profile.region else '',
                'city': profile.city.name if profile and profile.city else '',
                'district': profile.district.name if profile and profile.district else '',
                'address': profile.address if profile else '',
                'phone': profile.phone if profile else '',
                'created_at': doctor.created_at,
            }
            doctors_data.append(doctor_data)
        
        return Response(doctors_data)
    except Exception as e:
        print(f"Ошибка при получении врачей: {e}")
        return Response({'error': 'Ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_profile(request, doctor_id):
    """Получение профиля конкретного врача (только для пациентов)"""
    if request.user.role != 'patient':
        return Response({'error': 'Доступ запрещен. Только пациенты могут просматривать профили врачей'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        doctor = User.objects.get(id=doctor_id, role='doctor')
        profile, created = UserProfile.objects.get_or_create(user=doctor)
        
        doctor_data = {
            'id': doctor.id,
            'first_name': doctor.first_name,
            'last_name': doctor.last_name,
            'email': doctor.email,
            'avatar': doctor.avatar,
            'full_name': doctor.full_name,
            'initials': doctor.initials,
            'specialization': profile.specialization or '',
            'experience': profile.experience or '',
            'education': profile.education or '',
            'license_number': profile.license_number or '',
            'languages': profile.languages or [],
            'additional_info': profile.additional_info or '',
            'region': profile.region.name if profile.region else '',
            'city': profile.city.name if profile.city else '',
            'district': profile.district.name if profile.district else '',
            'address': profile.address or '',
            'phone': profile.phone or '',
            'created_at': doctor.created_at,
            'reviews': []  # Пока пустой массив для отзывов
        }
        
        return Response(doctor_data)
    except User.DoesNotExist:
        return Response({'error': 'Врач не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Ошибка при получении профиля врача: {e}")
        return Response({'error': 'Ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    """Получение списка всех пользователей (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        users = User.objects.all().prefetch_related('profile')
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        return Response({'error': 'Ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def manage_user_profile(request, user_id):
    """Управление профилем пользователя (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        profile, created = UserProfile.objects.get_or_create(user=user)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Обновляем данные пользователя (включая роль)
        user_data = {}
        if 'first_name' in request.data:
            user_data['first_name'] = request.data['first_name']
        if 'last_name' in request.data:
            user_data['last_name'] = request.data['last_name']
        if 'role' in request.data:
            user_data['role'] = request.data['role']
        
        # Обновляем пользователя
        if user_data:
            for field, value in user_data.items():
                setattr(user, field, value)
            user.save()
            print(f"Обновлен пользователь {user.email}: {user_data}")
        
        # Обновляем профиль
        profile_data = {k: v for k, v in request.data.items() 
                       if k not in ['first_name', 'last_name', 'email', 'username', 'role']}
        
        # Преобразуем названия полей для сериализатора
        if 'region' in profile_data:
            profile_data['region_id'] = profile_data.pop('region')
        if 'city' in profile_data:
            profile_data['city_id'] = profile_data.pop('city')
        if 'district' in profile_data:
            profile_data['district_id'] = profile_data.pop('district')
        
        serializer = UserProfileSerializer(profile, data=profile_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Профиль пользователя успешно обновлен!',
                'profile': UserProfileSerializer(profile).data
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_doctor_name_from_application(request, application_id):
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    """Принудительное обновление имени врача из заявки (только для админов)"""
    try:
        application = DoctorApplication.objects.get(id=application_id)
        
        if application.status != 'approved':
            return Response({'error': 'Заявка не одобрена'}, status=400)
        
        user = application.user
        print(f"=== ОБНОВЛЕНИЕ ИМЕНИ ВРАЧА ===")
        print(f"Пользователь: {user.email}")
        print(f"Текущее имя: first_name='{user.first_name}', last_name='{user.last_name}'")
        print(f"Имя из заявки: first_name='{application.first_name}', last_name='{application.last_name}'")
        
        # Копируем имя из заявки
        if application.first_name:
            user.first_name = application.first_name
            print(f"Установлено first_name: '{user.first_name}'")
        
        if application.last_name:
            user.last_name = application.last_name
            print(f"Установлено last_name: '{user.last_name}'")
        
        user.save()
        print(f"Сохранено в базе: first_name='{user.first_name}', last_name='{user.last_name}'")
        
        # Проверяем, что сохранилось
        user.refresh_from_db()
        print(f"После refresh: first_name='{user.first_name}', last_name='{user.last_name}'")
        
        return Response({
            'message': 'Имя врача успешно обновлено из заявки!',
            'new_name': f"{user.first_name} {user.last_name}".strip()
        })
            
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=404) 

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора'}, status=status.HTTP_403_FORBIDDEN)
    """Удаление пользователя (только для админов)"""
    try:
        user = User.objects.get(id=user_id)
        
        # Проверяем, что админ не удаляет сам себя
        if user.id == request.user.id:
            return Response({'error': 'Нельзя удалить свой собственный аккаунт'}, status=400)
        
        # Проверяем, что не удаляем суперпользователя
        if user.is_superuser:
            return Response({'error': 'Нельзя удалить суперпользователя'}, status=400)
        
        print(f"Удаляем пользователя: {user.email} (ID: {user.id})")
        
        # Удаляем пользователя (это также удалит связанные профили и заявки)
        user.delete()
        
        return Response({
            'message': f'Пользователь {user.email} успешно удален!'
        })
        
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=404) 

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_view(request, token):
    """Верификация email по токену"""
    success, message = verify_email_token(token)
    
    if success:
        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': message
        }, status=status.HTTP_400_BAD_REQUEST)


def verify_email_html_view(request, token):
    """HTML страница для подтверждения email"""
    success, message = verify_email_token(token)
    
    context = {
        'success': success,
        'error_message': message if not success else None
    }
    
    return render(request, 'authentication/email_verification_success.html', context)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """Повторная отправка email для верификации"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email, is_verified=False)
        
        # Генерируем новый токен
        from .utils import generate_verification_token
        user.email_verification_token = generate_verification_token()
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        # Отправляем email
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': user.email_verification_token})
        )
        
        # Заменяем API URL на HTML URL для email
        html_verification_url = verification_url.replace('/api/auth/verify-email/', '/api/auth/verify-email-html/')
        
        email_sent = send_verification_email(user, html_verification_url)
        
        if email_sent:
            return Response({
                'message': 'Email для подтверждения отправлен повторно'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Ошибка отправки email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь с таким email не найден или уже подтвержден'
        }, status=status.HTTP_404_NOT_FOUND) 

 