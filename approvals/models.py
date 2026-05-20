from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    is_student = models.BooleanField(default=False)
    is_faculty = models.BooleanField(default=False)

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    register_number = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.register_number})"

class FacultyProfile(models.Model):
    ROLE_CHOICES = [
        ('MENTOR', 'Mentor'),
        ('HOD', 'HOD'),
        ('DEAN', 'Dean'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    register_number = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    signature_image = models.ImageField(upload_to='signatures/')
    public_key = models.TextField(blank=True, null=True)
    private_key = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.get_role_display()})"

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING_MENTOR', 'Pending Mentor Approval'),
        ('PENDING_STUDENT_HOD', 'Pending Student Request to HOD'),
        ('PENDING_HOD', 'Pending HOD Approval'),
        ('PENDING_STUDENT_DEAN', 'Pending Student Request to Dean'),
        ('PENDING_DEAN', 'Pending Dean Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    APPROVAL_LEVEL_CHOICES = [
        ('MENTOR', 'Mentor Only'),
        ('HOD', 'Up to HOD'),
        ('DEAN', 'Up to Dean'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='leave_requests')
    mentor = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, related_name='mentor_requests')
    subject = models.CharField(max_length=255)
    original_letter = models.FileField(upload_to='letters/original/')
    signed_letter = models.FileField(upload_to='letters/signed/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_MENTOR')
    approval_level = models.CharField(max_length=10, choices=APPROVAL_LEVEL_CHOICES, default='DEAN')
    verification_key = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.student.user.first_name}"
