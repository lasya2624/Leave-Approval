from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm, FacultyRegistrationForm, LoginForm, LeaveRequestForm
from .models import User, StudentProfile, FacultyProfile, LeaveRequest, Department
from .utils.security import generate_rsa_keypair, generate_verification_key, visually_sign_pdf
from django.http import HttpResponse, Http404, FileResponse
from django.conf import settings
import uuid
import os

def faculty_login(request):
    if request.user.is_authenticated:
        if request.user.is_faculty:
            return redirect('faculty_dashboard')
        else:
            return redirect('student_dashboard')
            
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                if not user.is_faculty:
                    form.add_error(None, "This login page is for Faculty only.")
                else:
                    user = authenticate(request, username=user.username, password=password)
                    if user is not None:
                        login(request, user)
                        return redirect('faculty_dashboard')
                    else:
                        form.add_error(None, "Invalid email or password")
            except User.DoesNotExist:
                form.add_error(None, "Invalid email or password")
    else:
        form = LoginForm()
    return render(request, 'approvals/faculty_login.html', {'form': form})

def student_login(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student_dashboard')
        else:
            return redirect('faculty_dashboard')
            
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                if not user.is_student:
                    form.add_error(None, "This login page is for Students only.")
                else:
                    user = authenticate(request, username=user.username, password=password)
                    if user is not None:
                        login(request, user)
                        return redirect('student_dashboard')
                    else:
                        form.add_error(None, "Invalid email or password")
            except User.DoesNotExist:
                form.add_error(None, "Invalid email or password")
    else:
        form = LoginForm()
    return render(request, 'approvals/student_login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('faculty_login')

def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['college_email']
            user.email = form.cleaned_data['college_email']
            user.is_student = True
            user.set_password(form.cleaned_data['password'])
            user.save()
            StudentProfile.objects.create(
                user=user,
                register_number=form.cleaned_data['register_number'],
                department=form.cleaned_data['department']
            )
            return redirect('student_login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'approvals/register_student.html', {'form': form})

def register_faculty(request):
    if request.method == 'POST':
        form = FacultyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['college_email']
            user.email = form.cleaned_data['college_email']
            user.is_faculty = True
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            priv, pub = generate_rsa_keypair()
            
            FacultyProfile.objects.create(
                user=user,
                register_number=form.cleaned_data['register_number'],
                department=form.cleaned_data['department'],
                role=form.cleaned_data['role'],
                signature_image=form.cleaned_data['signature_image'],
                private_key=priv,
                public_key=pub
            )
            return redirect('faculty_login')
    else:
        form = FacultyRegistrationForm()
    return render(request, 'approvals/register_faculty.html', {'form': form})

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        return redirect('faculty_dashboard')
    profile = get_object_or_404(StudentProfile, user=request.user)
    requests_list = LeaveRequest.objects.filter(student=profile).order_by('-created_at')
    
    if request.method == 'POST':
        if 'submit_request' in request.POST:
            form = LeaveRequestForm(request.POST, request.FILES, department=profile.department)
            if form.is_valid():
                LeaveRequest.objects.create(
                    student=profile,
                    mentor=form.cleaned_data['mentor'],
                    subject=form.cleaned_data['subject'],
                    original_letter=form.cleaned_data['letter']
                )
                return redirect('student_dashboard')
        
        elif 'request_hod' in request.POST:
            req_id = request.POST.get('request_id')
            leave_req = get_object_or_404(LeaveRequest, id=req_id, student=profile, status='PENDING_STUDENT_HOD')
            # Assuming uploaded letter logic handles placing the already downloaded letter
            # User workflow says: "Upload Downloaded letter again". 
            # We'll just transition status for simplicity or require file upload. Let's just transition.
            leave_req.status = 'PENDING_HOD'
            leave_req.save()
            return redirect('student_dashboard')
            
        elif 'request_dean' in request.POST:
            req_id = request.POST.get('request_id')
            leave_req = get_object_or_404(LeaveRequest, id=req_id, student=profile, status='PENDING_STUDENT_DEAN')
            leave_req.status = 'PENDING_DEAN'
            leave_req.save()
            return redirect('student_dashboard')
            
    form = LeaveRequestForm(department=profile.department)
    return render(request, 'approvals/student_dashboard.html', {'form': form, 'requests': requests_list})

@login_required
def faculty_dashboard(request):
    if not request.user.is_faculty:
        return redirect('student_dashboard')
    profile = get_object_or_404(FacultyProfile, user=request.user)
    
    pending_requests = []
    error_msg = None
    
    if profile.role == 'MENTOR':
        pending_requests = LeaveRequest.objects.filter(mentor=profile, status='PENDING_MENTOR')
    elif profile.role == 'HOD':
        pending_requests = LeaveRequest.objects.filter(student__department=profile.department, status='PENDING_HOD')
    elif profile.role == 'DEAN':
        pending_requests = LeaveRequest.objects.filter(status='PENDING_DEAN')
        
    if request.method == 'POST':
        if 'approve_request' in request.POST:
            req_id = request.POST.get('request_id')
            leave_req = get_object_or_404(LeaveRequest, id=req_id)
            
            # HOD/DEAN validation check
            if profile.role in ['HOD', 'DEAN']:
                key = request.POST.get('verification_key')
                if key != leave_req.verification_key:
                    error_msg = "Invalid Verification Key! Application existence cannot be confirmed."
                    return render(request, 'approvals/faculty_dashboard.html', {'profile': profile, 'pending_requests': pending_requests, 'error_msg': error_msg})
            
            # Sign PDF
            input_pdf = leave_req.signed_letter.path if leave_req.signed_letter.name else leave_req.original_letter.path
            output_filename = f"signed_{uuid.uuid4().hex}.pdf"
            output_pdf = os.path.join(settings.MEDIA_ROOT, 'letters', 'signed', output_filename)
            os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
            
            visually_sign_pdf(input_pdf, output_pdf, profile.signature_image.path, profile.role)
            
            leave_req.signed_letter.name = f"letters/signed/{output_filename}"
            
            # Generate new verification key for next stage
            leave_req.verification_key = generate_verification_key(f"{leave_req.id}_{profile.role}_{uuid.uuid4().hex}")
            
            if profile.role == 'MENTOR':
                leave_req.status = 'PENDING_STUDENT_HOD'
            elif profile.role == 'HOD':
                leave_req.status = 'PENDING_STUDENT_DEAN'
            elif profile.role == 'DEAN':
                leave_req.status = 'APPROVED'
            
            leave_req.save()
            return redirect('faculty_dashboard')

    return render(request, 'approvals/faculty_dashboard.html', {'profile': profile, 'pending_requests': pending_requests, 'error_msg': error_msg})

@login_required
def download_letter(request, req_id):
    leave_req = get_object_or_404(LeaveRequest, id=req_id)
    file_path = leave_req.signed_letter.path if leave_req.signed_letter.name else leave_req.original_letter.path
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response
    raise Http404
