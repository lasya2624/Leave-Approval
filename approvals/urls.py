from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_login, name='student_login'),
    path('faculty-login/', views.faculty_login, name='faculty_login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/faculty/', views.register_faculty, name='register_faculty'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('download/<int:req_id>/', views.download_letter, name='download_letter'),
]
