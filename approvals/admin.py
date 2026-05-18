from django.contrib import admin
from .models import User, Department, StudentProfile, FacultyProfile, LeaveRequest

admin.site.register(User)
admin.site.register(Department)
admin.site.register(StudentProfile)
admin.site.register(FacultyProfile)
admin.site.register(LeaveRequest)
