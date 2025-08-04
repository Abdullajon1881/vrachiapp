from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile, Region, City, District, DoctorApplication
import json


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'initials', 'is_staff', 'is_superuser', 'role']
        read_only_fields = ['id', 'is_staff', 'is_superuser', 'role']


class RegionSerializer(serializers.ModelSerializer):
    """Сериализатор для регионов"""
    class Meta:
        model = Region
        fields = ['id', 'name', 'name_uz']


class CitySerializer(serializers.ModelSerializer):
    """Сериализатор для городов"""
    region = RegionSerializer(read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'name_uz', 'region']


class DistrictSerializer(serializers.ModelSerializer):
    """Сериализатор для районов"""
    region = RegionSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    
    class Meta:
        model = District
        fields = ['id', 'name', 'name_uz', 'region', 'city']


class UserProfileReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения профиля пользователя"""
    region = RegionSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'first_name', 'last_name', 'email', 'date_of_birth', 'gender', 'phone', 
            'region', 'city', 'district', 'address', 'medical_info', 'emergency_contact',
            # Поля врача
            'specialization', 'experience', 'education', 'license_number', 'languages', 'additional_info'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    
    # Добавляем поля пользователя для редактирования
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    role = serializers.CharField(source='user.role', required=False)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'first_name', 'last_name', 'role',
            'date_of_birth', 'gender', 'phone', 
            'region', 'region_name', 'city', 'city_name', 'district', 'district_name', 'address',
            'medical_info', 'emergency_contact',
            'specialization', 'experience', 'education', 'license_number', 'languages', 'additional_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        # Проверяем, является ли пользователь врачом
        request = self.context.get('request')
        if request and request.user:
            # Если пользователь врач, блокируем редактирование полей врача
            if request.user.role == 'doctor':
                doctor_fields = ['specialization', 'experience', 'education', 'license_number', 'languages', 'additional_info']
                for field in doctor_fields:
                    if field in attrs:
                        raise serializers.ValidationError(f"Поле '{field}' не может быть изменено врачом. Обратитесь к администратору.")
        
        return attrs
    
    def update(self, instance, validated_data):
        # Обрабатываем ID для связей
        region_id = validated_data.pop('region', None)
        city_id = validated_data.pop('city', None)
        district_id = validated_data.pop('district', None)
        
        # Обновляем связи
        if region_id is not None:
            try:
                # Если передали объект, берем его ID
                if hasattr(region_id, 'id'):
                    region_id = region_id.id
                instance.region = Region.objects.get(id=region_id)
            except Region.DoesNotExist:
                instance.region = None
        
        if city_id is not None:
            try:
                # Если передали объект, берем его ID
                if hasattr(city_id, 'id'):
                    city_id = city_id.id
                instance.city = City.objects.get(id=city_id)
            except City.DoesNotExist:
                instance.city = None
        
        if district_id is not None:
            try:
                # Если передали объект, берем его ID
                if hasattr(district_id, 'id'):
                    district_id = district_id.id
                instance.district = District.objects.get(id=district_id)
            except District.DoesNotExist:
                instance.district = None
        
        # Обновляем остальные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        
        # Проверяем уникальность username
        username = attrs.get('username')
        if username:
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError("Пользователь с таким именем уже существует")
        
        # Проверяем уникальность email
        email = attrs.get('email')
        if email:
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError("Пользователь с таким email уже существует")
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Сериализатор для входа"""
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные')
            if not user.is_active:
                raise serializers.ValidationError('Аккаунт заблокирован')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Необходимо указать email и пароль')
        
        return attrs





class PasswordResetSerializer(serializers.Serializer):
    """Сериализатор для сброса пароля"""
    email = serializers.EmailField()


class GoogleAuthSerializer(serializers.Serializer):
    """Сериализатор для Google OAuth"""
    access_token = serializers.CharField()
    
    def validate_access_token(self, value):
        # Здесь будет валидация Google токена
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Сериализатор для подтверждения сброса пароля"""
    token = serializers.CharField()
    password = serializers.CharField(validators=[validate_password])
    password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs 

class DoctorApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    region_name = serializers.CharField(source='region.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    
    class Meta:
        model = DoctorApplication
        fields = [
            'id', 'user', 'first_name', 'last_name', 'full_name', 'specialization', 
            'region', 'region_name', 'city', 'city_name', 'district', 'district_name',
            'languages', 'experience', 'education', 'license_number', 'additional_info',
            'date_of_birth', 'gender', 'phone', 'address', 'medical_info', 'emergency_contact',
            'photo', 'diploma', 'license', 'status', 'status_display', 'rejection_reason', 
            'created_at', 'updated_at', 'reviewed_by', 'reviewed_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class DoctorApplicationCreateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    region = serializers.IntegerField(required=False, allow_null=True)
    city = serializers.IntegerField(required=False, allow_null=True)
    district = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = DoctorApplication
        fields = [
            'first_name', 'last_name', 'specialization', 'region', 'city', 'district',
            'languages', 'experience', 'education', 'license_number', 'additional_info',
            'date_of_birth', 'gender', 'phone', 'address', 'medical_info', 'emergency_contact',
            'photo', 'diploma', 'license'
        ]
    
    def validate_languages(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Неверный формат JSON для языков")
        return value
    
    def create(self, validated_data):
        # Обрабатываем ID для связей
        region_id = validated_data.pop('region', None)
        city_id = validated_data.pop('city', None)
        district_id = validated_data.pop('district', None)
        
        # Создаем заявку
        application = DoctorApplication.objects.create(**validated_data)
        
        # Устанавливаем связи
        if region_id:
            try:
                application.region = Region.objects.get(id=region_id)
            except Region.DoesNotExist:
                pass
        
        if city_id:
            try:
                application.city = City.objects.get(id=city_id)
            except City.DoesNotExist:
                pass
        
        if district_id:
            try:
                application.district = District.objects.get(id=district_id)
            except District.DoesNotExist:
                pass
        
        application.save()
        return application

class DoctorApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorApplication
        fields = ['status', 'rejection_reason'] 