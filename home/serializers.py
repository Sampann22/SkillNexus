from rest_framework import serializers
from home.models import Post, CustomUser, Profile, Experience, Connection


# --- Post Serializer ---
# serializers.py
class PostSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'created_at', 'user_full_name', 'can_edit', 'is_owner']

    def get_user_full_name(self, obj):
        first = obj.user.first_name or ''
        last = obj.user.last_name or ''
        return f"{first} {last}".strip()
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.user
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        return request and request.user == obj.user

# --- Experience Serializer (for freelancer profile) ---
class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['organization','role', 'years','details']


# --- Connection Serializer ---
class ConnectionSerializer(serializers.ModelSerializer):
    connected_user_email = serializers.EmailField(source='connected_user.email', read_only=True)

    class Meta:
        model = Connection
        fields = ['id', 'connected_user', 'connected_user_email']


# --- Profile Serializer (shared for both freelancers and organizations) ---
class ProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_type = serializers.CharField(source='user.user_type', read_only=True)
    profile_picture = serializers.ImageField(required=False)
    posts = PostSerializer(source='user.posts', many=True, read_only=True)
    connections = ConnectionSerializer(source='user.following', many=True, read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            'profile_picture'
            'user_email',
            'user_type',
            'bio',
            'website',
            'social_links',
            'skills',
            'company_name',
            'industry',
            'experiences',
            'posts',
            'connections'
        ]




# --- Register Serializer ---
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'user_type']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)
