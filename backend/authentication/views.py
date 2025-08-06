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


class GoogleAuthView(generics.GenericAPIView):
    """Google OAuth аутентификация"""
    permission_classes = (AllowAny,)
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
            
        except Exception as e:
            print(f"Google auth error: {e}")
            return Response({
                'error': 'Ошибка аутентификации через Google'
            }, status=status.HTTP_400_BAD_REQUEST)

    def get_google_user_info(self, access_token):
        """Получает информацию о пользователе от Google"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Google API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting Google user info: {e}")
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
def get_csrf_token(request):
    """Получение CSRF токена"""
    from django.middleware.csrf import get_token
    return Response({'csrfToken': get_token(request)})


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
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location_data = self.extract_nominatim_address(data)
        except:
            pass
        
        # Попытка 2: BigDataCloud
        if not location_data:
            try:
                response = requests.get(f'https://api.bigdatacloud.net/data/ip-geolocation?ip={ip}&key=free', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    location_data = self.extract_bigdatacloud_address(data)
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
            return Response({
                'error': 'Не удалось определить местоположение'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"Location detection error: {e}")
        return Response({
            'error': 'Ошибка определения местоположения'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_nominatim_address(self, data):
        """Извлекает адрес из ответа Nominatim"""
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
        except Exception as e:
            print(f"Error extracting Nominatim address: {e}")
            return None

    def extract_bigdatacloud_address(self, data):
        """Извлекает адрес из ответа BigDataCloud"""
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
        except Exception as e:
            print(f"Error extracting BigDataCloud address: {e}")
            return None

    def extract_locationiq_address(self, data):
        """Извлекает адрес из ответа LocationIQ"""
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
        except Exception as e:
            print(f"Error extracting LocationIQ address: {e}")
            return None


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
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
            return Response({
                'error': 'Пользователь не авторизован'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
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
            print(f"Адресные данные из заявки: region={application.region}, city={application.city}, district={application.district}")
            
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
            print(f"Профиль обновлен: {profile}")
        
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
            return render(request, 'authentication/email_verification_success.html', {
                'user': user
            })
        else:
            return render(request, 'authentication/email_verification.html', {
                'error': 'Недействительный или истекший токен верификации'
            })
    except Exception as e:
        return render(request, 'authentication/email_verification.html', {
            'error': 'Ошибка верификации email'
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

 