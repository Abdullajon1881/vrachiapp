from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('google-auth/', views.GoogleAuthView.as_view(), name='google-auth'),
    
    # Email верификация
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-email-html/<str:token>/', views.verify_email_html_view, name='verify_email_html'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification_email'),
    
    # Профиль
    path('profile/', views.user_profile, name='user-profile'),
    path('check-auth/', views.check_auth, name='check-auth'),
    path('csrf/', views.get_csrf_token, name='csrf'),
    path('users/', views.list_users, name='list-users'),
    path('regions/', views.get_regions, name='regions'),
    path('cities/', views.get_cities, name='cities'),
    path('districts/', views.get_districts, name='districts'),
    path('detect-location/', views.detect_location, name='detect-location'),
    
    # Сброс пароля
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    
    # Новые маршруты для заявок врачей
    path('doctor-applications/', views.submit_doctor_application, name='submit_doctor_application'),
    path('doctor-applications/list/', views.get_doctor_applications, name='get_doctor_applications'),
    path('doctor-applications/<int:application_id>/', views.get_doctor_application_detail, name='get_doctor_application_detail'),
    path('doctor-applications/<int:application_id>/update/', views.update_doctor_application, name='update_doctor_application'),
    path('doctor-applications/<int:application_id>/update-name/', views.update_doctor_name_from_application, name='update_doctor_name_from_application'),
    path('user-applications/', views.get_user_applications, name='get_user_applications'),
    
    # Управление пользователями (только для админов)
    path('users/', views.get_all_users, name='get_all_users'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Врачи (только для пациентов)
    path('doctors/', views.get_doctors, name='get_doctors'),
    path('doctors/<int:doctor_id>/', views.get_doctor_profile, name='get_doctor_profile'),
    path('users/<int:user_id>/profile/', views.manage_user_profile, name='manage_user_profile'),
    path('current-user/', views.get_current_user_data, name='get_current_user_data'),
] 