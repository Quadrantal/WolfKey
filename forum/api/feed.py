from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from forum.services.feed_services import get_for_you_posts, get_all_posts
from forum.serializers import PostListSerializer

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_for_you(request):
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('limit', 10))
        
        posts, page_obj = get_for_you_posts(request.user, page, per_page)
        serializer = PostListSerializer(posts, many=True, context={'request': request})
        
        return Response({
            "posts": serializer.data,
            "has_next": page_obj.has_next(),
            "page": page_obj.number,
            "total_pages": page_obj.paginator.num_pages
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_all_posts(request):
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('limit', 10))
        query = request.GET.get('q', '')
        
        result = get_all_posts(request.user, query, page, per_page)
        page_obj = result['page_obj']
        
        serializer = PostListSerializer(page_obj.object_list, many=True, context={'request': request})
        
        return Response({
            "posts": serializer.data,
            "has_next": result['has_next'],
            "page": page_obj.number,
            "total_pages": page_obj.paginator.num_pages,
            "query": query
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
