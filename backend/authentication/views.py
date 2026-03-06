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

from .models import User, UserProfile, Region, City, District, DoctorApplication, Consultation, Message
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
            elif file_type == 'video':
                allowed = getattr(settings, 'ALLOWED_VIDEO_MIME_TYPES', ['video/mp4', 'video/webm'])
            
            if allowed and getattr(file, 'content_type', '') not in allowed:
                return Response({'error': 'Неподдерживаемый тип файла'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Используем обновленный сервис
            if file_type == 'image':
                # Асинхронная обработка изображения
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_image_message(user, file))
                finally:
                    loop.close()
                    
            elif file_type == 'audio':
                # Асинхронная обработка аудио с полным голосовым циклом
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_audio_message(user, file))
                finally:
                    loop.close()
                    
            elif file_type == 'video':
                # Пока что видео обрабатываем как изображение
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(ai_service.process_image_message(user, file))
                finally:
                    loop.close()
            else:
                return Response({
                    'error': 'Неподдерживаемый тип файла'
                }, status=status.HTTP_400_BAD_REQUEST)
                
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

from .models import Appointment, DoctorSchedule, MedicalRecord, VitalSigns, Notification 
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

# ============================================
# MEDICAL RECORDS SYSTEM
# ============================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def medical_records(request):
    """Get all medical records or create a new one"""
    if request.method == 'GET':
        user = request.user
        if user.role == 'patient':
            records = MedicalRecord.objects.filter(
                patient=user, is_visible_to_patient=True
            ).select_related('doctor', 'doctor__profile')
        elif user.role == 'doctor':
            records = MedicalRecord.objects.filter(
                doctor=user
            ).select_related('patient', 'patient__profile')
        else:
            records = MedicalRecord.objects.all().select_related('patient', 'doctor')

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
    notifs = Notification.objects.filter(recipient=request.user)[:50]
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