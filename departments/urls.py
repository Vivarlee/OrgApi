from django.urls import path
from . import views

urlpatterns = [
    path('departments/', views.create_department, name='create_department'),
    path('departments/<int:id>/', views.department_detail, name='department_detail'),
    path('departments/<int:id>/employees/', views.create_employee, name='create_employee'),
]