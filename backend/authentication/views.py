from rest_framework import status, generics
import uuid
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
import requests
import json
from django.db import models
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponse
from django.http import FileResponse, Http404
from django.views.decorators.http import require_http_methods
from asgiref.sync import sync_to_async
import asyncio
from .ai_service import ai_service
import html
from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import User, UserProfile, Region, City, District, DoctorApplication, Consultation, Message, UserProfile
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, 
    GoogleAuthSerializer, PasswordResetSerializer, UserProfileSerializer, UserProfileReadSerializer,
    RegionSerializer, CitySerializer, DistrictSerializer,
    DoctorApplicationSerializer, DoctorApplicationCreateSerializer, DoctorApplicationUpdateSerializer,
    ConsultationSerializer, ConsultationCreateSerializer, ConsultationUpdateSerializer, MessageSerializer
)
from .utils import create_user_with_verification, send_verification_email, verify_email_token, create_google_user


class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя с email верификацией"""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
                
        if not serializer.is_valid():
            # Не логируем чувствительные ошибки со входными данными
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
            return Response({'error': 'Ошибка отправки email для подтверждения. Попробуйте позже.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(generics.GenericAPIView):
    """Вход пользователя"""
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data['user']
        login(request, user)
        
        # Получаем данные пользователя
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'Вход выполнен успешно',
            'user': user_data
        })


class LogoutView(generics.GenericAPIView):
    """Выход пользователя"""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        logout(request)
        return Response({'message': 'Выход выполнен успешно'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Профиль пользователя"""
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthView(generics.GenericAPIView):
    """Google OAuth аутентификация"""
    permission_classes = (AllowAny,)
    authentication_classes = ()  # отключаем SessionAuthentication/CSRF для этого эндпоинта
    serializer_class = GoogleAuthSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        access_token = serializer.validated_data['access_token']
        
        try:
            # Получаем информацию о пользователе от Google
            google_user_info = self.get_google_user_info(access_token)
            
            if not google_user_info:
                return Response({
                    'error': 'Не удалось получить информацию о пользователе от Google'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Создаем или получаем пользователя
            user = self.get_or_create_google_user(google_user_info)
            
            if not user.is_active:
                return Response({
                    'error': 'Аккаунт не активирован'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Входим в систему
            login(request, user)
            
            # Получаем данные пользователя
            user_data = UserSerializer(user).data
            
            return Response({
                'message': 'Вход через Google выполнен успешно',
                'user': user_data
            })
            
        except Exception:
            return Response({
                'error': 'Ошибка аутентификации через Google'
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_google_user_info(self, access_token):
        """Получает информацию о пользователе от Google"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None

    def get_or_create_google_user(self, google_user_info):
        """Создает или получает пользователя на основе Google данных"""
        email = google_user_info.get('email')
        google_id = google_user_info.get('id')
        
        if not email:
            raise ValueError("Email не найден в данных Google")
        
        # Пытаемся найти пользователя по email или google_id
        user = None
        
        if google_id:
            try:
                user = User.objects.get(google_id=google_id)
            except User.DoesNotExist:
                pass
        
        if not user:
            try:
                user = User.objects.get(email=email)
                # Если пользователь найден по email, но у него нет google_id, добавляем его
                if not user.google_id and google_id:
                    user.google_id = google_id
                    user.save()
            except User.DoesNotExist:
                # Создаем нового пользователя
                user = create_google_user(google_user_info)
        
        return user


class PasswordResetView(generics.GenericAPIView):
    """Сброс пароля"""
    permission_classes = (AllowAny,)
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            # Здесь должна быть логика отправки email для сброса пароля
            return Response({
                'message': 'Инструкции по сбросу пароля отправлены на ваш email'
            })
        except User.DoesNotExist:
            return Response({
                'message': 'Если пользователь с таким email существует, инструкции по сбросу пароля отправлены'
            })


@api_view(['GET'])
@permission_classes([AllowAny])
def check_auth(request):
    """Проверка аутентификации"""
    if request.user.is_authenticated:
        user_data = UserSerializer(request.user).data
        return Response({
            'authenticated': True,
            'user': user_data
        })
    else:
        return Response({
            'authenticated': False,
            'user': None
        })


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """Выдаёт CSRF токен и гарантированно устанавливает csrftoken cookie"""
    from django.middleware.csrf import get_token
    token = get_token(request)
    resp = Response({'csrfToken': token})
    # Явно выставляем cookie, чтобы избежать проблем на некоторых клиентах/браузерах
    resp.set_cookie(
        key='csrftoken',
        value=token,
        secure=True,
        httponly=False,
        samesite='Lax'
    )
    return resp


@api_view(['GET'])
@permission_classes([AllowAny])
def list_users(request):
    """Список пользователей (только для отладки)"""
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_regions(request):
    """Получение списка регионов"""
    regions = Region.objects.all()
    serializer = RegionSerializer(regions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    """Получение списка городов"""
    region_id = request.GET.get('region_id')
    if region_id:
        cities = City.objects.filter(region_id=region_id)
    else:
        cities = City.objects.all()
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_districts(request):
    """Получение списка районов"""
    region_id = request.GET.get('region_id')
    city_id = request.GET.get('city_id')
    
    districts = District.objects.all()
    
    if region_id:
        districts = districts.filter(region_id=region_id)
    
    if city_id:
        districts = districts.filter(city_id=city_id)
    
    serializer = DistrictSerializer(districts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def detect_location(request):
    """Определение местоположения по IP"""
    
    # Локальные хелперы (объявлены до использования)
    def extract_nominatim_address(data):
        try:
            country = data.get('country', '')
            region = data.get('regionName', '')
            city = data.get('city', '')
            # Ищем регион в базе данных
            region_obj = None
            if region:
                try:
                    region_obj = Region.objects.filter(name__icontains=region).first()
                except:
                    pass
            # Ищем город в базе данных
            city_obj = None
            if city and region_obj:
                try:
                    city_obj = City.objects.filter(
                        name__icontains=city,
                        region=region_obj
                    ).first()
                except:
                    pass
            return {
                'country': country,
                'region': region,
                'city': city,
                'region_id': region_obj.id if region_obj else None,
                'city_id': city_obj.id if city_obj else None,
                'ip': data.get('query', '')
            }
        except Exception:
            return None

    def extract_bigdatacloud_address(data):
        try:
            location = data.get('location', {})
            country = location.get('country', {}).get('name', '')
            region = location.get('region', {}).get('name', '')
            city = location.get('city', {}).get('name', '')
            # Ищем регион в базе данных
            region_obj = None
            if region:
                try:
                    region_obj = Region.objects.filter(name__icontains=region).first()
                except:
                    pass
            # Ищем город в базе данных
            city_obj = None
            if city and region_obj:
                try:
                    city_obj = City.objects.filter(
                        name__icontains=city,
                        region=region_obj
                    ).first()
                except:
                    pass
            return {
                'country': country,
                'region': region,
                'city': city,
                'region_id': region_obj.id if region_obj else None,
                'city_id': city_obj.id if city_obj else None,
                'ip': data.get('ip', '')
            }
        except Exception:
            return None

    def extract_locationiq_address(data):
        try:
            country = data.get('country', '')
            region = data.get('region', '')
            city = data.get('city', '')
            # Ищем регион в базе данных
            region_obj = None
            if region:
                try:
                    region_obj = Region.objects.filter(name__icontains=region).first()
                except:
                    pass
            # Ищем город в базе данных
            city_obj = None
            if city and region_obj:
                try:
                    city_obj = City.objects.filter(
                        name__icontains=city,
                        region=region_obj
                    ).first()
                except:
                    pass
            return {
                'country': country,
                'region': region,
                'city': city,
                'region_id': region_obj.id if region_obj else None,
                'city_id': city_obj.id if city_obj else None,
                'ip': data.get('ip', '')
            }
        except Exception:
            return None
    try:
        # Получаем IP адрес
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Используем несколько сервисов для определения местоположения
        location_data = None
        
        # Попытка 1: Nominatim (OpenStreetMap)
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location_data = extract_nominatim_address(data)
        except:
            pass
        
        # Попытка 2: BigDataCloud
        if not location_data:
            try:
                response = requests.get(f'https://api.bigdatacloud.net/data/ip-geolocation?ip={ip}&key=free', timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    location_data = extract_bigdatacloud_address(data)
            except:
                pass
        
        # Попытка 3: LocationIQ (если есть API ключ)
        if not location_data:
            try:
                # Здесь можно добавить LocationIQ API ключ
                # response = requests.get(f'https://us1.locationiq.com/v1/ip.php?key=YOUR_API_KEY&ip={ip}', timeout=5)
                # if response.status_code == 200:
                #     data = response.json()
                #     location_data = self.extract_locationiq_address(data)
                pass
            except:
                pass
        
        if location_data:
            return Response(location_data)
        else:
            return Response({'error': 'Не удалось определить местоположение'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception:
        return Response({'error': 'Ошибка определения местоположения'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # (локальные хелперы перенесены наверх функции)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Профиль пользователя"""
    if request.method == 'GET':
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                serializer = UserProfileReadSerializer(profile)
                return Response(serializer.data)
            except UserProfile.DoesNotExist:
                return Response({
                    'error': 'Профиль не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'Пользователь не авторизован'}, status=status.HTTP_401_UNAUTHORIZED)
    
    elif request.method == 'PUT':
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
                
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except UserProfile.DoesNotExist:
                return Response({
                    'error': 'Профиль не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({
                'error': 'Пользователь не авторизован'
            }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_doctor_application(request):
    """Подача заявки на роль врача"""
    
    serializer = DoctorApplicationCreateSerializer(data=request.data)
    # сериализатор создан
    
    if serializer.is_valid():
        # сериализатор валиден
        # Привязываем заявку к текущему пользователю
        application = serializer.save(user=request.user)
        # заявка создана
        
        # Возвращаем полную информацию о заявке
        full_serializer = DoctorApplicationSerializer(application)
        return Response({
            'message': 'Заявка успешно отправлена! Мы рассмотрим её в течение 1-3 рабочих дней.',
            'application': full_serializer.data
        }, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_applications(request):
    """Получение списка заявок (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора.'}, status=status.HTTP_403_FORBIDDEN)
    
    applications = DoctorApplication.objects.all()
    serializer = DoctorApplicationSerializer(applications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_application_detail(request, application_id):
    """Получение детальной информации о заявке"""
    try:
        application = DoctorApplication.objects.get(id=application_id)
        serializer = DoctorApplicationSerializer(application)
        return Response(serializer.data)
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_doctor_application(request, application_id):
    """Обновление заявки (только для админов)"""
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора.'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        application = DoctorApplication.objects.get(id=application_id)
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = DoctorApplicationUpdateSerializer(application, data=request.data, partial=True)
    if serializer.is_valid():
        # Если заявка одобрена, обновляем профиль пользователя
        if serializer.validated_data.get('status') == 'approved':
            user = application.user
            user.role = 'doctor'
            
            # Обновляем имя пользователя из заявки
            if application.first_name:
                user.first_name = application.first_name
            
            if application.last_name:
                user.last_name = application.last_name
            
            user.save()
            
            # Проверяем, что сохранилось
            user.refresh_from_db()
            
            # Обновляем или создаем профиль пользователя
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # убраны избыточные логи с персональными данными
            
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
            
            # Копируем адресные данные
            if application.region:
                profile.region = application.region
            if application.city:
                profile.city = application.city
            if application.district:
                profile.district = application.district
            
            profile.save()
        
        # Обновляем заявку
        serializer.save(reviewed_by=request.user, reviewed_at=timezone.now())
        
        # Возвращаем обновленную заявку
        full_serializer = DoctorApplicationSerializer(application)
        return Response({
            'message': 'Заявка успешно обновлена',
            'application': full_serializer.data
        })
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
    """Получение данных текущего пользователя"""
    user_data = UserSerializer(request.user).data
    
    # Добавляем информацию о профиле
    try:
        profile = UserProfile.objects.get(user=request.user)
        profile_data = UserProfileReadSerializer(profile).data
        user_data['profile'] = profile_data
    except UserProfile.DoesNotExist:
        user_data['profile'] = None
    
    # Добавляем информацию о заявках (если есть)
    if request.user.role == 'patient':
        applications = DoctorApplication.objects.filter(user=request.user)
        applications_data = DoctorApplicationSerializer(applications, many=True).data
        user_data['applications'] = applications_data
    else:
        user_data['applications'] = []
    
    return Response(user_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctors(request):
    """Получение списка врачей"""
    # Получаем всех пользователей с ролью врача
    doctors = User.objects.filter(role='doctor', is_active=True)
    
    # Фильтры
    specialization = request.GET.get('specialization')
    region_id = request.GET.get('region_id')
    city_id = request.GET.get('city_id')
    search = request.GET.get('search')
    
    if specialization:
        doctors = doctors.filter(profile__specialization__icontains=specialization)
    
    if region_id:
        doctors = doctors.filter(profile__region_id=region_id)
    
    if city_id:
        doctors = doctors.filter(profile__city_id=city_id)
    
    if search:
        doctors = doctors.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(profile__specialization__icontains=search)
        )
    
    # Получаем данные профилей
    doctors_data = []
    for doctor in doctors:
        try:
            profile = UserProfile.objects.get(user=doctor)
            doctor_data = {
                'id': doctor.id,
                'email': doctor.email,
                'first_name': doctor.first_name,
                'last_name': doctor.last_name,
                'full_name': doctor.full_name,
                'initials': doctor.initials,
                'avatar': doctor.avatar,
                'specialization': profile.specialization,
                'experience': profile.experience,
                'education': profile.education,
                'license_number': profile.license_number,
                'languages': profile.languages,
                'additional_info': profile.additional_info,
                'region': profile.region.name if profile.region else None,
                'city': profile.city.name if profile.city else None,
                'district': profile.district.name if profile.district else None,
                'phone': profile.phone,
                'address': profile.address,
            }
            doctors_data.append(doctor_data)
        except UserProfile.DoesNotExist:
            continue
    
    return Response(doctors_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctor_profile(request, doctor_id):
    """Получение профиля врача"""
    try:
        doctor = User.objects.get(id=doctor_id, role='doctor', is_active=True)
        profile = UserProfile.objects.get(user=doctor)
        
        doctor_data = {
            'id': doctor.id,
            'email': doctor.email,
            'first_name': doctor.first_name,
            'last_name': doctor.last_name,
            'full_name': doctor.full_name,
            'initials': doctor.initials,
            'avatar': doctor.avatar,
            'specialization': profile.specialization,
            'experience': profile.experience,
            'education': profile.education,
            'license_number': profile.license_number,
            'languages': profile.languages,
            'additional_info': profile.additional_info,
            'region': profile.region.name if profile.region else None,
            'city': profile.city.name if profile.city else None,
            'district': profile.district.name if profile.district else None,
            'phone': profile.phone,
            'address': profile.address,
        }
        
        return Response(doctor_data)
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return Response({'error': 'Врач не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):
    """Получение всех пользователей (только для админов)"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def manage_user_profile(request, user_id):
    """Управление профилем пользователя (только для админов)"""
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        try:
            profile = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Профиль не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    elif request.method == 'PUT':
        try:
            profile = UserProfile.objects.get(user=user)
            serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'Профиль не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_doctor_name_from_application(request, application_id):
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора.'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        application = DoctorApplication.objects.get(id=application_id)
    except DoctorApplication.DoesNotExist:
        return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)
    
    user = application.user
    
    # Обновляем имя пользователя из заявки
    if application.first_name:
        user.first_name = application.first_name
    
    if application.last_name:
        user.last_name = application.last_name
    
    user.save()
    
    # Проверяем, что сохранилось
    user.refresh_from_db()
    
    return Response({
        'message': 'Имя пользователя обновлено',
        'user': UserSerializer(user).data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request, user_id):
    # Проверяем, что пользователь является администратором
    if not (request.user.is_staff or request.user.is_superuser or request.user.role == 'admin'):
        return Response({'error': 'Доступ запрещен. Требуются права администратора.'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    # Не позволяем удалять самого себя
    if user == request.user:
        return Response({'error': 'Нельзя удалить самого себя'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Удаляем пользователя
    user.delete()
    
    return Response({'message': 'Пользователь успешно удален'})


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_view(request, token):
    """Верификация email по токену"""
    try:
        user = verify_email_token(token)
        if user:
            return Response({
                'message': 'Email успешно подтвержден! Теперь вы можете войти в систему.',
                'user_id': user.id
            })
        else:
            return Response({
                'error': 'Недействительный или истекший токен верификации'
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Ошибка верификации email'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def verify_email_html_view(request, token):
    """HTML страница для верификации email"""
    try:
        user = verify_email_token(token)
        if user:
            # Успех: передаем флаг success в шаблон успеха
            return render(request, 'authentication/email_verification_success.html', {
                'success': True,
                'user': user,
            })
        else:
            # Неуспех: показываем страницу успеха, но с блоком ошибки
            return render(request, 'authentication/email_verification_success.html', {
                'success': False,
                'error_message': 'Недействительный или истекший токен верификации'
            })
    except Exception:
        return render(request, 'authentication/email_verification_success.html', {
            'success': False,
            'error_message': 'Ошибка верификации email'
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """Повторная отправка email для верификации"""
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email обязателен'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        if user.is_verified:
            return Response({'error': 'Email уже подтвержден'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаем новый токен верификации
        user.email_verification_token = uuid.uuid4()
        user.email_verification_sent_at = timezone.now()
        user.save()
        
        # Отправляем email
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': user.email_verification_token})
        )
        
        email_sent = send_verification_email(user, verification_url)
        
        if email_sent:
            return Response({
                'message': 'Email для подтверждения отправлен повторно. Проверьте вашу почту.'
            })
        else:
            return Response({
                'error': 'Ошибка отправки email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except User.DoesNotExist:
        return Response({
            'error': 'Пользователь с таким email не найден'
        }, status=status.HTTP_404_NOT_FOUND)


# Views для консультаций и чатов
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_consultations(request):
    """Получение списка консультаций пользователя"""
    user = request.user
    
    if user.role == 'patient':
        consultations = Consultation.objects.filter(patient=user)
    elif user.role == 'doctor':
        consultations = Consultation.objects.filter(doctor=user)
    else:
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = ConsultationSerializer(consultations, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_consultation(request):
    """Создание новой консультации"""
    serializer = ConsultationCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        consultation = serializer.save()
        full_serializer = ConsultationSerializer(consultation)
        return Response({
            'message': 'Консультация успешно создана',
            'consultation': full_serializer.data
        }, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_consultation_detail(request, consultation_id):
    """Получение детальной информации о консультации"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем доступ
        if request.user not in [consultation.patient, consultation.doctor]:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ConsultationSerializer(consultation)
        return Response(serializer.data)
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_consultation(request, consultation_id):
    """Обновление консультации"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем доступ
        if request.user not in [consultation.patient, consultation.doctor]:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ConsultationUpdateSerializer(consultation, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            full_serializer = ConsultationSerializer(consultation)
            return Response({
                'message': 'Консультация успешно обновлена',
                'consultation': full_serializer.data
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_messages(request, consultation_id):
    """Получение сообщений консультации"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем доступ
        if request.user not in [consultation.patient, consultation.doctor]:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        messages = consultation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, consultation_id):
    """Отправка сообщения в консультацию"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем доступ
        if request.user not in [consultation.patient, consultation.doctor]:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем, может ли пользователь писать
        if request.user == consultation.patient and not consultation.can_patient_write:
            return Response({'error': 'Нельзя писать в завершенной консультации'}, status=status.HTTP_400_BAD_REQUEST)
        elif request.user == consultation.doctor and not consultation.can_doctor_write:
            return Response({'error': 'Нельзя писать в завершенной консультации'}, status=status.HTTP_400_BAD_REQUEST)
        
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Содержание сообщения обязательно'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = Message.objects.create(
            consultation=consultation,
            sender=request.user,
            content=content
        )
        
        serializer = MessageSerializer(message)
        return Response({
            'message': 'Сообщение отправлено',
            'message_data': serializer.data
        }, status=status.HTTP_201_CREATED)
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_consultation(request, consultation_id):
    """Принятие консультации врачом"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем, что пользователь является врачом этой консультации
        if request.user != consultation.doctor:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем, что консультация в статусе ожидания
        if consultation.status != 'pending':
            return Response({'error': 'Консультация уже не в статусе ожидания'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Принимаем консультацию
        consultation.status = 'active'
        consultation.started_at = timezone.now()
        consultation.save()
        
        serializer = ConsultationSerializer(consultation)
        return Response({
            'message': 'Консультация успешно принята',
            'consultation': serializer.data
        })
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_consultation(request, consultation_id):
    """Завершение консультации врачом"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
        
        # Проверяем, что пользователь является врачом этой консультации
        if request.user != consultation.doctor:
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем, что консультация активна
        if consultation.status != 'active':
            return Response({'error': 'Консультация не активна'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Завершаем консультацию
        consultation.status = 'completed'
        consultation.completed_at = timezone.now()
        consultation.save()
        
        serializer = ConsultationSerializer(consultation)
        return Response({
            'message': 'Консультация успешно завершена',
            'consultation': serializer.data
        })
    except Consultation.DoesNotExist:
        return Response({'error': 'Консультация не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_diagnosis(request):
    """API для работы с AI диагностикой с поддержкой голосового общения"""
    try:
        user = request.user
        
        # Проверяем тип запроса
        if 'file' in request.FILES:
            # Обработка файла (изображение, видео, аудио)
            file = request.FILES['file']
            file_type = request.data.get('type', 'image')
            # Базовая валидация контента
            max_size = getattr(settings, 'FILE_UPLOAD_MAX_SIZE', 10 * 1024 * 1024)
            if file.size > max_size:
                return Response({'error': 'Файл слишком большой'}, status=status.HTTP_400_BAD_REQUEST)
            allowed = []
            if file_type == 'image':
                allowed = getattr(settings, 'ALLOWED_IMAGE_MIME_TYPES', ['image/jpeg', 'image/png', 'image/gif'])
            elif file_type == 'audio':
                allowed = getattr(settings, 'ALLOWED_AUDIO_MIME_TYPES', ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/ogg'])
            elif file_type == 'pdf':
                allowed = ['application/pdf']
            elif file_type == 'video':
                allowed = getattr(settings, 'ALLOWED_VIDEO_MIME_TYPES', ['video/mp4', 'video/webm'])
            
            if allowed and getattr(file, 'content_type', '') not in allowed:
                return Response({'error': 'Неподдерживаемый тип файла'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Используем обновленный сервис
            if allowed and getattr(file, 'content_type', '') not in allowed:
                return Response({'error': 'Неподдерживаемый тип файла'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Обработка по типу файла
            if file_type == 'image':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_image_message(user, file))
                finally:
                    loop.close()

            elif file_type == 'audio':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_audio_message(user, file))
                finally:
                    loop.close()

            elif file_type == 'pdf':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_pdf_message(user, file))
                finally:
                    loop.close()

            elif file_type == 'video':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_image_message(user, file))
                finally:
                    loop.close()
            else:
                return Response({'error': 'Неподдерживаемый тип файла'}, status=status.HTTP_400_BAD_REQUEST)
                
            if result['success']:
                # Сохраняем пользовательское сообщение
                user_message = ai_service.save_dialogue_message(
                    user=user,
                    content=result.get('transcription', f"Файл загружен: {file.name}"),
                    sender_type='user',
                    message_type=file_type,
                    audio_file=file.read() if file_type == 'audio' else None
                )
                
                # Сохраняем ответ AI с аудиофайлом если есть
                ai_message = ai_service.save_dialogue_message(
                    user=user,
                    content=result['response'],
                    sender_type='ai',
                    message_type='voice_response' if result.get('has_voice') else 'text',
                    audio_file=result.get('audio_content')
                )
                
                # Формируем ответ
                response_data = {
                    'response': result['response'],
                    'type': result['type'],
                    'has_voice': result.get('has_voice', False)
                }
                
                # Добавляем URL аудиофайла если есть
                if result.get('has_voice') and ai_message.audio_file:
                    response_data['audio_url'] = request.build_absolute_uri(ai_message.audio_file.url)
                
                # Добавляем расшифровку для аудио
                if result.get('transcription'):
                    response_data['transcription'] = result['transcription']
                
                return Response(response_data)
            else:
                return Response({
                    'error': result.get('error', 'Ошибка обработки файла')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        elif 'message' in request.data:
            # Обработка текстового сообщения
            message = request.data['message']
            
            if not message or not message.strip():
                return Response({
                    'error': 'Сообщение не может быть пустым'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Асинхронная обработка текста с возможностью голосового ответа
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(ai_service.process_text_message(user, message))
            finally:
                loop.close()
                
            if result['success']:
                # Сохраняем пользовательское сообщение
                ai_service.save_dialogue_message(
                    user=user,
                    content=message,
                    sender_type='user',
                    message_type='text'
                )
                
                # Сохраняем ответ AI с аудиофайлом если есть
                ai_message = ai_service.save_dialogue_message(
                    user=user,
                    content=result['response'],
                    sender_type='ai',
                    message_type='voice_response' if result.get('has_voice') else 'text',
                    audio_file=result.get('audio_content')
                )
                
                # Формируем ответ
                response_data = {
                    'response': result['response'],
                    'type': result['type'],
                    'has_voice': result.get('has_voice', False)
                }
                
                # Добавляем URL аудиофайла если есть
                if result.get('has_voice') and ai_message.audio_file:
                    response_data['audio_url'] = request.build_absolute_uri(ai_message.audio_file.url)
                
                return Response(response_data)
            else:
                return Response({
                    'error': result.get('error', 'Ошибка обработки сообщения')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': 'Не указано сообщение или файл'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"Error in ai_diagnosis: {e}")
        return Response({
            'error': 'Произошла внутренняя ошибка сервера'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_dialogue_history(request):
    """Получение истории диалогов с AI"""
    try:
        user = request.user
        
        # Получаем активный диалог пользователя
        from .models import AIDialogue
        
        try:
            dialogue = AIDialogue.objects.get(user=user, is_active=True)
            messages = dialogue.messages.all()
            
            messages_data = []
            for msg in messages:
                messages_data.append({
                    'id': msg.id,
                    'sender_type': msg.sender_type,
                    'message_type': msg.message_type,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                })
            
            return Response({
                'dialogue_id': dialogue.id,
                'messages': messages_data
            })
            
        except AIDialogue.DoesNotExist:
            # Если диалога нет, возвращаем пустой список
            return Response({
                'dialogue_id': None,
                'messages': []
            })
            
    except Exception:
        return Response({'error': 'Ошибка получения истории диалогов'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_support_message(request):
    """Получает сообщение поддержки от авторизованного пользователя и пересылает в Telegram группу"""
    try:
        user = request.user
        message_text = request.data.get('message', '').strip()
        if not message_text:
            return Response({'error': 'Сообщение не может быть пустым'}, status=status.HTTP_400_BAD_REQUEST)

        # Собираем информацию о пользователе
        profile_data = {}
        try:
            profile = UserProfile.objects.get(user=user)
            profile_data = {
                'specialization': getattr(profile, 'specialization', None),
                'phone': getattr(profile, 'phone', None),
                'region': getattr(profile.region, 'name', None) if getattr(profile, 'region', None) else None,
                'city': getattr(profile.city, 'name', None) if getattr(profile, 'city', None) else None,
            }
        except UserProfile.DoesNotExist:
            pass

        # Подготовка текста для Telegram (экранируем спецсимволы)
        def esc(s):
            return html.escape(str(s or ''))

        tg_lines = [
            f"🆘 Новое обращение в поддержку",
            f"👤 Пользователь: {esc(user.full_name)} (ID: {user.id})",
            f"📧 Email: {esc(user.email)}",
            f"📱 Phone: {esc(profile_data.get('phone'))}",
            f"🌍 Регион: {esc(profile_data.get('region'))}, Город: {esc(profile_data.get('city'))}",
            f"🔖 Роль: {esc(user.role)}",
            "",
            f"✉️ Сообщение:\n{esc(message_text)}",
        ]

        tg_text = "\n".join(tg_lines)

        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'TELEGRAM_SUPPORT_CHAT_ID', '')
        if not bot_token or not chat_id:
            return Response({'error': 'Не настроены параметры Telegram'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Отправляем в Telegram
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    'chat_id': chat_id,
                    'text': tg_text,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True,
                },
                timeout=5
            )
        except Exception:
            return Response({'error': 'Ошибка отправки в Telegram'}, status=status.HTTP_502_BAD_GATEWAY)

        if resp.status_code != 200:
            return Response({'error': 'Не удалось отправить сообщение в Telegram'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'message': 'Сообщение отправлено в поддержку'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'error': 'Внутренняя ошибка'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_media(request, subpath):
    """Выдаёт файл из MEDIA только админам; остальным 403. Путь указывается относительно MEDIA_ROOT."""
    user = request.user
    if not (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'admin'):
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

    # Нормализуем путь, не даём выходить выше MEDIA_ROOT
    from django.conf import settings as dj_settings
    import os
    safe_subpath = os.path.normpath(subpath).lstrip('/\\')
    abs_path = os.path.join(dj_settings.MEDIA_ROOT, safe_subpath)
    if not abs_path.startswith(str(dj_settings.MEDIA_ROOT)):
        return Response({'error': 'Некорректный путь'}, status=status.HTTP_400_BAD_REQUEST)

    if not os.path.exists(abs_path):
        raise Http404()

    # Отдаём файл безопасно
    return FileResponse(open(abs_path, 'rb'))

# APPOINTMENT BOOKING SYSTEM

from .models import Appointment, DoctorSchedule, MedicalRecord, VitalSigns, Notification, UserProfile, Review
from datetime import datetime, date, timedelta

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def appointments(request):
    """Get all appointments or create a new one"""
    if request.method == 'GET':
        user = request.user
        if user.role == 'patient':
            appts = Appointment.objects.filter(patient=user).select_related('doctor', 'doctor__profile')
        elif user.role == 'doctor':
            appts = Appointment.objects.filter(doctor=user).select_related('patient', 'patient__profile')
        else:
            appts = Appointment.objects.all().select_related('patient', 'doctor')

        data = []
        for a in appts:
            data.append({
                'id': a.id,
                'patient': {
                    'id': a.patient.id,
                    'full_name': a.patient.full_name,
                    'email': a.patient.email,
                    'avatar': a.patient.avatar,
                },
                'doctor': {
                    'id': a.doctor.id,
                    'full_name': a.doctor.full_name,
                    'email': a.doctor.email,
                    'avatar': a.doctor.avatar,
                    'specialization': getattr(a.doctor.profile, 'specialization', None) if hasattr(a.doctor, 'profile') else None,
                },
                'appointment_date': str(a.appointment_date),
                'appointment_time': str(a.appointment_time),
                'duration_minutes': a.duration_minutes,
                'status': a.status,
                'reason': a.reason,
                'notes': a.notes,
                'doctor_notes': a.doctor_notes,
                'is_upcoming': a.is_upcoming,
                'created_at': a.created_at.isoformat(),
            })
        return Response(data)

    if request.method == 'POST':
        if request.user.role != 'patient':
            return Response({'error': 'Only patients can book appointments'}, status=403)

        doctor_id = request.data.get('doctor_id')
        appointment_date = request.data.get('appointment_date')
        appointment_time = request.data.get('appointment_time')
        reason = request.data.get('reason', '')
        duration_minutes = request.data.get('duration_minutes', 30)

        if not all([doctor_id, appointment_date, appointment_time]):
            return Response({'error': 'doctor_id, appointment_date and appointment_time are required'}, status=400)

        try:
            doctor = User.objects.get(id=doctor_id, role='doctor')
        except User.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=404)

        # Check if slot is already taken
        if Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=['pending', 'confirmed']
        ).exists():
            return Response({'error': 'This time slot is already booked'}, status=400)

        # Check date is not in the past
        try:
            appt_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            if appt_date < date.today():
                return Response({'error': 'Cannot book appointments in the past'}, status=400)
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            duration_minutes=duration_minutes,
            reason=reason,
            status='pending',
        )

        send_appointment_confirmation_email(appointment)
        send_appointment_sms(appointment, event='booked')

        return Response({
            'id': appointment.id,
            'message': 'Appointment booked successfully',
            'status': appointment.status,
            'appointment_date': str(appointment.appointment_date),
            'appointment_time': str(appointment.appointment_time),
        }, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def appointment_detail(request, appointment_id):
    """Get, update or cancel a specific appointment"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=404)

    # Only patient, doctor or admin can access
    if request.user not in [appointment.patient, appointment.doctor] and request.user.role != 'admin':
        return Response({'error': 'Permission denied'}, status=403)

    if request.method == 'GET':
        return Response({
            'id': appointment.id,
            'patient': {
                'id': appointment.patient.id,
                'full_name': appointment.patient.full_name,
                'email': appointment.patient.email,
                'avatar': appointment.patient.avatar,
            },
            'doctor': {
                'id': appointment.doctor.id,
                'full_name': appointment.doctor.full_name,
                'specialization': getattr(appointment.doctor.profile, 'specialization', None) if hasattr(appointment.doctor, 'profile') else None,
            },
            'appointment_date': str(appointment.appointment_date),
            'appointment_time': str(appointment.appointment_time),
            'duration_minutes': appointment.duration_minutes,
            'status': appointment.status,
            'reason': appointment.reason,
            'notes': appointment.notes,
            'doctor_notes': appointment.doctor_notes,
            'is_upcoming': appointment.is_upcoming,
            'created_at': appointment.created_at.isoformat(),
        })

    if request.method == 'PATCH':
        # Doctor can confirm or add notes
        if request.user == appointment.doctor:
            if 'status' in request.data:
                new_status = request.data['status']
                if new_status in ['confirmed', 'completed', 'no_show']:
                    appointment.status = new_status
            if 'doctor_notes' in request.data:
                appointment.doctor_notes = request.data['doctor_notes']
            appointment.save()
            return Response({'message': 'Appointment updated', 'status': appointment.status})

        # Patient can update reason/notes
        if request.user == appointment.patient:
            if 'reason' in request.data:
                appointment.reason = request.data['reason']
            if 'notes' in request.data:
                appointment.notes = request.data['notes']
            appointment.save()
            return Response({'message': 'Appointment updated'})

        return Response({'error': 'Permission denied'}, status=403)

    if request.method == 'DELETE':
        # Both patient and doctor can cancel
        if appointment.status in ['completed', 'cancelled']:
            return Response({'error': 'Cannot cancel a completed or already cancelled appointment'}, status=400)

        appointment.status = 'cancelled'
        appointment.cancelled_by = request.user
        appointment.cancellation_reason = request.data.get('reason', '')
        appointment.save()
        return Response({'message': 'Appointment cancelled successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_available_slots(request, doctor_id):
    """Get available time slots for a doctor on a specific date"""
    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'date parameter is required (YYYY-MM-DD)'}, status=400)

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        doctor = User.objects.get(id=doctor_id, role='doctor')
    except (ValueError, User.DoesNotExist):
        return Response({'error': 'Invalid date or doctor not found'}, status=400)

    # Get doctor's schedule for that day of week
    day_of_week = target_date.weekday()
    try:
        schedule = DoctorSchedule.objects.get(doctor=doctor, day_of_week=day_of_week, is_available=True)
    except DoctorSchedule.DoesNotExist:
        return Response({'available_slots': [], 'message': 'Doctor is not available on this day'})

    # Generate all possible slots
    slot_duration = schedule.slot_duration_minutes
    all_slots = []
    current = datetime.combine(target_date, schedule.start_time)
    end = datetime.combine(target_date, schedule.end_time)

    while current + timedelta(minutes=slot_duration) <= end:
        all_slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=slot_duration)

    # Remove already booked slots
    booked = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=target_date,
        status__in=['pending', 'confirmed']
    ).values_list('appointment_time', flat=True)

    booked_times = [t.strftime('%H:%M') for t in booked]
    available_slots = [s for s in all_slots if s not in booked_times]

    return Response({
        'doctor_id': doctor_id,
        'date': date_str,
        'available_slots': available_slots,
        'booked_slots': booked_times,
        'slot_duration_minutes': slot_duration,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def doctor_schedule(request):
    """Get or set doctor's weekly schedule"""
    if request.user.role != 'doctor':
        return Response({'error': 'Only doctors can manage schedules'}, status=403)

    if request.method == 'GET':
        schedules = DoctorSchedule.objects.filter(doctor=request.user)
        data = [{
            'id': s.id,
            'day_of_week': s.day_of_week,
            'day_name': s.get_day_of_week_display(),
            'start_time': str(s.start_time),
            'end_time': str(s.end_time),
            'is_available': s.is_available,
            'slot_duration_minutes': s.slot_duration_minutes,
        } for s in schedules]
        return Response(data)

    if request.method == 'POST':
        day_of_week = request.data.get('day_of_week')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        is_available = request.data.get('is_available', True)
        slot_duration = request.data.get('slot_duration_minutes', 30)

        if day_of_week is None or not start_time or not end_time:
            return Response({'error': 'day_of_week, start_time and end_time are required'}, status=400)

        schedule, created = DoctorSchedule.objects.update_or_create(
            doctor=request.user,
            day_of_week=day_of_week,
            defaults={
                'start_time': start_time,
                'end_time': end_time,
                'is_available': is_available,
                'slot_duration_minutes': slot_duration,
            }
        )

        return Response({
            'message': 'Schedule saved successfully',
            'day_name': schedule.get_day_of_week_display(),
            'start_time': str(schedule.start_time),
            'end_time': str(schedule.end_time),
            'is_available': schedule.is_available,
        }, status=201 if created else 200)

# MEDICAL RECORDS SYSTEM

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def medical_records(request):
    """Get all medical records or create a new one"""
    if request.method == 'GET':
        user = request.user
        if user.role == 'patient':
            records = MedicalRecord.objects.filter(
                patient=user, is_visible_to_patient=True
            ).select_related('doctor', 'doctor__profile').prefetch_related('prescriptions')
        elif user.role == 'doctor':
            records = MedicalRecord.objects.filter(
                doctor=user
            ).select_related('patient', 'patient__profile').prefetch_related('prescriptions')
        else:
            records = MedicalRecord.objects.all().select_related('patient', 'doctor').prefetch_related('prescriptions')

        data = []
        for r in records:
            data.append({
                'id': r.id,
                'record_type': r.record_type,
                'title': r.title,
                'description': r.description,
                'diagnosis_code': r.diagnosis_code,
                'medications': r.medications,
                'patient': {'id': r.patient.id, 'full_name': r.patient.full_name},
                'doctor': {
                    'id': r.doctor.id,
                    'full_name': r.doctor.full_name,
                    'specialization': getattr(r.doctor.profile, 'specialization', None) if hasattr(r.doctor, 'profile') else None,
                },
                'consultation_id': r.consultation_id,
                'appointment_id': r.appointment_id,
                'created_at': r.created_at.isoformat(),
            })
        return Response(data)

    if request.method == 'POST':
        if request.user.role != 'doctor':
            return Response({'error': 'Only doctors can create medical records'}, status=403)

        required = ['patient_id', 'record_type', 'title', 'description']
        for field in required:
            if not request.data.get(field):
                return Response({'error': f'{field} is required'}, status=400)

        try:
            patient = User.objects.get(id=request.data['patient_id'], role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)

        record = MedicalRecord.objects.create(
            patient=patient,
            doctor=request.user,
            record_type=request.data['record_type'],
            title=request.data['title'],
            description=request.data['description'],
            diagnosis_code=request.data.get('diagnosis_code', ''),
            medications=request.data.get('medications', []),
            consultation_id=request.data.get('consultation_id'),
            appointment_id=request.data.get('appointment_id'),
            is_visible_to_patient=request.data.get('is_visible_to_patient', True),
        )
        return Response({'id': record.id, 'message': 'Medical record created'}, status=201)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def medical_record_detail(request, record_id):
    """Get, update or delete a medical record"""
    try:
        record = MedicalRecord.objects.get(id=record_id)
    except MedicalRecord.DoesNotExist:
        return Response({'error': 'Record not found'}, status=404)

    if request.user not in [record.patient, record.doctor] and request.user.role != 'admin':
        return Response({'error': 'Permission denied'}, status=403)

    if request.method == 'GET':
        prescriptions = [{
            'id': p.id,
            'medication_name': p.medication_name,
            'dosage': p.dosage,
            'frequency': p.frequency,
            'duration_days': p.duration_days,
            'instructions': p.instructions,
            'status': p.status,
            'prescribed_at': p.prescribed_at.isoformat(),
        } for p in record.prescriptions.all()]

        return Response({
            'id': record.id,
            'record_type': record.record_type,
            'title': record.title,
            'description': record.description,
            'diagnosis_code': record.diagnosis_code,
            'medications': record.medications,
            'attachments': record.attachments,
            'patient': {'id': record.patient.id, 'full_name': record.patient.full_name},
            'doctor': {'id': record.doctor.id, 'full_name': record.doctor.full_name},
            'prescriptions': prescriptions,
            'created_at': record.created_at.isoformat(),
            'updated_at': record.updated_at.isoformat(),
        })

    if request.method == 'PATCH':
        if request.user != record.doctor:
            return Response({'error': 'Only the doctor can edit this record'}, status=403)
        for field in ['title', 'description', 'diagnosis_code', 'medications', 'is_visible_to_patient']:
            if field in request.data:
                setattr(record, field, request.data[field])
        record.save()
        return Response({'message': 'Record updated'})

    if request.method == 'DELETE':
        if request.user != record.doctor and request.user.role != 'admin':
            return Response({'error': 'Permission denied'}, status=403)
        record.delete()
        return Response({'message': 'Record deleted'})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vital_signs(request, patient_id=None):
    """Get or record vital signs"""
    if request.method == 'GET':
        pid = patient_id or request.user.id
        if request.user.id != pid and request.user.role not in ['doctor', 'admin']:
            return Response({'error': 'Permission denied'}, status=403)
        vitals = VitalSigns.objects.filter(patient_id=pid)[:20]
        data = [{
            'id': v.id,
            'blood_pressure': f"{v.blood_pressure_systolic}/{v.blood_pressure_diastolic}" if v.blood_pressure_systolic else None,
            'heart_rate': v.heart_rate,
            'temperature': float(v.temperature) if v.temperature else None,
            'weight_kg': float(v.weight_kg) if v.weight_kg else None,
            'height_cm': float(v.height_cm) if v.height_cm else None,
            'oxygen_saturation': v.oxygen_saturation,
            'bmi': v.bmi,
            'notes': v.notes,
            'recorded_at': v.recorded_at.isoformat(),
        } for v in vitals]
        return Response(data)

    if request.method == 'POST':
        target_patient = request.user
        if request.data.get('patient_id') and request.user.role in ['doctor', 'admin']:
            try:
                target_patient = User.objects.get(id=request.data['patient_id'])
            except User.DoesNotExist:
                return Response({'error': 'Patient not found'}, status=404)

        vital = VitalSigns.objects.create(
            patient=target_patient,
            recorded_by=request.user,
            blood_pressure_systolic=request.data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=request.data.get('blood_pressure_diastolic'),
            heart_rate=request.data.get('heart_rate'),
            temperature=request.data.get('temperature'),
            weight_kg=request.data.get('weight_kg'),
            height_cm=request.data.get('height_cm'),
            oxygen_saturation=request.data.get('oxygen_saturation'),
            notes=request.data.get('notes', ''),
        )
        return Response({'id': vital.id, 'bmi': vital.bmi, 'message': 'Vitals recorded'}, status=201)

# NOTIFICATIONS SYSTEM

def create_notification(recipient, notification_type, title, message, sender=None, link=None, data=None):
    """Helper function to create a notification"""
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link or '',
        data=data or {},
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    """Get all notifications for the current user"""
    notifs = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender')[:50]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    data = [{
        'id': n.id,
        'type': n.notification_type,
        'title': n.title,
        'message': n.message,
        'is_read': n.is_read,
        'link': n.link,
        'data': n.data,
        'created_at': n.created_at.isoformat(),
    } for n in notifs]

    return Response({
        'notifications': data,
        'unread_count': unread_count,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notif = Notification.objects.get(id=notification_id, recipient=request.user)
        notif.mark_as_read()
        return Response({'message': 'Marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())
    return Response({'message': 'All notifications marked as read'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        notif = Notification.objects.get(id=notification_id, recipient=request.user)
        notif.delete()
        return Response({'message': 'Notification deleted'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404) 

# PATIENT DASHBOARD API

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_dashboard(request):
    """Complete dashboard summary for a patient"""
    if request.user.role != 'patient':
        return Response({'error': 'Only patients can access this dashboard'}, status=403)

    user = request.user
    today = date.today()

    # Upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=user,
        status__in=['pending', 'confirmed'],
        appointment_date__gte=today
    ).select_related('doctor', 'doctor__profile').order_by('appointment_date', 'appointment_time')[:5]

    # Recent medical records
    recent_records = MedicalRecord.objects.filter(
        patient=user,
        is_visible_to_patient=True
    ).select_related('doctor').order_by('-created_at')[:5]

    # Active prescriptions
    active_prescriptions = Prescription.objects.filter(
        patient=user,
        status='active'
    ).select_related('doctor', 'medical_record').order_by('-prescribed_at')[:5]

    # Latest vital signs
    latest_vitals = VitalSigns.objects.filter(patient=user).order_by('-recorded_at').first()

    # Unread notifications
    unread_notifications = Notification.objects.filter(
        recipient=user, is_read=False
    ).order_by('-created_at')[:5]

    # Stats
    total_consultations = user.patient_consultations.count()
    total_appointments = user.patient_appointments.count()
    total_records = user.medical_records.filter(is_visible_to_patient=True).count()
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    return Response({
        'user': {
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'avatar': user.avatar,
        },
        'stats': {
            'total_consultations': total_consultations,
            'total_appointments': total_appointments,
            'total_medical_records': total_records,
            'unread_notifications': unread_count,
        },
        'upcoming_appointments': [{
            'id': a.id,
            'doctor_name': a.doctor.full_name,
            'doctor_avatar': a.doctor.avatar,
            'specialization': getattr(a.doctor.profile, 'specialization', None) if hasattr(a.doctor, 'profile') else None,
            'appointment_date': str(a.appointment_date),
            'appointment_time': str(a.appointment_time),
            'status': a.status,
            'reason': a.reason,
        } for a in upcoming_appointments],
        'recent_medical_records': [{
            'id': r.id,
            'record_type': r.record_type,
            'title': r.title,
            'doctor_name': r.doctor.full_name,
            'created_at': r.created_at.isoformat(),
        } for r in recent_records],
        'active_prescriptions': [{
            'id': p.id,
            'medication_name': p.medication_name,
            'dosage': p.dosage,
            'frequency': p.frequency,
            'duration_days': p.duration_days,
            'doctor_name': p.doctor.full_name,
            'prescribed_at': p.prescribed_at.isoformat(),
            'expires_at': str(p.expires_at) if p.expires_at else None,
        } for p in active_prescriptions],
        'latest_vitals': {
            'blood_pressure': f"{latest_vitals.blood_pressure_systolic}/{latest_vitals.blood_pressure_diastolic}" if latest_vitals and latest_vitals.blood_pressure_systolic else None,
            'heart_rate': latest_vitals.heart_rate if latest_vitals else None,
            'temperature': float(latest_vitals.temperature) if latest_vitals and latest_vitals.temperature else None,
            'weight_kg': float(latest_vitals.weight_kg) if latest_vitals and latest_vitals.weight_kg else None,
            'bmi': latest_vitals.bmi if latest_vitals else None,
            'recorded_at': latest_vitals.recorded_at.isoformat() if latest_vitals else None,
        },
        'unread_notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'created_at': n.created_at.isoformat(),
        } for n in unread_notifications],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_dashboard(request):
    """Complete dashboard summary for a doctor"""
    if request.user.role != 'doctor':
        return Response({'error': 'Only doctors can access this dashboard'}, status=403)

    user = request.user
    today = date.today()

    # Today's appointments
    todays_appointments = Appointment.objects.filter(
        doctor=user,
        appointment_date=today,
        status__in=['pending', 'confirmed']
    ).select_related('patient', 'patient__profile').order_by('appointment_time')

    # Upcoming appointments (next 7 days)
    upcoming_appointments = Appointment.objects.filter(
        doctor=user,
        status__in=['pending', 'confirmed'],
        appointment_date__gt=today,
        appointment_date__lte=today + timedelta(days=7)
    ).select_related('patient').order_by('appointment_date', 'appointment_time')[:10]

    # Recent patients (distinct patients from consultations)
    recent_consultations = user.doctor_consultations.filter(
        status='completed'
    ).select_related('patient').order_by('-completed_at')[:5]

    # Unread notifications
    unread_notifications = Notification.objects.filter(
        recipient=user, is_read=False
    ).order_by('-created_at')[:5]

    # Stats
    total_patients = user.doctor_consultations.values('patient').distinct().count()
    total_consultations = user.doctor_consultations.count()
    total_appointments = user.doctor_appointments.count()
    pending_appointments = user.doctor_appointments.filter(status='pending').count()
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()

    return Response({
        'user': {
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'avatar': user.avatar,
            'specialization': getattr(user.profile, 'specialization', None) if hasattr(user, 'profile') else None,
        },
        'stats': {
            'total_patients': total_patients,
            'total_consultations': total_consultations,
            'total_appointments': total_appointments,
            'pending_appointments': pending_appointments,
            'unread_notifications': unread_count,
        },
        'todays_appointments': [{
            'id': a.id,
            'patient_name': a.patient.full_name,
            'patient_avatar': a.patient.avatar,
            'appointment_time': str(a.appointment_time),
            'duration_minutes': a.duration_minutes,
            'status': a.status,
            'reason': a.reason,
        } for a in todays_appointments],
        'upcoming_appointments': [{
            'id': a.id,
            'patient_name': a.patient.full_name,
            'appointment_date': str(a.appointment_date),
            'appointment_time': str(a.appointment_time),
            'status': a.status,
        } for a in upcoming_appointments],
        'recent_patients': [{
            'id': c.patient.id,
            'full_name': c.patient.full_name,
            'avatar': c.patient.avatar,
            'last_consultation': c.completed_at.isoformat() if c.completed_at else None,
        } for c in recent_consultations],
        'unread_notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'created_at': n.created_at.isoformat(),
        } for n in unread_notifications],
    })

# DOCTOR SEARCH & FILTERING

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_doctors(request):
    """Search and filter doctors by specialization, city, language, name"""
    queryset = User.objects.filter(
        role='doctor',
        is_active=True
    ).select_related('profile', 'profile__city', 'profile__region').prefetch_related(
        'schedules', 'received_reviews', 'doctor_consultations'
    ) 

    # Filter by name
    name = request.query_params.get('name')
    if name:
        queryset = queryset.filter(
            models.Q(first_name__icontains=name) |
            models.Q(last_name__icontains=name)
        )

    # Filter by specialization
    specialization = request.query_params.get('specialization')
    if specialization:
        queryset = queryset.filter(
            profile__specialization__icontains=specialization
        )

    # Filter by city
    city = request.query_params.get('city')
    if city:
        queryset = queryset.filter(
            profile__city__name__icontains=city
        )

    # Filter by region
    region = request.query_params.get('region')
    if region:
        queryset = queryset.filter(
            profile__region__name__icontains=region
        )

    # Filter by language
    language = request.query_params.get('language')
    if language:
        queryset = queryset.filter(
            profile__languages__icontains=language
        )

    # Filter by availability (has schedule set up)
    available_only = request.query_params.get('available_only')
    if available_only == 'true':
        queryset = queryset.filter(schedules__is_available=True).distinct()

    # Build response
    data = []
    for doctor in queryset:
        profile = getattr(doctor, 'profile', None)

        # Get average rating if reviews exist
        avg_rating = None
        review_count = 0
        if hasattr(doctor, 'received_reviews'):
            reviews = doctor.received_reviews.all()
            review_count = reviews.count()
            if review_count > 0:
                avg_rating = round(sum(r.rating for r in reviews) / review_count, 1)

        # Get next available appointment slot
        has_schedule = doctor.schedules.filter(is_available=True).exists()

        data.append({
            'id': doctor.id,
            'full_name': doctor.full_name,
            'avatar': doctor.avatar,
            'email': doctor.email,
            'specialization': profile.specialization if profile else None,
            'experience': profile.experience if profile else None,
            'education': profile.education if profile else None,
            'languages': profile.languages if profile else [],
            'city': profile.city.name if profile and profile.city else None,
            'region': profile.region.name if profile and profile.region else None,
            'license_number': profile.license_number if profile else None,
            'additional_info': profile.additional_info if profile else None,
            'avg_rating': avg_rating,
            'review_count': review_count,
            'has_schedule': has_schedule,
            'total_consultations': doctor.doctor_consultations.filter(status='completed').count(),
        })

    # Sort by total consultations (most experienced first)
    data.sort(key=lambda x: x['total_consultations'], reverse=True)

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    total = len(data)
    paginated = data[start:end]

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'doctors': paginated,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_profile_detail(request, doctor_id):
    """Get full profile of a specific doctor"""
    try:
        doctor = User.objects.get(id=doctor_id, role='doctor')
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    profile = getattr(doctor, 'profile', None)

    # Get schedule
    schedules = [{
        'day_of_week': s.day_of_week,
        'day_name': s.get_day_of_week_display(),
        'start_time': str(s.start_time),
        'end_time': str(s.end_time),
        'is_available': s.is_available,
        'slot_duration_minutes': s.slot_duration_minutes,
    } for s in doctor.schedules.filter(is_available=True)]

    # Get completed consultations count
    total_consultations = doctor.doctor_consultations.filter(status='completed').count()

    return Response({
        'id': doctor.id,
        'full_name': doctor.full_name,
        'avatar': doctor.avatar,
        'email': doctor.email,
        'specialization': profile.specialization if profile else None,
        'experience': profile.experience if profile else None,
        'education': profile.education if profile else None,
        'languages': profile.languages if profile else [],
        'city': profile.city.name if profile and profile.city else None,
        'region': profile.region.name if profile and profile.region else None,
        'license_number': profile.license_number if profile else None,
        'additional_info': profile.additional_info if profile else None,
        'total_consultations': total_consultations,
        'schedule': schedules,
    })


@api_view(['GET'])
def specializations_list(request):
    """Get all unique specializations for filter dropdown"""
    cache_key = 'specializations_list'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    from django.db.models import Count
    specs = UserProfile.objects.filter(
        user__role='doctor',
        user__is_active=True,
        specialization__isnull=False
    ).exclude(
        specialization=''
    ).values('specialization').annotate(
        count=Count('specialization')
    ).order_by('-count')

    data = [{'specialization': s['specialization'], 'doctor_count': s['count']} for s in specs]
    cache.set(cache_key, data, 3600)  # Cache for 1 hour
    return Response(data)

# REVIEWS & RATINGS SYSTEM

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def doctor_reviews(request, doctor_id):
    """Get all reviews for a doctor or submit a new review"""

    try:
        doctor = User.objects.get(id=doctor_id, role='doctor')
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    if request.method == 'GET':
        reviews = Review.objects.filter(
            doctor=doctor, is_visible=True
        ).select_related('patient')

        # Calculate stats
        total = reviews.count()
        avg_rating = 0
        rating_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        if total > 0:
            total_score = sum(r.rating for r in reviews)
            avg_rating = round(total_score / total, 1)
            for r in reviews:
                rating_breakdown[r.rating] += 1

        data = []
        for r in reviews:
            data.append({
                'id': r.id,
                'rating': r.rating,
                'comment': r.comment,
                'is_anonymous': r.is_anonymous,
                'patient_name': 'Anonymous' if r.is_anonymous else r.patient.full_name,
                'patient_avatar': None if r.is_anonymous else r.patient.avatar,
                'created_at': r.created_at.isoformat(),
            })

        return Response({
            'doctor_id': doctor_id,
            'avg_rating': avg_rating,
            'total_reviews': total,
            'rating_breakdown': rating_breakdown,
            'reviews': data,
        })

    if request.method == 'POST':
        if request.user.role != 'patient':
            return Response({'error': 'Only patients can submit reviews'}, status=403)

        rating = request.data.get('rating')
        if not rating or int(rating) not in [1, 2, 3, 4, 5]:
            return Response({'error': 'Rating must be between 1 and 5'}, status=400)

        consultation_id = request.data.get('consultation_id')

        # Check if patient already reviewed this doctor for this consultation
        if consultation_id:
            if Review.objects.filter(
                patient=request.user,
                doctor=doctor,
                consultation_id=consultation_id
            ).exists():
                return Response({'error': 'You have already reviewed this doctor for this consultation'}, status=400)
        else:
            # Allow one review per doctor if no consultation specified
            if Review.objects.filter(
                patient=request.user,
                doctor=doctor,
                consultation__isnull=True
            ).exists():
                return Response({'error': 'You have already reviewed this doctor'}, status=400)

        review = Review.objects.create(
            patient=request.user,
            doctor=doctor,
            rating=int(rating),
            comment=request.data.get('comment', ''),
            is_anonymous=request.data.get('is_anonymous', False),
            consultation_id=consultation_id,
            appointment_id=request.data.get('appointment_id'),
        )

        # Send notification to doctor
        create_notification(
            recipient=doctor,
            sender=request.user,
            notification_type='general',
            title='New Review Received',
            message=f'You received a {rating}-star review from a patient.',
            link=f'/doctor/reviews/',
        )

        return Response({
            'id': review.id,
            'message': 'Review submitted successfully',
            'rating': review.rating,
        }, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def review_detail(request, review_id):
    """Edit or delete a review"""
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=404)

    if request.user != review.patient and request.user.role != 'admin':
        return Response({'error': 'Permission denied'}, status=403)

    if request.method == 'PATCH':
        if 'rating' in request.data:
            new_rating = int(request.data['rating'])
            if new_rating not in [1, 2, 3, 4, 5]:
                return Response({'error': 'Rating must be between 1 and 5'}, status=400)
            review.rating = new_rating
        if 'comment' in request.data:
            review.comment = request.data['comment']
        if 'is_anonymous' in request.data:
            review.is_anonymous = request.data['is_anonymous']
        review.save()
        return Response({'message': 'Review updated'})

    if request.method == 'DELETE':
        review.delete()
        return Response({'message': 'Review deleted'})
    


# ============================================
# ADMIN PANEL & DOCTOR APPROVAL SYSTEM
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    """Admin overview stats"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    today = date.today()

    total_users = User.objects.count()
    total_patients = User.objects.filter(role='patient').count()
    total_doctors = User.objects.filter(role='doctor').count()
    pending_doctors = User.objects.filter(role='doctor', is_active=False).count()
    total_consultations = Consultation.objects.count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    total_reviews = Review.objects.count()

    recent_users = User.objects.order_by('-date_joined')[:5]
    pending_doctor_list = User.objects.filter(
        role='doctor', is_active=False
    ).select_related('profile').order_by('-date_joined')[:10]

    return Response({
        'stats': {
            'total_users': total_users,
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'pending_doctors': pending_doctors,
            'total_consultations': total_consultations,
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'total_reviews': total_reviews,
        },
        'recent_users': [{
            'id': u.id,
            'full_name': u.full_name,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'date_joined': u.date_joined.isoformat(),
        } for u in recent_users],
        'pending_doctors': [{
            'id': d.id,
            'full_name': d.full_name,
            'email': d.email,
            'specialization': getattr(d.profile, 'specialization', None) if hasattr(d, 'profile') else None,
            'license_number': getattr(d.profile, 'license_number', None) if hasattr(d, 'profile') else None,
            'date_joined': d.date_joined.isoformat(),
        } for d in pending_doctor_list],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    """List all users with filters"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    queryset = User.objects.all().order_by('-date_joined')

    role = request.query_params.get('role')
    if role:
        queryset = queryset.filter(role=role)

    is_active = request.query_params.get('is_active')
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active == 'true')

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(email__icontains=search)
        )

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size

    total = queryset.count()
    users = queryset[start:end]

    data = [{
        'id': u.id,
        'full_name': u.full_name,
        'email': u.email,
        'role': u.role,
        'is_active': u.is_active,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
    } for u in users]

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'users': data,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_approve_doctor(request, doctor_id):
    """Approve or reject a doctor application"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    try:
        doctor = User.objects.get(id=doctor_id, role='doctor')
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    action = request.data.get('action')  # 'approve' or 'reject'
    if action not in ['approve', 'reject']:
        return Response({'error': 'action must be approve or reject'}, status=400)

    if action == 'approve':
        doctor.is_active = True
        doctor.save()
        create_notification(
            recipient=doctor,
            sender=request.user,
            notification_type='doctor_approved',
            title='Your application has been approved!',
            message='Congratulations! Your doctor profile has been approved. You can now receive patients.',
            link='/doctor/dashboard/',
        )
        send_doctor_approval_email(doctor, approved=True)
        send_doctor_approval_sms(doctor, approved=True)

        return Response({'message': f'Dr. {doctor.full_name} has been approved'})

    if action == 'reject':
        reason = request.data.get('reason', 'Your application did not meet our requirements.')
        doctor.is_active = False
        doctor.save()
        create_notification(
            recipient=doctor,
            sender=request.user,
            notification_type='doctor_rejected',
            title='Your application was not approved',
            message=reason,
        )
        send_doctor_approval_email(doctor, approved=False, reason=reason)
        send_doctor_approval_sms(doctor, approved=False)


        return Response({'message': f'Dr. {doctor.full_name} has been rejected'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_toggle_user(request, user_id):
    """Activate or deactivate any user account"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    if user == request.user:
        return Response({'error': 'You cannot deactivate your own account'}, status=400)

    user.is_active = not user.is_active
    user.save()

    status_text = 'activated' if user.is_active else 'deactivated'
    return Response({'message': f'User {user.full_name} has been {status_text}', 'is_active': user.is_active})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_user(request, user_id):
    """Delete a user account"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    if user == request.user:
        return Response({'error': 'You cannot delete your own account'}, status=400)

    name = user.full_name
    user.delete()
    return Response({'message': f'User {name} has been deleted'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_consultations_list(request):
    """List all consultations for admin"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    queryset = Consultation.objects.all().select_related(
        'patient', 'doctor'
    ).order_by('-created_at')[:100]

    data = [{
        'id': c.id,
        'patient_name': c.patient.full_name,
        'doctor_name': c.doctor.full_name,
        'status': c.status,
        'created_at': c.created_at.isoformat(),
        'completed_at': c.completed_at.isoformat() if c.completed_at else None,
    } for c in queryset]

    return Response({'count': len(data), 'consultations': data})

# FILE UPLOADS SYSTEM

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_avatar(request):
    """Upload or update profile avatar"""
    if 'avatar' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)

    file = request.FILES['avatar']

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        return Response({'error': 'Only JPEG, PNG, WebP and GIF images are allowed'}, status=400)

    # Validate file size (max 5MB)
    if file.size > 5 * 1024 * 1024:
        return Response({'error': 'File size must be under 5MB'}, status=400)

    # Delete old avatar if exists
    user = request.user
    if user.avatar:
        old_path = os.path.join(settings.MEDIA_ROOT, user.avatar)
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new avatar
    ext = file.name.split('.')[-1].lower()
    filename = f"avatars/{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    saved_path = default_storage.save(filename, file)

    user.avatar = saved_path
    user.save()

    return Response({
        'message': 'Avatar uploaded successfully',
        'avatar_url': request.build_absolute_uri(settings.MEDIA_URL + saved_path),
        'avatar': saved_path,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_medical_document(request):
    """Upload a medical document (PDF, image)"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)

    file = request.FILES['file']

    # Validate file type
    allowed_types = [
        'image/jpeg', 'image/png', 'image/webp',
        'application/pdf',
    ]
    if file.content_type not in allowed_types:
        return Response({'error': 'Only JPEG, PNG, WebP and PDF files are allowed'}, status=400)

    # Validate file size (max 20MB)
    if file.size > 20 * 1024 * 1024:
        return Response({'error': 'File size must be under 20MB'}, status=400)

    # Save file
    ext = file.name.split('.')[-1].lower()
    folder = f"medical_docs/{request.user.id}/"
    filename = f"{folder}{uuid.uuid4().hex}.{ext}"
    saved_path = default_storage.save(filename, file)

    file_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)

    return Response({
        'message': 'File uploaded successfully',
        'file_url': file_url,
        'file_path': saved_path,
        'file_name': file.name,
        'file_size': file.size,
        'content_type': file.content_type,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_consultation_file(request, consultation_id):
    """Upload a file to a specific consultation"""
    try:
        consultation = Consultation.objects.get(id=consultation_id)
    except Consultation.DoesNotExist:
        return Response({'error': 'Consultation not found'}, status=404)

    if request.user not in [consultation.patient, consultation.doctor]:
        return Response({'error': 'Permission denied'}, status=403)

    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)

    file = request.FILES['file']

    allowed_types = [
        'image/jpeg', 'image/png', 'image/webp',
        'application/pdf',
    ]
    if file.content_type not in allowed_types:
        return Response({'error': 'Only JPEG, PNG, WebP and PDF files are allowed'}, status=400)

    if file.size > 20 * 1024 * 1024:
        return Response({'error': 'File size must be under 20MB'}, status=400)

    ext = file.name.split('.')[-1].lower()
    folder = f"consultations/{consultation_id}/"
    filename = f"{folder}{uuid.uuid4().hex}.{ext}"
    saved_path = default_storage.save(filename, file)

    file_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)

    return Response({
        'message': 'File uploaded successfully',
        'file_url': file_url,
        'file_path': saved_path,
        'file_name': file.name,
        'file_size': file.size,
        'content_type': file.content_type,
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_file(request):
    """Delete an uploaded file"""
    file_path = request.data.get('file_path')
    if not file_path:
        return Response({'error': 'file_path is required'}, status=400)

    # Security: make sure user can only delete their own files
    if str(request.user.id) not in file_path:
        if request.user.role != 'admin':
            return Response({'error': 'Permission denied'}, status=403)

    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
        return Response({'message': 'File deleted successfully'})

    return Response({'error': 'File not found'}, status=404)

# EMAIL NOTIFICATIONS SYSTEM

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_email_notification(recipient_email, subject, html_message):
    """Helper function to send email notifications"""
    try:
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        print(f"Email sending failed: {e}")


def send_appointment_confirmation_email(appointment):
    """Send confirmation email when appointment is booked"""
    # Email to patient
    patient_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Healzy — Appointment Confirmed</h2>
        <p>Dear {appointment.patient.full_name},</p>
        <p>Your appointment has been successfully booked.</p>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Doctor:</strong> Dr. {appointment.doctor.full_name}</p>
            <p><strong>Date:</strong> {appointment.appointment_date}</p>
            <p><strong>Time:</strong> {appointment.appointment_time}</p>
            <p><strong>Duration:</strong> {appointment.duration_minutes} minutes</p>
            <p><strong>Status:</strong> {appointment.get_status_display()}</p>
        </div>
        <p>You can view your appointment details in the Healzy app.</p>
        <p style="color: #6b7280; font-size: 12px;">This is an automated message from Healzy Medical Platform.</p>
    </div>
    """
    send_email_notification(
        appointment.patient.email,
        f"Appointment Confirmed — Dr. {appointment.doctor.full_name}",
        patient_html
    )

    # Email to doctor
    doctor_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Healzy — New Appointment</h2>
        <p>Dear Dr. {appointment.doctor.full_name},</p>
        <p>You have a new appointment booked.</p>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Patient:</strong> {appointment.patient.full_name}</p>
            <p><strong>Date:</strong> {appointment.appointment_date}</p>
            <p><strong>Time:</strong> {appointment.appointment_time}</p>
            <p><strong>Reason:</strong> {appointment.reason or 'Not specified'}</p>
        </div>
        <p>You can manage your appointments in the Healzy app.</p>
        <p style="color: #6b7280; font-size: 12px;">This is an automated message from Healzy Medical Platform.</p>
    </div>
    """
    send_email_notification(
        appointment.doctor.email,
        f"New Appointment — {appointment.patient.full_name}",
        doctor_html
    )


def send_doctor_approval_email(doctor, approved=True, reason=None):
    """Send email when doctor is approved or rejected"""
    if approved:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #16a34a;">Healzy — Application Approved! 🎉</h2>
            <p>Dear Dr. {doctor.full_name},</p>
            <p>Congratulations! Your doctor profile on Healzy has been <strong>approved</strong>.</p>
            <p>You can now:</p>
            <ul>
                <li>Receive patient appointments</li>
                <li>Start online consultations</li>
                <li>Create medical records and prescriptions</li>
                <li>Set your weekly schedule</li>
            </ul>
            <p>Log in to your Healzy account to get started.</p>
            <p style="color: #6b7280; font-size: 12px;">This is an automated message from Healzy Medical Platform.</p>
        </div>
        """
        subject = "Your Healzy Doctor Application is Approved!"
    else:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Healzy — Application Update</h2>
            <p>Dear Dr. {doctor.full_name},</p>
            <p>We have reviewed your application and unfortunately it was not approved at this time.</p>
            <div style="background: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Reason:</strong> {reason or 'Your application did not meet our requirements.'}</p>
            </div>
            <p>You may reapply after addressing the issues mentioned above.</p>
            <p style="color: #6b7280; font-size: 12px;">This is an automated message from Healzy Medical Platform.</p>
        </div>
        """
        subject = "Update on Your Healzy Doctor Application"

    send_email_notification(doctor.email, subject, html)


def send_welcome_email(user):
    """Send welcome email when user registers"""
    role_text = "doctor" if user.role == "doctor" else "patient"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Welcome to Healzy! 👋</h2>
        <p>Dear {user.full_name},</p>
        <p>Thank you for joining Healzy as a <strong>{role_text}</strong>.</p>
        <p>With Healzy you can:</p>
        <ul>
            <li>Connect with qualified doctors online</li>
            <li>Book appointments easily</li>
            <li>Access your medical records securely</li>
            <li>Get AI-powered health guidance</li>
        </ul>
        <p>We're glad to have you on board!</p>
        <p style="color: #6b7280; font-size: 12px;">This is an automated message from Healzy Medical Platform.</p>
    </div>
    """
    send_email_notification(
        user.email,
        "Welcome to Healzy!",
        html
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_email(request):
    """Admin endpoint to test email sending"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    recipient = request.data.get('email', request.user.email)
    html = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Healzy — Test Email</h2>
        <p>This is a test email from Healzy Medical Platform.</p>
        <p>If you received this, email notifications are working correctly! ✅</p>
    </div>
    """
    send_email_notification(recipient, "Healzy — Test Email", html)
    return Response({'message': f'Test email sent to {recipient}'})

# ADDITIONAL API FEATURES

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response({'error': 'old_password and new_password are required'}, status=400)

    if not request.user.check_password(old_password):
        return Response({'error': 'Current password is incorrect'}, status=400)

    if len(new_password) < 8:
        return Response({'error': 'New password must be at least 8 characters'}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    return Response({'message': 'Password changed successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_statistics(request):
    """Get statistics for the current user"""
    user = request.user

    if user.role == 'patient':
        stats = {
            'total_appointments': user.patient_appointments.count(),
            'upcoming_appointments': user.patient_appointments.filter(
                status__in=['pending', 'confirmed'],
                appointment_date__gte=date.today()
            ).count(),
            'completed_appointments': user.patient_appointments.filter(status='completed').count(),
            'total_consultations': user.patient_consultations.count(),
            'total_medical_records': user.medical_records.filter(is_visible_to_patient=True).count(),
            'active_prescriptions': user.prescriptions.filter(status='active').count(),
            'total_reviews_given': user.given_reviews.count(),
            'unread_notifications': user.notifications.filter(is_read=False).count(),
        }
    elif user.role == 'doctor':
        stats = {
            'total_appointments': user.doctor_appointments.count(),
            'upcoming_appointments': user.doctor_appointments.filter(
                status__in=['pending', 'confirmed'],
                appointment_date__gte=date.today()
            ).count(),
            'completed_appointments': user.doctor_appointments.filter(status='completed').count(),
            'total_consultations': user.doctor_consultations.count(),
            'completed_consultations': user.doctor_consultations.filter(status='completed').count(),
            'total_patients': user.doctor_consultations.values('patient').distinct().count(),
            'total_medical_records_created': user.created_records.count(),
            'avg_rating': None,
            'total_reviews': user.received_reviews.count(),
            'unread_notifications': user.notifications.filter(is_read=False).count(),
        }
        reviews = user.received_reviews.all()
        if reviews.exists():
            stats['avg_rating'] = round(
                sum(r.rating for r in reviews) / reviews.count(), 1
            )
    else:
        stats = {
            'total_users': User.objects.count(),
            'total_doctors': User.objects.filter(role='doctor').count(),
            'total_patients': User.objects.filter(role='patient').count(),
            'total_consultations': Consultation.objects.count(),
            'total_appointments': Appointment.objects.count(),
        }

    return Response({'role': user.role, 'statistics': stats})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_issue(request):
    """Report a bug or issue"""
    title = request.data.get('title', '').strip()
    description = request.data.get('description', '').strip()
    category = request.data.get('category', 'general')

    if not title or not description:
        return Response({'error': 'title and description are required'}, status=400)

    # Send to Telegram support
    import html as html_lib
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_SUPPORT_CHAT_ID', '')

    if bot_token and chat_id:
        try:
            import requests as req
            text = (
                f"🐛 Bug Report\n"
                f"👤 User: {html_lib.escape(request.user.full_name)} (ID: {request.user.id})\n"
                f"📧 Email: {html_lib.escape(request.user.email)}\n"
                f"🔖 Category: {html_lib.escape(category)}\n"
                f"📌 Title: {html_lib.escape(title)}\n\n"
                f"📝 Description:\n{html_lib.escape(description)}"
            )
            req.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={'chat_id': chat_id, 'text': text},
                timeout=5
            )
        except Exception:
            pass

    return Response({'message': 'Issue reported successfully. Thank you!'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_global(request):
    """Global search across doctors, records and appointments"""
    query = request.query_params.get('q', '').strip()
    if len(query) < 2:
        return Response({'error': 'Query must be at least 2 characters'}, status=400)

    results = {}
    user = request.user

    # Search doctors
    doctors = User.objects.filter(
        role='doctor',
        is_active=True
    ).filter(
        models.Q(first_name__icontains=query) |
        models.Q(last_name__icontains=query) |
        models.Q(profile__specialization__icontains=query)
    ).select_related('profile')[:5]

    results['doctors'] = [{
        'id': d.id,
        'full_name': d.full_name,
        'specialization': getattr(d.profile, 'specialization', None) if hasattr(d, 'profile') else None,
        'avatar': d.avatar,
    } for d in doctors]

    # Search medical records (for patients and doctors)
    if user.role == 'patient':
        records = MedicalRecord.objects.filter(
            patient=user,
            is_visible_to_patient=True
        ).filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query)
        )[:5]
    elif user.role == 'doctor':
        records = MedicalRecord.objects.filter(
            doctor=user
        ).filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query)
        )[:5]
    else:
        records = MedicalRecord.objects.none()

    results['medical_records'] = [{
        'id': r.id,
        'title': r.title,
        'record_type': r.record_type,
        'created_at': r.created_at.isoformat(),
    } for r in records]

    return Response({'query': query, 'results': results})

# APPOINTMENT REMINDERS & CALENDAR

from datetime import datetime, date, timedelta


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_calendar(request, doctor_id):
    """Get full month calendar for a doctor — available and booked slots"""
    year = int(request.query_params.get('year', date.today().year))
    month = int(request.query_params.get('month', date.today().month))

    try:
        doctor = User.objects.get(id=doctor_id, role='doctor')
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    # Get doctor's weekly schedule
    schedules = DoctorSchedule.objects.filter(doctor=doctor, is_available=True)
    schedule_map = {s.day_of_week: s for s in schedules}

    # Get all booked appointments for that month
    booked = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__year=year,
        appointment_date__month=month,
        status__in=['pending', 'confirmed']
    ).values('appointment_date', 'appointment_time', 'status')

    booked_map = {}
    for b in booked:
        d = str(b['appointment_date'])
        if d not in booked_map:
            booked_map[d] = []
        booked_map[d].append(b['appointment_time'].strftime('%H:%M'))

    # Build calendar days
    import calendar
    _, days_in_month = calendar.monthrange(year, month)

    calendar_data = []
    for day in range(1, days_in_month + 1):
        current_date = date(year, month, day)
        day_of_week = current_date.weekday()
        date_str = str(current_date)

        if day_of_week not in schedule_map:
            calendar_data.append({
                'date': date_str,
                'is_working_day': False,
                'available_slots': [],
                'booked_slots': [],
                'total_slots': 0,
                'available_count': 0,
            })
            continue

        schedule = schedule_map[day_of_week]
        slot_duration = schedule.slot_duration_minutes

        # Generate all slots
        all_slots = []
        current = datetime.combine(current_date, schedule.start_time)
        end = datetime.combine(current_date, schedule.end_time)
        while current + timedelta(minutes=slot_duration) <= end:
            all_slots.append(current.strftime('%H:%M'))
            current += timedelta(minutes=slot_duration)

        booked_times = booked_map.get(date_str, [])
        available_slots = [s for s in all_slots if s not in booked_times]

        calendar_data.append({
            'date': date_str,
            'is_working_day': True,
            'is_past': current_date < date.today(),
            'available_slots': available_slots if current_date >= date.today() else [],
            'booked_slots': booked_times,
            'total_slots': len(all_slots),
            'available_count': len(available_slots) if current_date >= date.today() else 0,
        })

    return Response({
        'doctor_id': doctor_id,
        'doctor_name': doctor.full_name,
        'year': year,
        'month': month,
        'calendar': calendar_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_reminders(request):
    """Get upcoming appointments that need reminders (24h and 1h)"""
    user = request.user
    now = timezone.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    if user.role == 'patient':
        base_qs = Appointment.objects.filter(
            patient=user,
            status__in=['pending', 'confirmed']
        ).select_related('doctor', 'doctor__profile')
    elif user.role == 'doctor':
        base_qs = Appointment.objects.filter(
            doctor=user,
            status__in=['pending', 'confirmed']
        ).select_related('patient', 'patient__profile')
    else:
        return Response({'error': 'Permission denied'}, status=403)

    # Appointments in next 24 hours
    next_24h = base_qs.filter(
        appointment_date__in=[today, tomorrow]
    ).order_by('appointment_date', 'appointment_time')

    reminders = []
    for appt in next_24h:
        appt_datetime = datetime.combine(appt.appointment_date, appt.appointment_time)
        appt_datetime = timezone.make_aware(appt_datetime)
        hours_until = (appt_datetime - now).total_seconds() / 3600

        if hours_until < 0:
            continue

        if hours_until <= 1:
            urgency = 'now'
            message = 'Your appointment is in less than 1 hour!'
        elif hours_until <= 3:
            urgency = 'soon'
            message = f'Your appointment is in {int(hours_until)} hours.'
        elif hours_until <= 24:
            urgency = 'tomorrow'
            message = 'Your appointment is tomorrow.'
        else:
            continue

        if user.role == 'patient':
            other_person = appt.doctor.full_name
            other_label = 'doctor'
        else:
            other_person = appt.patient.full_name
            other_label = 'patient'

        reminders.append({
            'appointment_id': appt.id,
            'urgency': urgency,
            'message': message,
            'hours_until': round(hours_until, 1),
            other_label: other_person,
            'appointment_date': str(appt.appointment_date),
            'appointment_time': str(appt.appointment_time),
            'status': appt.status,
            'reason': appt.reason,
        })

    return Response({
        'reminders': reminders,
        'count': len(reminders),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def appointment_history(request):
    """Get paginated appointment history with stats"""
    user = request.user

    if user.role == 'patient':
        queryset = Appointment.objects.filter(
            patient=user
        ).select_related('doctor', 'doctor__profile').order_by('-appointment_date', '-appointment_time')
    elif user.role == 'doctor':
        queryset = Appointment.objects.filter(
            doctor=user
        ).select_related('patient', 'patient__profile').order_by('-appointment_date', '-appointment_time')
    else:
        queryset = Appointment.objects.all().select_related(
            'patient', 'doctor'
        ).order_by('-appointment_date', '-appointment_time')

    # Filters
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    date_from = request.query_params.get('date_from')
    if date_from:
        queryset = queryset.filter(appointment_date__gte=date_from)

    date_to = request.query_params.get('date_to')
    if date_to:
        queryset = queryset.filter(appointment_date__lte=date_to)

    # Stats
    total = queryset.count()
    completed = queryset.filter(status='completed').count()
    cancelled = queryset.filter(status='cancelled').count()
    upcoming = queryset.filter(
        status__in=['pending', 'confirmed'],
        appointment_date__gte=date.today()
    ).count()

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    start = (page - 1) * page_size
    end = start + page_size
    paginated = queryset[start:end]

    data = []
    for a in paginated:
        entry = {
            'id': a.id,
            'appointment_date': str(a.appointment_date),
            'appointment_time': str(a.appointment_time),
            'duration_minutes': a.duration_minutes,
            'status': a.status,
            'reason': a.reason,
            'notes': a.notes,
            'doctor_notes': a.doctor_notes,
            'created_at': a.created_at.isoformat(),
        }
        if user.role == 'patient':
            entry['doctor'] = {
                'id': a.doctor.id,
                'full_name': a.doctor.full_name,
                'avatar': a.doctor.avatar,
                'specialization': getattr(a.doctor.profile, 'specialization', None) if hasattr(a.doctor, 'profile') else None,
            }
        else:
            entry['patient'] = {
                'id': a.patient.id,
                'full_name': a.patient.full_name,
                'avatar': a.patient.avatar,
            }
        data.append(entry)

    return Response({
        'stats': {
            'total': total,
            'completed': completed,
            'cancelled': cancelled,
            'upcoming': upcoming,
        },
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'appointments': data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reschedule_appointment(request, appointment_id):
    """Reschedule an existing appointment to a new date/time"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=404)

    if request.user not in [appointment.patient, appointment.doctor]:
        return Response({'error': 'Permission denied'}, status=403)

    if appointment.status in ['completed', 'cancelled']:
        return Response({'error': 'Cannot reschedule a completed or cancelled appointment'}, status=400)

    new_date = request.data.get('appointment_date')
    new_time = request.data.get('appointment_time')

    if not new_date or not new_time:
        return Response({'error': 'appointment_date and appointment_time are required'}, status=400)

    # Check new slot is not taken
    if Appointment.objects.filter(
        doctor=appointment.doctor,
        appointment_date=new_date,
        appointment_time=new_time,
        status__in=['pending', 'confirmed']
    ).exclude(id=appointment_id).exists():
        return Response({'error': 'This time slot is already booked'}, status=400)

    # Check not in the past
    try:
        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
        if new_date_obj < date.today():
            return Response({'error': 'Cannot reschedule to a past date'}, status=400)
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    old_date = appointment.appointment_date
    old_time = appointment.appointment_time

    appointment.appointment_date = new_date
    appointment.appointment_time = new_time
    appointment.status = 'pending'
    appointment.save()

    # Notify the other party
    if request.user == appointment.patient:
        recipient = appointment.doctor
        msg = f'Patient {appointment.patient.full_name} rescheduled their appointment.'
    else:
        recipient = appointment.patient
        msg = f'Dr. {appointment.doctor.full_name} rescheduled your appointment.'

    create_notification(
        recipient=recipient,
        sender=request.user,
        notification_type='appointment_reminder',
        title='Appointment Rescheduled',
        message=f'{msg} New time: {new_date} at {new_time}.',
        link=f'/appointments/{appointment.id}/',
    )

    return Response({
        'message': 'Appointment rescheduled successfully',
        'old_date': str(old_date),
        'old_time': str(old_time),
        'new_date': new_date,
        'new_time': new_time,
        'status': appointment.status,
    })


# AI DIALOGUE MANAGEMENT

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_new_ai_dialogue(request):
    """Start a fresh AI dialogue (clears history)"""
    title = request.data.get('title', '')
    dialogue = ai_service.start_new_dialogue(request.user, title or None)
    return Response({
        'message': 'New dialogue started',
        'dialogue_id': dialogue.id,
        'title': dialogue.title,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_ai_dialogue(request, dialogue_id):
    """Close a specific AI dialogue"""
    success = ai_service.close_dialogue(request.user, dialogue_id)
    if success:
        return Response({'message': 'Dialogue closed'})
    return Response({'error': 'Dialogue not found'}, status=404)


# ============================================
# DOCTOR AVAILABILITY & BOOKING SLOTS
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_available_slots(request, doctor_id):
    """Get available time slots for a doctor on a specific date"""
    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'date parameter is required (YYYY-MM-DD)'}, status=400)

    try:
        requested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    if requested_date < date.today():
        return Response({'error': 'Cannot check slots for past dates'}, status=400)

    try:
        doctor = User.objects.get(id=doctor_id, role='doctor', is_active=True)
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    # Get doctor's schedule for that day of week
    day_of_week = requested_date.weekday()
    try:
        schedule = DoctorSchedule.objects.get(
            doctor=doctor, day_of_week=day_of_week, is_available=True
        )
    except DoctorSchedule.DoesNotExist:
        return Response({
            'doctor_id': doctor_id,
            'date': date_str,
            'is_working_day': False,
            'available_slots': [],
            'message': 'Doctor does not work on this day',
        })

    # Generate all time slots
    slot_duration = schedule.slot_duration_minutes
    all_slots = []
    current = datetime.combine(requested_date, schedule.start_time)
    end = datetime.combine(requested_date, schedule.end_time)
    while current + timedelta(minutes=slot_duration) <= end:
        all_slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=slot_duration)

    # Get already booked slots
    booked_times = set(
        Appointment.objects.filter(
            doctor=doctor,
            appointment_date=requested_date,
            status__in=['pending', 'confirmed']
        ).values_list('appointment_time', flat=True)
    )
    booked_str = {t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)[:5] for t in booked_times}

    # Build slot list with availability
    slots = []
    now = timezone.now()
    for slot_time in all_slots:
        slot_dt = datetime.combine(requested_date, datetime.strptime(slot_time, '%H:%M').time())
        slot_dt_aware = timezone.make_aware(slot_dt)
        is_past = slot_dt_aware <= now
        is_booked = slot_time in booked_str

        slots.append({
            'time': slot_time,
            'is_available': not is_booked and not is_past,
            'is_booked': is_booked,
            'is_past': is_past,
        })

    available_count = sum(1 for s in slots if s['is_available'])

    return Response({
        'doctor_id': doctor_id,
        'doctor_name': doctor.full_name,
        'date': date_str,
        'day_of_week': requested_date.strftime('%A'),
        'is_working_day': True,
        'working_hours': {
            'start': schedule.start_time.strftime('%H:%M'),
            'end': schedule.end_time.strftime('%H:%M'),
            'slot_duration_minutes': slot_duration,
        },
        'total_slots': len(slots),
        'available_count': available_count,
        'booked_count': len(booked_str),
        'slots': slots,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doctor_available_dates(request, doctor_id):
    """Get available dates for a doctor in the next N days"""
    days_ahead = int(request.query_params.get('days', 30))
    days_ahead = min(days_ahead, 90)  # Max 90 days

    try:
        doctor = User.objects.get(id=doctor_id, role='doctor', is_active=True)
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    schedules = DoctorSchedule.objects.filter(doctor=doctor, is_available=True)
    working_days = {s.day_of_week for s in schedules}

    if not working_days:
        return Response({
            'doctor_id': doctor_id,
            'available_dates': [],
            'message': 'Doctor has no schedule set up',
        })

    # Get all booked dates in range
    start_date = date.today()
    end_date = start_date + timedelta(days=days_ahead)
    booked = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__range=[start_date, end_date],
        status__in=['pending', 'confirmed']
    ).values('appointment_date').annotate(
        booked_count=models.Count('id')
    )
    booked_map = {str(b['appointment_date']): b['booked_count'] for b in booked}

    # Build available dates
    available_dates = []
    for i in range(days_ahead):
        check_date = start_date + timedelta(days=i)
        if check_date.weekday() not in working_days:
            continue

        schedule = schedules.filter(day_of_week=check_date.weekday()).first()
        if not schedule:
            continue

        # Calculate total slots
        total_slots = 0
        current = datetime.combine(check_date, schedule.start_time)
        end = datetime.combine(check_date, schedule.end_time)
        while current + timedelta(minutes=schedule.slot_duration_minutes) <= end:
            total_slots += 1
            current += timedelta(minutes=schedule.slot_duration_minutes)

        date_str = str(check_date)
        booked_count = booked_map.get(date_str, 0)
        available = total_slots - booked_count

        if available > 0:
            available_dates.append({
                'date': date_str,
                'day_of_week': check_date.strftime('%A'),
                'available_slots': available,
                'total_slots': total_slots,
            })

    return Response({
        'doctor_id': doctor_id,
        'doctor_name': doctor.full_name,
        'days_checked': days_ahead,
        'available_dates': available_dates,
        'total_available_days': len(available_dates),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_available_slot(request, doctor_id):
    """Get the next available appointment slot for a doctor"""
    try:
        doctor = User.objects.get(id=doctor_id, role='doctor', is_active=True)
    except User.DoesNotExist:
        return Response({'error': 'Doctor not found'}, status=404)

    schedules = DoctorSchedule.objects.filter(doctor=doctor, is_available=True)
    working_days = {s.day_of_week: s for s in schedules}

    now = timezone.now()

    for i in range(60):  # Check next 60 days
        check_date = date.today() + timedelta(days=i)
        if check_date.weekday() not in working_days:
            continue

        schedule = working_days[check_date.weekday()]
        current = datetime.combine(check_date, schedule.start_time)
        end = datetime.combine(check_date, schedule.end_time)

        booked_times = set(
            Appointment.objects.filter(
                doctor=doctor,
                appointment_date=check_date,
                status__in=['pending', 'confirmed']
            ).values_list('appointment_time', flat=True)
        )
        booked_str = {t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)[:5] for t in booked_times}

        while current + timedelta(minutes=schedule.slot_duration_minutes) <= end:
            slot_time = current.strftime('%H:%M')
            slot_aware = timezone.make_aware(current)
            if slot_time not in booked_str and slot_aware > now:
                return Response({
                    'doctor_id': doctor_id,
                    'doctor_name': doctor.full_name,
                    'next_available_date': str(check_date),
                    'next_available_time': slot_time,
                    'day_of_week': check_date.strftime('%A'),
                })
            current += timedelta(minutes=schedule.slot_duration_minutes)

    return Response({
        'doctor_id': doctor_id,
        'message': 'No available slots in the next 60 days',
        'next_available_date': None,
    })

# ============================================
# SMS NOTIFICATIONS
# ============================================

def send_sms(phone_number, message):
    """Send SMS via Twilio"""
    if not settings.SMS_ENABLED:
        print(f"[SMS disabled] To: {phone_number} | Message: {message}")
        return False

    if not phone_number:
        return False

    try:
        from twilio.rest import Client
        client_twilio = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client_twilio.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number,
        )
        return True
    except Exception as e:
        print(f"SMS sending failed: {e}")
        return False


def send_appointment_sms(appointment, event='booked'):
    """Send SMS for appointment events"""
    if event == 'booked':
        patient_msg = (
            f"Healzy: Ваша запись подтверждена!\n"
            f"Врач: Dr. {appointment.doctor.full_name}\n"
            f"Дата: {appointment.appointment_date} в {appointment.appointment_time}\n"
            f"healzy.uz"
        )
        doctor_msg = (
            f"Healzy: Новая запись!\n"
            f"Пациент: {appointment.patient.full_name}\n"
            f"Дата: {appointment.appointment_date} в {appointment.appointment_time}\n"
            f"healzy.uz"
        )
    elif event == 'cancelled':
        patient_msg = (
            f"Healzy: Ваша запись отменена.\n"
            f"Врач: Dr. {appointment.doctor.full_name}\n"
            f"Дата: {appointment.appointment_date} в {appointment.appointment_time}\n"
            f"Для записи снова: healzy.uz"
        )
        doctor_msg = (
            f"Healzy: Запись отменена.\n"
            f"Пациент: {appointment.patient.full_name}\n"
            f"Дата: {appointment.appointment_date} в {appointment.appointment_time}"
        )
    elif event == 'reminder':
        patient_msg = (
            f"Healzy: Напоминание!\n"
            f"Завтра у вас запись к Dr. {appointment.doctor.full_name}\n"
            f"Время: {appointment.appointment_time}\n"
            f"healzy.uz"
        )
        doctor_msg = (
            f"Healzy: Напоминание!\n"
            f"Завтра: {appointment.patient.full_name}\n"
            f"Время: {appointment.appointment_time}"
        )
    elif event == 'rescheduled':
        patient_msg = (
            f"Healzy: Запись перенесена.\n"
            f"Врач: Dr. {appointment.doctor.full_name}\n"
            f"Новая дата: {appointment.appointment_date} в {appointment.appointment_time}\n"
            f"healzy.uz"
        )
        doctor_msg = (
            f"Healzy: Запись перенесена.\n"
            f"Пациент: {appointment.patient.full_name}\n"
            f"Новая дата: {appointment.appointment_date} в {appointment.appointment_time}"
        )
    else:
        return

    patient_phone = getattr(appointment.patient, 'phone_number', None)
    doctor_phone = getattr(appointment.doctor, 'phone_number', None)

    if patient_phone:
        send_sms(patient_phone, patient_msg)
    if doctor_phone:
        send_sms(doctor_phone, doctor_msg)


def send_doctor_approval_sms(doctor, approved=True):
    """Send SMS when doctor application is approved or rejected"""
    phone = getattr(doctor, 'phone_number', None)
    if not phone:
        return

    if approved:
        msg = (
            f"Healzy: Поздравляем, Dr. {doctor.full_name}!\n"
            f"Ваш профиль врача одобрен.\n"
            f"Войдите на healzy.uz чтобы начать принимать пациентов."
        )
    else:
        msg = (
            f"Healzy: Dr. {doctor.full_name},\n"
            f"К сожалению, ваша заявка не была одобрена.\n"
            f"Свяжитесь с нами для уточнения деталей."
        )
    send_sms(phone, msg)


def send_welcome_sms(user):
    """Send welcome SMS when user registers"""
    phone = getattr(user, 'phone_number', None)
    if not phone:
        return

    if user.role == 'doctor':
        msg = (
            f"Healzy: Добро пожаловать, Dr. {user.full_name}!\n"
            f"Ваша заявка на рассмотрении. Мы уведомим вас об одобрении.\n"
            f"healzy.uz"
        )
    else:
        msg = (
            f"Healzy: Добро пожаловать, {user.full_name}!\n"
            f"Ваш аккаунт создан. Записывайтесь к врачам онлайн.\n"
            f"healzy.uz"
        )
    send_sms(phone, msg)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_sms(request):
    """Admin endpoint to test SMS sending"""
    if request.user.role != 'admin':
        return Response({'error': 'Admin access required'}, status=403)

    phone = request.data.get('phone')
    if not phone:
        return Response({'error': 'phone is required'}, status=400)

    success = send_sms(phone, 'Healzy: Тестовое SMS сообщение. Если вы получили это — SMS работает! ✅')
    if success:
        return Response({'message': f'Test SMS sent to {phone}'})
    return Response({'message': f'SMS disabled or failed. Check SMS_ENABLED in .env', 'sent': False})

# ============================================
# AI MEDICAL HISTORY SUMMARY
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_medical_summary(request, patient_id=None):
    """Generate AI-powered medical history summary for a patient"""
    user = request.user

    # Determine which patient to summarize
    if user.role == 'patient':
        target_patient = user
    elif user.role in ['doctor', 'admin']:
        if not patient_id:
            return Response({'error': 'patient_id is required for doctors/admins'}, status=400)
        try:
            target_patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)
    else:
        return Response({'error': 'Permission denied'}, status=403)

    # Gather all medical data
    medical_records = MedicalRecord.objects.filter(
        patient=target_patient
    ).select_related('doctor').order_by('-created_at')[:20]

    appointments = Appointment.objects.filter(
        patient=target_patient,
        status='completed'
    ).select_related('doctor').order_by('-appointment_date')[:10]

    vital_signs = VitalSigns.objects.filter(
        patient=target_patient
    ).order_by('-recorded_at')[:10] if hasattr(target_patient, 'vital_signs') else []

    if not medical_records.exists() and not appointments.exists():
        return Response({
            'patient_id': target_patient.id,
            'patient_name': target_patient.full_name,
            'summary': None,
            'message': 'No medical history found for this patient',
        })

    # Build context for Claude
    records_text = ""
    for r in medical_records:
        records_text += (
            f"\n- [{r.record_type.upper()}] {r.title} "
            f"(by Dr. {r.doctor.full_name}, {r.created_at.strftime('%Y-%m-%d')}): "
            f"{r.description[:300]}"
        )

    appointments_text = ""
    for a in appointments:
        appointments_text += (
            f"\n- {a.appointment_date} with Dr. {a.doctor.full_name}"
            f"{' — ' + a.doctor_notes[:200] if a.doctor_notes else ''}"
        )

    vitals_text = ""
    if vital_signs:
        latest = vital_signs[0] if vital_signs else None
        if latest:
            vitals_text = (
                f"\nLatest vitals ({latest.recorded_at.strftime('%Y-%m-%d')}): "
                f"BP: {getattr(latest, 'blood_pressure', 'N/A')}, "
                f"HR: {getattr(latest, 'heart_rate', 'N/A')} bpm, "
                f"Temp: {getattr(latest, 'temperature', 'N/A')}°C, "
                f"Weight: {getattr(latest, 'weight', 'N/A')} kg"
            )

    patient_age = ""
    if hasattr(target_patient, 'profile') and target_patient.profile:
        dob = getattr(target_patient.profile, 'date_of_birth', None)
        if dob:
            from datetime import date as date_type
            age = (date_type.today() - dob).days // 365
            patient_age = f", Age: {age}"

    prompt = f"""You are a medical AI assistant. Analyze this patient's medical history and create a comprehensive summary in Russian.

Patient: {target_patient.full_name}{patient_age}

MEDICAL RECORDS:
{records_text if records_text else 'No records available'}

COMPLETED APPOINTMENTS:
{appointments_text if appointments_text else 'No completed appointments'}

VITAL SIGNS:
{vitals_text if vitals_text else 'No vital signs recorded'}

Please provide a structured medical summary in Russian with these sections:
1. **Общая картина здоровья** — overall health status
2. **Основные диагнозы и состояния** — main diagnoses and conditions
3. **История лечения** — treatment history
4. **Текущие показатели** — current vitals if available
5. **Рекомендации** — recommendations for the patient or doctor
6. **Важные предупреждения** — any red flags or urgent concerns (if any)

Be concise, professional, and clinically accurate. Use simple language where possible."""

    try:
        from django.conf import settings as django_settings
        import anthropic
        claude_client = anthropic.Anthropic(api_key=django_settings.ANTHROPIC_API_KEY)
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        summary_text = response.content[0].text

        return Response({
            'patient_id': target_patient.id,
            'patient_name': target_patient.full_name,
            'generated_at': timezone.now().isoformat(),
            'data_points': {
                'medical_records': medical_records.count(),
                'appointments': appointments.count(),
                'has_vitals': bool(vitals_text),
            },
            'summary': summary_text,
        })

    except Exception as e:
        return Response({'error': f'AI summary generation failed: {str(e)}'}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_patient_risk_assessment(request, patient_id=None):
    """AI-powered risk assessment for a patient based on their history"""
    user = request.user

    if user.role == 'patient':
        target_patient = user
    elif user.role in ['doctor', 'admin']:
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=400)
        try:
            target_patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)
    else:
        return Response({'error': 'Permission denied'}, status=403)

    # Gather records
    medical_records = MedicalRecord.objects.filter(
        patient=target_patient
    ).order_by('-created_at')[:15]

    if not medical_records.exists():
        return Response({
            'patient_id': target_patient.id,
            'risk_level': 'unknown',
            'message': 'Insufficient medical history for risk assessment',
        })

    records_text = "\n".join([
        f"- [{r.record_type}] {r.title}: {r.description[:200]}"
        for r in medical_records
    ])

    prompt = f"""Based on this patient's medical records, provide a brief risk assessment in Russian.

Patient: {target_patient.full_name}
Medical Records:
{records_text}

Respond ONLY with a JSON object (no markdown, no extra text):
{{
  "risk_level": "low|medium|high",
  "risk_factors": ["factor1", "factor2"],
  "protective_factors": ["factor1", "factor2"],
  "immediate_concerns": ["concern1"],
  "recommended_screenings": ["screening1", "screening2"],
  "lifestyle_recommendations": ["recommendation1"],
  "summary": "2-3 sentence summary in Russian"
}}"""

    try:
        from django.conf import settings as django_settings
        import anthropic
        claude_client = anthropic.Anthropic(api_key=django_settings.ANTHROPIC_API_KEY)
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        # Clean JSON
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        assessment = json.loads(raw)

        return Response({
            'patient_id': target_patient.id,
            'patient_name': target_patient.full_name,
            'generated_at': timezone.now().isoformat(),
            'assessment': assessment,
        })

    except json.JSONDecodeError:
        return Response({'error': 'Failed to parse AI response'}, status=500)
    except Exception as e:
        return Response({'error': f'Risk assessment failed: {str(e)}'}, status=500)
    
# VIDEO CALL / TELEMEDICINE

from .models import VideoCall, VideoCallSignal

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_video_call(request):
    """Create a new video call room"""
    user = request.user
    other_user_id = request.data.get('user_id')
    appointment_id = request.data.get('appointment_id')

    if not other_user_id:
        return Response({'error': 'user_id is required'}, status=400)

    try:
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    # Determine doctor and patient
    if user.role == 'doctor' and other_user.role == 'patient':
        doctor, patient = user, other_user
    elif user.role == 'patient' and other_user.role == 'doctor':
        doctor, patient = other_user, user
    else:
        return Response({'error': 'Video call must be between a doctor and a patient'}, status=400)

    # Get appointment if provided
    appointment = None
    if appointment_id:
        try:
            appointment = Appointment.objects.get(
                id=appointment_id, doctor=doctor, patient=patient
            )
        except Appointment.DoesNotExist:
            pass

    # Generate unique room ID
    room_id = f"healzy_{uuid.uuid4().hex[:12]}"

    # Create video call
    call = VideoCall.objects.create(
        doctor=doctor,
        patient=patient,
        appointment=appointment,
        room_id=room_id,
        status='waiting',
    )

    # Notify the other user
    create_notification(
        recipient=other_user,
        sender=user,
        notification_type='general',
        title='Incoming Video Call',
        message=f'{user.full_name} is calling you. Join the video call now.',
        link=f'/video-call/{room_id}/',
    )

    # Send SMS notification
    call_msg = f"Healzy: {user.full_name} начинает видеозвонок. Присоединитесь: healzy.uz/video-call/{room_id}/"
    other_phone = getattr(other_user, 'phone_number', None)
    if other_phone:
        send_sms(other_phone, call_msg)

    return Response({
        'room_id': room_id,
        'call_id': call.id,
        'doctor': {'id': doctor.id, 'full_name': doctor.full_name, 'avatar': doctor.avatar},
        'patient': {'id': patient.id, 'full_name': patient.full_name, 'avatar': patient.avatar},
        'status': call.status,
        'created_at': call.created_at.isoformat(),
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_video_call(request, room_id):
    """Get video call details by room ID"""
    try:
        call = VideoCall.objects.get(room_id=room_id)
    except VideoCall.DoesNotExist:
        return Response({'error': 'Video call room not found'}, status=404)

    if request.user not in [call.doctor, call.patient]:
        return Response({'error': 'Permission denied'}, status=403)

    return Response({
        'room_id': call.room_id,
        'call_id': call.id,
        'status': call.status,
        'doctor': {'id': call.doctor.id, 'full_name': call.doctor.full_name, 'avatar': call.doctor.avatar},
        'patient': {'id': call.patient.id, 'full_name': call.patient.full_name, 'avatar': call.patient.avatar},
        'started_at': call.started_at.isoformat() if call.started_at else None,
        'ended_at': call.ended_at.isoformat() if call.ended_at else None,
        'duration_minutes': call.duration_minutes,
        'created_at': call.created_at.isoformat(),
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_video_call_status(request, room_id):
    """Update video call status (active, ended, missed)"""
    try:
        call = VideoCall.objects.get(room_id=room_id)
    except VideoCall.DoesNotExist:
        return Response({'error': 'Video call room not found'}, status=404)

    if request.user not in [call.doctor, call.patient]:
        return Response({'error': 'Permission denied'}, status=403)

    new_status = request.data.get('status')
    if new_status not in ['active', 'ended', 'missed']:
        return Response({'error': 'status must be active, ended or missed'}, status=400)

    if new_status == 'active' and call.status == 'waiting':
        call.started_at = timezone.now()

    if new_status == 'ended' and call.started_at:
        call.ended_at = timezone.now()
        call.duration_seconds = int((call.ended_at - call.started_at).total_seconds())

    call.status = new_status
    call.save()

    return Response({
        'room_id': room_id,
        'status': call.status,
        'duration_seconds': call.duration_seconds,
        'duration_minutes': call.duration_minutes,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_webrtc_signal(request, room_id):
    """Send WebRTC signaling data (offer, answer, ICE candidate)"""
    try:
        call = VideoCall.objects.get(room_id=room_id)
    except VideoCall.DoesNotExist:
        return Response({'error': 'Video call room not found'}, status=404)

    if request.user not in [call.doctor, call.patient]:
        return Response({'error': 'Permission denied'}, status=403)

    signal_type = request.data.get('signal_type')
    payload = request.data.get('payload')

    if signal_type not in ['offer', 'answer', 'ice_candidate', 'end_call']:
        return Response({'error': 'Invalid signal_type'}, status=400)

    if not payload:
        return Response({'error': 'payload is required'}, status=400)

    signal = VideoCallSignal.objects.create(
        call=call,
        sender=request.user,
        signal_type=signal_type,
        payload=payload,
    )

    return Response({
        'signal_id': signal.id,
        'signal_type': signal_type,
        'created_at': signal.created_at.isoformat(),
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_webrtc_signals(request, room_id):
    """Poll for new WebRTC signals (for the other participant)"""
    try:
        call = VideoCall.objects.get(room_id=room_id)
    except VideoCall.DoesNotExist:
        return Response({'error': 'Video call room not found'}, status=404)

    if request.user not in [call.doctor, call.patient]:
        return Response({'error': 'Permission denied'}, status=403)

    # Get signals sent by the OTHER user (not self)
    after_id = request.query_params.get('after_id', 0)
    signals = VideoCallSignal.objects.filter(
        call=call,
        id__gt=after_id,
    ).exclude(sender=request.user).order_by('created_at')

    return Response({
        'signals': [{
            'id': s.id,
            'signal_type': s.signal_type,
            'payload': s.payload,
            'created_at': s.created_at.isoformat(),
        } for s in signals],
        'count': signals.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_video_calls(request):
    """Get video call history for the current user"""
    user = request.user

    if user.role == 'doctor':
        calls = VideoCall.objects.filter(doctor=user).order_by('-created_at')[:20]
    else:
        calls = VideoCall.objects.filter(patient=user).order_by('-created_at')[:20]

    data = [{
        'room_id': c.room_id,
        'call_id': c.id,
        'status': c.status,
        'doctor': {'id': c.doctor.id, 'full_name': c.doctor.full_name},
        'patient': {'id': c.patient.id, 'full_name': c.patient.full_name},
        'duration_minutes': c.duration_minutes,
        'created_at': c.created_at.isoformat(),
    } for c in calls]

    return Response({'calls': data, 'count': len(data)})

# DENTAL TOOTH HISTORY SYSTEM

from .models import DentalChart, Tooth, ToothTreatment, ToothXray

def get_or_create_dental_chart(patient):
    """Get or create a dental chart for a patient, with all 32 teeth"""
    chart, created = DentalChart.objects.get_or_create(patient=patient)
    if created:
        # Create all 32 teeth using FDI numbering
        fdi_numbers = (
            list(range(11, 19)) +  # Upper right
            list(range(21, 29)) +  # Upper left
            list(range(31, 39)) +  # Lower left
            list(range(41, 49))    # Lower right
        )
        Tooth.objects.bulk_create([
            Tooth(chart=chart, fdi_number=n, condition='healthy')
            for n in fdi_numbers
        ])
    return chart


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dental_chart(request, patient_id=None):
    """Get full dental chart for a patient"""
    user = request.user

    if user.role == 'patient':
        target_patient = user
    elif user.role in ['doctor', 'admin']:
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=400)
        try:
            target_patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)
    else:
        return Response({'error': 'Permission denied'}, status=403)

    chart = get_or_create_dental_chart(target_patient)
    teeth = Tooth.objects.filter(chart=chart).prefetch_related(
        'treatments', 'treatments__doctor', 'xrays'
    ).order_by('fdi_number')

    # Group teeth by quadrant
    quadrants = {
        'upper_right': [],  # 11-18
        'upper_left': [],   # 21-28
        'lower_left': [],   # 31-38
        'lower_right': [],  # 41-48
    }

    quadrant_map = {
        1: 'upper_right', 2: 'upper_left',
        3: 'lower_left', 4: 'lower_right'
    }

    for tooth in teeth:
        quadrant_key = quadrant_map.get(tooth.fdi_number // 10)
        if not quadrant_key:
            continue

        tooth_data = {
            'id': tooth.id,
            'fdi_number': tooth.fdi_number,
            'condition': tooth.condition,
            'quadrant': tooth.quadrant,
            'notes': tooth.notes,
            'last_updated': tooth.last_updated.isoformat(),
            'last_updated_by': tooth.last_updated_by.full_name if tooth.last_updated_by else None,
            'treatment_count': tooth.treatments.count(),
            'xray_count': tooth.xrays.count(),
            'latest_treatment': None,
        }

        latest = tooth.treatments.first()
        if latest:
            tooth_data['latest_treatment'] = {
                'treatment_type': latest.treatment_type,
                'treatment_date': str(latest.treatment_date),
                'doctor': latest.doctor.full_name if latest.doctor else None,
            }

        quadrants[quadrant_key].append(tooth_data)

    # Overall stats
    condition_summary = {}
    for tooth in teeth:
        condition_summary[tooth.condition] = condition_summary.get(tooth.condition, 0) + 1

    return Response({
        'chart_id': chart.id,
        'patient_id': target_patient.id,
        'patient_name': target_patient.full_name,
        'created_at': chart.created_at.isoformat(),
        'updated_at': chart.updated_at.isoformat(),
        'notes': chart.notes,
        'condition_summary': condition_summary,
        'total_teeth': teeth.count(),
        'quadrants': quadrants,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tooth_detail(request, patient_id, fdi_number):
    """Get full history of a single tooth"""
    user = request.user

    if user.role == 'patient':
        if str(user.id) != str(patient_id):
            return Response({'error': 'Permission denied'}, status=403)
        target_patient = user
    elif user.role in ['doctor', 'admin']:
        try:
            target_patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)
    else:
        return Response({'error': 'Permission denied'}, status=403)

    chart = get_or_create_dental_chart(target_patient)

    try:
        tooth = Tooth.objects.get(chart=chart, fdi_number=fdi_number)
    except Tooth.DoesNotExist:
        return Response({'error': f'Tooth {fdi_number} not found'}, status=404)

    treatments = ToothTreatment.objects.filter(tooth=tooth).select_related('doctor').order_by('-treatment_date')
    xrays = ToothXray.objects.filter(tooth=tooth).select_related('uploaded_by').order_by('-taken_at')

    return Response({
        'tooth_id': tooth.id,
        'fdi_number': tooth.fdi_number,
        'quadrant': tooth.quadrant,
        'condition': tooth.condition,
        'notes': tooth.notes,
        'last_updated': tooth.last_updated.isoformat(),
        'last_updated_by': tooth.last_updated_by.full_name if tooth.last_updated_by else None,
        'patient': {
            'id': target_patient.id,
            'full_name': target_patient.full_name,
        },
        'treatments': [{
            'id': t.id,
            'treatment_type': t.treatment_type,
            'treatment_date': str(t.treatment_date),
            'doctor': t.doctor.full_name if t.doctor else None,
            'doctor_id': t.doctor.id if t.doctor else None,
            'description': t.description,
            'materials_used': t.materials_used,
            'cost': str(t.cost) if t.cost else None,
            'next_visit_recommended': str(t.next_visit_recommended) if t.next_visit_recommended else None,
            'created_at': t.created_at.isoformat(),
        } for t in treatments],
        'xrays': [{
            'id': x.id,
            'file_url': request.build_absolute_uri(x.file.url) if x.file else None,
            'file_type': x.file_type,
            'notes': x.notes,
            'taken_at': str(x.taken_at),
            'uploaded_by': x.uploaded_by.full_name if x.uploaded_by else None,
            'treatment_id': x.treatment.id if x.treatment else None,
        } for x in xrays],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_tooth_treatment(request, patient_id, fdi_number):
    """Add a treatment record to a specific tooth (doctors only)"""
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Only doctors can add treatment records'}, status=403)

    try:
        target_patient = User.objects.get(id=patient_id, role='patient')
    except User.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=404)

    chart = get_or_create_dental_chart(target_patient)

    try:
        tooth = Tooth.objects.get(chart=chart, fdi_number=fdi_number)
    except Tooth.DoesNotExist:
        return Response({'error': f'Tooth {fdi_number} not found'}, status=404)

    treatment_type = request.data.get('treatment_type')
    treatment_date = request.data.get('treatment_date')

    if not treatment_type or not treatment_date:
        return Response({'error': 'treatment_type and treatment_date are required'}, status=400)

    valid_treatments = [t[0] for t in ToothTreatment.TREATMENT_CHOICES]
    if treatment_type not in valid_treatments:
        return Response({
            'error': f'Invalid treatment_type. Valid options: {valid_treatments}'
        }, status=400)

    treatment = ToothTreatment.objects.create(
        tooth=tooth,
        doctor=request.user,
        treatment_type=treatment_type,
        treatment_date=treatment_date,
        description=request.data.get('description', ''),
        materials_used=request.data.get('materials_used', ''),
        cost=request.data.get('cost'),
        next_visit_recommended=request.data.get('next_visit_recommended'),
    )

    # Update tooth condition based on treatment
    condition_map = {
        'filling': 'filled',
        'composite_filling': 'filled',
        'amalgam_filling': 'filled',
        'crown': 'crowned',
        'root_canal': 'root_canal',
        'extraction': 'extracted',
        'implant': 'implant',
        'implant_crown': 'implant',
        'bridge': 'bridge',
        'veneer': 'veneer',
    }
    new_condition = condition_map.get(treatment_type)
    if new_condition:
        tooth.condition = new_condition

    tooth.notes = request.data.get('tooth_notes', tooth.notes)
    tooth.last_updated_by = request.user
    tooth.save()

    # Notify patient
    create_notification(
        recipient=target_patient,
        sender=request.user,
        notification_type='general',
        title='Dental Record Updated',
        message=f'Dr. {request.user.full_name} added a {treatment_type} record for tooth {fdi_number}.',
        link='/dental-chart/',
    )

    return Response({
        'message': 'Treatment added successfully',
        'treatment_id': treatment.id,
        'tooth_fdi': fdi_number,
        'new_condition': tooth.condition,
        'treatment_type': treatment_type,
        'treatment_date': str(treatment_date),
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_tooth_condition(request, patient_id, fdi_number):
    """Update the condition of a tooth (doctors only)"""
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Only doctors can update tooth conditions'}, status=403)

    try:
        target_patient = User.objects.get(id=patient_id, role='patient')
    except User.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=404)

    chart = get_or_create_dental_chart(target_patient)

    try:
        tooth = Tooth.objects.get(chart=chart, fdi_number=fdi_number)
    except Tooth.DoesNotExist:
        return Response({'error': f'Tooth {fdi_number} not found'}, status=404)

    valid_conditions = [c[0] for c in Tooth.CONDITION_CHOICES]
    new_condition = request.data.get('condition')

    if new_condition and new_condition not in valid_conditions:
        return Response({
            'error': f'Invalid condition. Valid options: {valid_conditions}'
        }, status=400)

    if new_condition:
        tooth.condition = new_condition
    if 'notes' in request.data:
        tooth.notes = request.data['notes']

    tooth.last_updated_by = request.user
    tooth.save()

    return Response({
        'message': 'Tooth updated successfully',
        'fdi_number': fdi_number,
        'condition': tooth.condition,
        'notes': tooth.notes,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_tooth_xray(request, patient_id, fdi_number):
    """Upload an X-ray or photo for a specific tooth (doctors only)"""
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Only doctors can upload X-rays'}, status=403)

    try:
        target_patient = User.objects.get(id=patient_id, role='patient')
    except User.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=404)

    chart = get_or_create_dental_chart(target_patient)

    try:
        tooth = Tooth.objects.get(chart=chart, fdi_number=fdi_number)
    except Tooth.DoesNotExist:
        return Response({'error': f'Tooth {fdi_number} not found'}, status=404)

    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)

    file = request.FILES['file']
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
    if file.content_type not in allowed_types:
        return Response({'error': 'Only JPEG, PNG, WebP and PDF files are allowed'}, status=400)

    if file.size > 20 * 1024 * 1024:
        return Response({'error': 'File size must be under 20MB'}, status=400)

    taken_at = request.data.get('taken_at', str(date.today()))
    treatment_id = request.data.get('treatment_id')
    treatment = None
    if treatment_id:
        try:
            treatment = ToothTreatment.objects.get(id=treatment_id, tooth=tooth)
        except ToothTreatment.DoesNotExist:
            pass

    xray = ToothXray.objects.create(
        tooth=tooth,
        treatment=treatment,
        uploaded_by=request.user,
        file=file,
        file_type=request.data.get('file_type', 'xray'),
        notes=request.data.get('notes', ''),
        taken_at=taken_at,
    )

    return Response({
        'message': 'X-ray uploaded successfully',
        'xray_id': xray.id,
        'file_url': request.build_absolute_uri(xray.file.url),
        'tooth_fdi': fdi_number,
        'taken_at': str(taken_at),
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_tooth_treatment(request, treatment_id):
    """Delete a treatment record (doctors/admins only)"""
    if request.user.role not in ['doctor', 'admin']:
        return Response({'error': 'Only doctors can delete treatment records'}, status=403)

    try:
        treatment = ToothTreatment.objects.get(id=treatment_id)
    except ToothTreatment.DoesNotExist:
        return Response({'error': 'Treatment not found'}, status=404)

    if treatment.doctor != request.user and request.user.role != 'admin':
        return Response({'error': 'You can only delete your own treatment records'}, status=403)

    fdi = treatment.tooth.fdi_number
    treatment.delete()

    return Response({'message': f'Treatment record for tooth {fdi} deleted successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_dental_summary(request, patient_id=None):
    """Get AI-powered dental summary for a patient"""
    user = request.user

    if user.role == 'patient':
        target_patient = user
    elif user.role in ['doctor', 'admin']:
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=400)
        try:
            target_patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=404)
    else:
        return Response({'error': 'Permission denied'}, status=403)

    chart = get_or_create_dental_chart(target_patient)
    teeth = Tooth.objects.filter(chart=chart).prefetch_related('treatments')

    # Build dental history text
    problem_teeth = []
    all_treatments = []

    for tooth in teeth:
        if tooth.condition != 'healthy':
            problem_teeth.append(f"Tooth {tooth.fdi_number} ({tooth.quadrant}): {tooth.condition}")
        for t in tooth.treatments.all():
            all_treatments.append(
                f"- Tooth {tooth.fdi_number}: {t.treatment_type} on {t.treatment_date}"
                f" by Dr. {t.doctor.full_name if t.doctor else 'Unknown'}"
            )

    if not problem_teeth and not all_treatments:
        return Response({
            'patient_name': target_patient.full_name,
            'summary': 'Нет данных о стоматологических процедурах. Зубы помечены как здоровые.',
            'problem_teeth_count': 0,
            'total_treatments': 0,
        })

    prompt = f"""Ты стоматолог-ассистент. Проанализируй историю зубов пациента и дай краткое резюме на русском языке.

Пациент: {target_patient.full_name}

Проблемные зубы:
{chr(10).join(problem_teeth) if problem_teeth else 'Нет'}

История лечения:
{chr(10).join(all_treatments[-20:]) if all_treatments else 'Нет'}

Дай структурированное резюме:
1. **Общее состояние зубов**
2. **Проведённые процедуры**
3. **Зубы требующие внимания**
4. **Рекомендации**

Будь краткой и профессиональной."""

    try:
        import anthropic
        from django.conf import settings as django_settings
        claude_client = anthropic.Anthropic(api_key=django_settings.ANTHROPIC_API_KEY)
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{'role': 'user', 'content': prompt}],
        )

        return Response({
            'patient_name': target_patient.full_name,
            'generated_at': timezone.now().isoformat(),
            'problem_teeth_count': len(problem_teeth),
            'total_treatments': len(all_treatments),
            'summary': response.content[0].text,
        })

    except Exception as e:
        return Response({'error': f'Summary generation failed: {str(e)}'}, status=500)