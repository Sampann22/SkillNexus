from django.shortcuts import render, redirect, get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from home.models import Post, CustomUser, Profile, Experience, Tag, Project, MatchRequest, Connection
from home.serializers import PostSerializer, RegisterSerializer, ProfileSerializer
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from django.contrib.auth.backends import ModelBackend
from home.forms import ExperienceForm, PostForm, ProjectForm
from django.contrib import messages
import json


def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

@login_required
def network(request):
    user = request.user

    # Get all connections for current user
    connection_entries = Connection.objects.filter(user=user).select_related('connected_to__profile')

    # Extract the connected users
    connections = [entry.connected_to for entry in connection_entries]

    return render(request, "network.html", {
        "connections": connections
    })


@login_required
def connection_profile(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    profile = Profile.objects.select_related('user') \
        .prefetch_related('experiences', 'skills') \
        .get(user=target_user)

    is_connected = Connection.objects.filter(user=request.user, connected_to=target_user).exists()
    if not is_connected:
        return redirect("network")

    user_posts = Post.objects.filter(user=target_user)
    experiences = Experience.objects.filter(profile=profile) if target_user.user_type == 'freelancer' else []
    projects = Project.objects.filter(profile=profile) if target_user.user_type == 'organization' else []
    skills = profile.skills.all()
    profile_picture = profile.profile_picture if hasattr(profile, 'profile_picture') else None

    # Fetch collaborative projects between the logged-in user and the target user
    collaborations = Project.objects.filter(
        profile__user=target_user if request.user.user_type == 'freelancer' else request.user,
        collaborators=request.user if request.user.user_type == 'freelancer' else target_user
    ).distinct()

    # Remove collaborative projects from current project list (to avoid duplicates)
    if target_user.user_type == 'organization':
        projects = projects.exclude(id__in=collaborations.values_list("id", flat=True))

    return render(request, "connection_profile.html", {
        "target_user": target_user,
        "profile_picture": profile_picture,
        "profile": profile,
        "posts": user_posts,
        "experiences": experiences,
        "projects": projects,
        "skills": skills,
        "is_connected": is_connected,
        "collaborations": collaborations
    })



@login_required
def remove_connection(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)

    # Remove both sides of the connection
    Connection.objects.filter(user=request.user, connected_to=target_user).delete()
    Connection.objects.filter(user=target_user, connected_to=request.user).delete()

    return redirect("network")


@login_required
def freelancer_matches(request):
    if request.user.user_type != 'freelancer':
        return redirect('portfolio')  # safety redirect for non-freelancers

    # Fetch freelancer's skill tags
    freelancer_skills = request.user.profile.skills.all()

    # Find projects with at least one matching required skill
    matched_projects = Project.objects.filter(
        required_skills__in=freelancer_skills
    ).exclude(profile=request.user.profile).distinct()

    enriched_projects = []
    for project in matched_projects:
        # Check if match request exists and attach status to project
        try:
            match_request = MatchRequest.objects.get(freelancer=request.user, project=project)
            project.match_status = match_request.status
        except MatchRequest.DoesNotExist:
            project.match_status = None

        enriched_projects.append(project)

    return render(request, "freelancer_matches.html", {
        "matched_projects": enriched_projects,
    })

@login_required
def send_match_request(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    if request.user.user_type != 'freelancer':
        return redirect('portfolio')

    # Prevent duplicate
    match, created = MatchRequest.objects.get_or_create(
        freelancer=request.user,
        project=project
    )

    if created:
        # success message could go here
        pass

    return redirect("freelancer_matches")

@login_required
def organization_match_requests(request):
    if request.user.user_type != 'organization':
        return redirect('portfolio')

    # Get all match requests for the organization's projects
    match_requests = MatchRequest.objects.filter(
        project__profile__user=request.user
    ).select_related('freelancer', 'project')

    match_requests = MatchRequest.objects.filter(
    project__profile__user=request.user
    ).select_related('freelancer', 'project').order_by('-created_at')  # ⬅ sort by latest first

    return render(request, 'organization_matches.html', {
        'match_requests': match_requests,
    })

@login_required
def respond_match_request(request, pk):
    match_request = get_object_or_404(MatchRequest, id=pk, project__profile__user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'accept':
            match_request.status = MatchRequest.StatusChoices.ACCEPTED
            match_request.save()

            freelancer = match_request.freelancer
            organization = match_request.project.profile.user

            # Create mutual connection if not already present
            if not Connection.objects.filter(user=freelancer, connected_to=organization).exists():
                Connection.objects.create(user=freelancer, connected_to=organization)

            if not Connection.objects.filter(user=organization, connected_to=freelancer).exists():
                Connection.objects.create(user=organization, connected_to=freelancer)

            # Add collaborator if not already added
            if match_request.freelancer not in match_request.project.collaborators.all():
                match_request.project.collaborators.add(match_request.freelancer)

        elif action == 'reject':
            match_request.status = MatchRequest.StatusChoices.REJECTED
            match_request.save()

    return redirect('organization_match_requests')


@login_required
def portfolio(request):
    user = request.user
    profile, created = Profile.objects.select_related('user') \
        .prefetch_related('experiences', 'skills') \
        .get_or_create(user=user)

    experiences = profile.experiences.all()
    skills_qs = profile.skills.all()
    skill_names = [skill.name for skill in skills_qs]
    projects = Project.objects.filter(profile=profile)
    user_posts = Post.objects.filter(user=user)

    # Predefined skill tags
    skills_list = [
        "Python", "JavaScript", "Django", "React", "Machine Learning",
        "UI/UX", "DevOps", "Project Management", "Data Analysis"
    ]

    if request.method == "POST":
        profile.bio = request.POST.get("bio", "")
        profile.website = request.POST.get("website", "")
        profile.industry = request.POST.get("industry", "")

        if user.user_type == "organization":
            profile.company_name = request.POST.get("company_name", "")
            profile.industry = request.POST.get("industry", "")
        else:
            # Social links
            linkedin = request.POST.get("linkedin", "").strip()
            github = request.POST.get("github", "").strip()
            profile.social_links = {
                "linkedin": linkedin,
                "github": github
            }
        if request.FILES.get("profile_picture"):
            profile.profile_picture = request.FILES["profile_picture"]

        profile.save()

        # Skills
        profile.skills.clear()
        selected_skills = request.POST.get("skills", "")
        skill_names_input = [s.strip() for s in selected_skills.split(",") if s.strip()]
        for skill_name in skill_names_input:
            tag, _ = Tag.objects.get_or_create(name=skill_name)
            profile.skills.add(tag)

        messages.success(request, "Profile updated successfully.")
        return redirect("portfolio")

    return render(request, 'portfolio.html', {
        "profile": profile,
        "experiences": experiences,
        "user_type": user.user_type,
        "user_posts": user_posts,
        "skill_names": skill_names,
        "skills_list": skills_list,
        "projects": projects,
    })

@login_required
def delete_profile(request):
    if request.method == 'POST':
        user = request.user
        profile = user.profile
        
        # Deleting associated data
        profile.delete()
        user.delete()

        # Add a success message
        messages.success(request, "Your profile has been deleted successfully.")
        
        # Redirect to a page after deletion (e.g., homepage or login page)
        return redirect('index')  # Adjust the redirect to your homepage or login URL

    return redirect('profile')  # If the method is not POST, stay on the profile page
    
@login_required
def engagements(request):
    return render(request, 'engagements.html')

@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            return redirect("portfolio")  # Redirect back to portfolio
    else:
        form = PostForm()
    return render(request, "create_post.html", 
                  { "form": form,
                    "title": "Create Post",
                    "button_text": "Post",
    })

@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('portfolio')
    else:
        form = PostForm(instance=post)
    return render(request, "create_post.html",{
        "form": form,
        "title": "Edit Post",
        "button_text": "Save Changes",
    })

@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, user=request.user)
    if request.method == 'POST':
        post.delete()
        return redirect('portfolio')


def signup(request):
    if request.method == 'POST':
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        user_type = request.POST.get("user_type")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'register.html', {"error": "Invalid email format"})

        if password != confirm_password:
            return render(request, 'register.html', {"error": "Passwords do not match"})

        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'register.html', {"error": "Email already registered"})

        try:
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type
            )
            user.save()
            print(f"User created successfully: {user}")
            return redirect("/login/")

        except Exception as e:
            print(f"Error creating user: {e}")
            return render(request, 'register.html', {"error": "User creation failed. Please try again."})

    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('/engagements/')

        messages.error(request, "Invalid email or password")
        return render(request, "login.html")

    return render(request, 'login.html')

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        request.session.flush()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"message": "Logout successful", "redirect": "/login/"}, status=200)
        return redirect("login")

    return JsonResponse({"error": "Method not allowed"}, status=405)


User = get_user_model()

class RegisterView(APIView):
    def post(self, request):
        data = json.loads(request.body)

        user = User.objects.create_user(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            password=data["password"],
            user_type=data["user_type"]
        )

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return JsonResponse({"message": "User created successfully"})

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("/engagements/")
        else:
            return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return redirect("/login/")

class SessionCheckView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            return JsonResponse({"isAuthenticated": True, "username": request.user.username})
        return JsonResponse({"isAuthenticated": False})

class PostListView(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class UserProfileView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile
    
@login_required
def add_experience(request):
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = ExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.profile = profile
            experience.save()
            messages.success(request, "Experience added successfully!")
            return redirect('portfolio')  # Change to your actual portfolio URL name
    else:
        form = ExperienceForm()
    return render(request, 'experience_form.html', {'form': form, 'title': 'Add Experience'})

@login_required
def edit_experience(request, pk):
    experience = get_object_or_404(Experience, pk=pk, profile__user=request.user)
    if request.method == 'POST':
        form = ExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            form.save()
            messages.success(request, "Experience updated successfully!")
            return redirect('portfolio')
    else:
        form = ExperienceForm(instance=experience)
    return render(request, 'experience_form.html', {'form': form, 'title': 'Edit Experience'})
    

@login_required
def delete_experience(request, pk):
    experience = get_object_or_404(Experience, pk=pk, profile__user=request.user)
    if request.method == 'POST':
        experience.delete()
        return redirect('portfolio')
    messages.success(request, "Experience deleted successfully!")
    return render(request, 'confirm_delete.html', {'object': experience})

@login_required
def user_posts_view(request):
    user_posts = Post.objects.filter(user=request.user)
    return render(request, 'portfolio/user_posts.html', {'user_posts': user_posts})

@login_required
def add_project(request):
    profile = request.user.profile
    skills_list = [
        "Python", "JavaScript", "Django", "React", "Machine Learning",
        "UI/UX", "DevOps", "Project Management", "Data Analysis"
    ]

    if request.method == 'POST':
        # Get raw input for skills
        raw_skills = request.POST.get('required_skills', '')

        # Create a mutable copy of POST to inject valid tag IDs
        post_data = request.POST.copy()
        skill_names = [s.strip() for s in raw_skills.split(',') if s.strip()]
        tag_ids = []

        for name in skill_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_ids.append(str(tag.id))

        # Replace raw skills with actual tag IDs so the form can validate
        post_data.setlist('required_skills', tag_ids)

        # Now pass the modified POST to the form
        form = ProjectForm(post_data)

        if form.is_valid():
            project = form.save(commit=False)
            project.profile = profile
            project.save()
            form.save_m2m()  # Save required_skills
            return redirect("portfolio")
        else:
            print("Form errors:", form.errors)

    else:
        form = ProjectForm()

    return render(request, "project_form.html", {
        "form": form,
        "heading": "Add New Project",
        "button_text": "Add Project",
        "is_delete": False,
        "skills_list": skills_list,
        "required_skill_names": [],
    })



@login_required
def edit_project(request, pk):
    profile = request.user.profile
    project = get_object_or_404(Project, pk=pk, profile=profile)

    skills_list = [
        "Python", "JavaScript", "Django", "React", "Machine Learning",
        "UI/UX", "DevOps", "Project Management", "Data Analysis"
    ]

    if request.method == 'POST':
        raw_skills = request.POST.get('required_skills', '')
        post_data = request.POST.copy()

        # Convert skill names to tag IDs
        skill_names = [s.strip() for s in raw_skills.split(',') if s.strip()]
        tag_ids = []

        for name in skill_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_ids.append(str(tag.id))

        post_data.setlist('required_skills', tag_ids)

        
        form = ProjectForm(post_data, instance=project)

        if form.is_valid():
            project = form.save(commit=False)
            project.profile = profile
            project.save()
            form.save_m2m()

            return redirect('portfolio')
        else:
            print("Form errors:", form.errors)
    else:
        form = ProjectForm(instance=project)

    required_skill_names = [tag.name for tag in project.required_skills.all()]

    return render(request, "project_form.html", {
        "form": form,
        "heading": "Edit Project",
        "button_text": "Edit Project",
        "is_delete": False,
        "skills_list": skills_list,
        "required_skill_names": required_skill_names,
    })


@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk, profile=request.user.profile)
    if request.method == 'POST':
        project.delete()
        return redirect('portfolio')
    return redirect('portfolio')  # fallback in case someone hits the URL directly

def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    users = CustomUser.objects.all()
    posts = Post.objects.all()
    projects = Project.objects.select_related("profile__user")
    matches = MatchRequest.objects.all()

    freelancer_count = users.filter(user_type='freelancer').count()
    org_count = users.filter(user_type='organization').count()
    total_projects = projects.count()
    total_matches = matches.count()
    post_count = posts.count()

    stats = [
        {'title': 'Total Users', 'value': users.count(), 'color': 'primary'},
        {'title': 'Freelancers', 'value': freelancer_count, 'color': 'success'},
        {'title': 'Organizations', 'value': org_count, 'color': 'warning'},
        {'title': 'Projects', 'value': total_projects, 'color': 'dark'},
        {'title': 'Posts', 'value': post_count, 'color': 'info'},
        {'title': 'Matches', 'value': total_matches, 'color': 'secondary'}
    ]


    context = {
        'stats': stats,
        'users': users,
        'posts': posts,
        'projects': projects,
        'matches': matches,
        'freelancer_count': freelancer_count,
        'org_count': org_count,
        'total_projects': total_projects,
        'total_matches': total_matches,
        'post_count': post_count,
    }
    return render(request, 'admin_dashboard.html', context)

User = get_user_model()

@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('admin_dashboard')

    try:
        user_to_delete = User.objects.get(pk=user_id)
        if user_to_delete == request.user:
            messages.error(request, "You cannot delete yourself.")
        else:
            user_to_delete.delete()
            messages.success(request, "User deleted successfully.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    
    return redirect('admin_dashboard')

@login_required
def admin_delete_post(request, post_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('admin_dashboard')

    try:
        post = Post.objects.get(id=post_id)
        post.delete()
        messages.success(request, "Post deleted successfully.")
    except Post.DoesNotExist:
        messages.error(request, "Post not found.")

    return redirect('admin_dashboard')

@login_required
def admin_delete_project(request, project_id):
    if not request.user.is_superuser:
        return redirect("portfolio")

    project = get_object_or_404(Project, id=project_id)
    project.delete()
    return redirect("admin_dashboard")


