from rest_framework import serializers
from .models import Post, Solution, Comment, User, UserProfile, Course
from django.utils.timezone import localtime
from .services.utils import process_post_preview

class CourseSerializer(serializers.ModelSerializer):
    is_experienced = serializers.SerializerMethodField()
    needs_help = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'name', 'category', 'description', 'is_experienced', 'needs_help']
    
    def get_is_experienced(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            experienced_courses = getattr(request, '_experienced_courses', None)
            if experienced_courses is None:
                from .services.course_services import get_user_courses
                experienced_courses, _ = get_user_courses(request.user)
                request._experienced_courses = experienced_courses
            return obj in experienced_courses
        return False
    
    def get_needs_help(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            help_needed_courses = getattr(request, '_help_needed_courses', None)
            if help_needed_courses is None:
                from .services.course_services import get_user_courses
                _, help_needed_courses = get_user_courses(request.user)
                request._help_needed_courses = help_needed_courses
            return obj in help_needed_courses
        return False

class UserProfileSerializer(serializers.ModelSerializer):
    block_1A = CourseSerializer(read_only=True)
    block_1B = CourseSerializer(read_only=True)
    block_1D = CourseSerializer(read_only=True)
    block_1E = CourseSerializer(read_only=True)
    block_2A = CourseSerializer(read_only=True)
    block_2B = CourseSerializer(read_only=True)
    block_2C = CourseSerializer(read_only=True)
    block_2D = CourseSerializer(read_only=True)
    block_2E = CourseSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'bio', 'points', 'is_moderator', 'created_at', 'updated_at',
            'background_hue', 'profile_picture',
            'block_1A', 'block_1B', 'block_1D', 'block_1E',
            'block_2A', 'block_2B', 'block_2C', 'block_2D', 'block_2E'
        ]

class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'school_email', 'personal_email', 'phone_number', 
            'date_joined', 'userprofile'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class PostListSerializer(serializers.ModelSerializer):
    """Serializer for post list/feed views - matches paginate_posts structure"""
    author = UserSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    preview_text = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'author', 'author_name', 'preview_text', 
            'created_at', 'courses', 'reply_count'
        ]
    
    def get_author_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.author.get_full_name() if obj.author else "Unknown"
    
    def get_preview_text(self, obj):
        return process_post_preview(obj)
    
    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()
    
    def get_courses(self, obj):
        return CourseSerializer(obj.courses.all(), many=True, context=self.context).data
    
    def get_reply_count(self, obj):
        return getattr(obj, 'total_response_count', 0)

class PostDetailSerializer(serializers.ModelSerializer):
    """Serializer for individual post views"""
    author = UserSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    solution_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    solutions = serializers.SerializerMethodField()
    has_solution_from_user = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'author', 'author_name', 'courses', 'created_at',
            'solved', 'views', 'is_anonymous', 'like_count', 'is_liked',
            'solution_count', 'comment_count', 'solutions', 'has_solution_from_user',
            'is_following'
        ]
    
    def get_courses(self, obj):
        return CourseSerializer(obj.courses.all(), many=True, context=self.context).data
    
    def get_author_name(self, obj):
        """Return author name, handling anonymous posts"""
        if obj.is_anonymous:
            return "Anonymous"
        return obj.author.get_full_name() if obj.author else "Unknown"
    
    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()
    
    def get_like_count(self, obj):
        return obj.like_count()
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_liked_by(request.user)
        return False
    
    def get_solution_count(self, obj):
        return getattr(obj, 'solution_count', obj.solutions.count())
    
    def get_comment_count(self, obj):
        return getattr(obj, 'comment_count', 0)
    
    def get_solutions(self, obj):
        """Return solutions using SolutionSerializer with proper ordering"""
        from django.db.models import F, Case, When, IntegerField
        
        solutions = obj.solutions.select_related('author').annotate(
            vote_score=F('upvotes') - F('downvotes')
        ).order_by(
            Case(
                When(id=obj.accepted_solution_id, then=0),
                default=1,
                output_field=IntegerField(),
            ),
            '-vote_score',
            '-created_at'
        )
        
        return SolutionSerializer(solutions, many=True, context=self.context).data
    
    def get_has_solution_from_user(self, obj):
        """Check if the current user has submitted a solution"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.solutions.filter(author=request.user).exists()
        return False
    
    def get_is_following(self, obj):
        """Check if the current user is following this post"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .models import FollowedPost
            return FollowedPost.objects.filter(user=request.user, post=obj).exists()
        return False

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'author', 'created_at', 'parent',
            'replies', 'depth'
        ]
    
    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()
    
    def get_replies(self, obj):
        if hasattr(obj, 'replies'):
            return CommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []
    
    def get_depth(self, obj):
        return obj.get_depth()

class SolutionSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    author_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    is_accepted = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    processed_content = serializers.SerializerMethodField()
    
    class Meta:
        model = Solution
        fields = [
            'id', 'content', 'processed_content', 'author', 'author_name', 'created_at', 
            'upvotes', 'downvotes', 'comments', 'is_accepted', 'is_saved'
        ]
    
    def get_author_name(self, obj):
        """Return author name for convenience"""
        return obj.author.get_full_name() if obj.author else "Unknown"
    
    def get_created_at(self, obj):
        return localtime(obj.created_at).isoformat()
    
    def get_processed_content(self, obj):
        """Process solution content - handle string JSON and quote replacement"""
        from .services.utils import selective_quote_replace
        import json
        
        try:
            solution_content = obj.content
            if isinstance(solution_content, str):
                solution_content = selective_quote_replace(solution_content)
                solution_content = json.loads(solution_content)
            return solution_content
        except Exception as e:
            return obj.content
    
    def get_comments(self, obj):
        """Get formatted comments for this solution"""
        comments = obj.comments.select_related('author').order_by('created_at')
        return [{
            'id': comment.id,
            'content': comment.content,
            'author': comment.author.get_full_name(),
            'created_at': comment.created_at.isoformat(),
            'parent_id': comment.parent_id,
            'depth': comment.get_depth(),
        } for comment in comments]
    
    def get_is_accepted(self, obj):
        return hasattr(obj, 'accepted_for') and obj.accepted_for is not None
    
    def get_is_saved(self, obj):
        """Check if the current user has saved this solution"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .models import SavedSolution
            return SavedSolution.objects.filter(user=request.user, solution=obj).exists()
        return False