from django.contrib import admin
from .models import Profile, Project, Post, MatchRequest, Experience, Tag, Connection, CustomUser

admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Project)
admin.site.register(Post)
admin.site.register(MatchRequest)
admin.site.register(Experience)
admin.site.register(Tag)
admin.site.register(Connection)
