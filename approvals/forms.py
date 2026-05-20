from django import forms
from django.contrib.auth import authenticate
from .models import User, StudentProfile, FacultyProfile, Department
import re

class StudentRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    college_email = forms.EmailField()
    register_number = forms.CharField(max_length=50)
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'college_email']

    def clean_college_email(self):
        email = self.cleaned_data.get('college_email')
        if not re.match(r'^vtu\d{5}@veltech\.edu\.in$', email):
            raise forms.ValidationError("Email must be in the format vtuxxxxx@veltech.edu.in")
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class FacultyRegistrationForm(forms.ModelForm):
    role = forms.ChoiceField(choices=FacultyProfile.ROLE_CHOICES)
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    college_email = forms.EmailField()
    register_number = forms.CharField(max_length=50)
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    signature_image = forms.ImageField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'college_email']

    def clean_college_email(self):
        email = self.cleaned_data.get('college_email')
        if not re.match(r'^tts\d{4}@veltech\.edu\.in$', email):
            raise forms.ValidationError("Email must be in the format ttsxxxx@veltech.edu.in")
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class LeaveRequestForm(forms.Form):
    APPROVAL_LEVEL_CHOICES = [
        ('MENTOR', 'Mentor Only'),
        ('HOD', 'Up to HOD'),
        ('DEAN', 'Up to Dean'),
    ]
    mentor = forms.ModelChoiceField(queryset=FacultyProfile.objects.none())
    subject = forms.CharField(max_length=255)
    approval_level = forms.ChoiceField(choices=APPROVAL_LEVEL_CHOICES, initial='DEAN', label="Required Approval Level")
    letter = forms.FileField(help_text="Upload your signed leave letter (PDF)")

    def __init__(self, *args, **kwargs):
        department = kwargs.pop('department', None)
        super(LeaveRequestForm, self).__init__(*args, **kwargs)
        if department:
            self.fields['mentor'].queryset = FacultyProfile.objects.filter(role='MENTOR', department=department)
        else:
            self.fields['mentor'].queryset = FacultyProfile.objects.filter(role='MENTOR')

    def clean_letter(self):
        letter = self.cleaned_data.get('letter')
        if letter:
            if not letter.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed. Please upload a valid PDF document.")
        return letter
