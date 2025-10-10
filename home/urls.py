from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from home import views

urlpatterns = [
    path('', views.index, name='index'),
    path("about/", views.about, name='about'),
    path("engagements/", views.engagements, name='engagements'),  # Frontend page
    path("network/", views.network, name='network'),
    path("network/<int:user_id>/", views.connection_profile, name="connection_profile"),
    path("network/<int:user_id>/remove/", views.remove_connection, name="remove_connection"),

    path("freelancer_matches/", views.freelancer_matches, name='freelancer_matches'),
    path('project/<int:project_id>/request/', views.send_match_request, name='send_match_request'),
    path('organization_matches/', views.organization_match_requests, name='organization_match_requests'),
    path('organization/match-requests/', views.organization_match_requests, name='organization_match_requests'),
    path('organization/match-request/<int:pk>/respond/', views.respond_match_request, name='respond_match_request'),

    path("portfolio/", views.portfolio, name='portfolio'),
    path("delete_profile/", views.delete_profile, name='delete_profile'),
    path('portfolio/engagements/', views.user_posts_view, name='user_posts'),
    path('create-post/', views.create_post, name='create_post'),
    path("post/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("post/<int:pk>/delete/", views.delete_post, name="delete_post"),

    path("signup/", views.signup, name='signup'),
    path("login/", views.login_view, name='login'),  # HTML form login
    path("logout/", views.logout_view, name='logout'),  # HTML logout
    
    # API for Engagements (Posts)
    path("api/posts/", views.PostListView.as_view(), name='api-posts'),

    # Login, Logout and Register (SignUp) APIs
    path('api/login/', views.LoginView.as_view(), name='api-login'),
    path('api/logout/', views.LogoutView.as_view(), name='api-logout'),
    path('api/register/', views.RegisterView.as_view(), name='api-register'),
    path("api/profile/", views.UserProfileView.as_view(), name="api-profile"),

    #experience editing
    path('experience/add/', views.add_experience, name='add_experience'),
    path('experience/<int:pk>/edit/', views.edit_experience, name='edit_experience'),
    path('experience/<int:pk>/delete/', views.delete_experience, name='delete_experience'),

    path('project/add/', views.add_project, name='add_project'),
    path('project/<int:pk>/edit/', views.edit_project, name='edit_project'),
    path('project/<int:pk>/delete/', views.delete_project, name='delete_project'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path("admin-dashboard/delete_user/<int:user_id>/", views.admin_delete_user, name="admin_delete_user"),
    path("admin-dashboard/delete_post/<int:post_id>/", views.admin_delete_post, name="admin_delete_post"),
    path("admin-dashboard/delete_project/<int:project_id>/", views.admin_delete_project, name="admin_delete_project"),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
