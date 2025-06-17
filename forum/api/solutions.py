from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
import json

from forum.services.solution_services import (
    create_solution_service,
    update_solution_service,
    delete_solution_service,
    vote_solution_service,
    accept_solution_service
)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_solution_api(request, post_id):
    try:
        data = json.loads(request.body)
        result = create_solution_service(request.user, post_id, data)
        return JsonResponse(result, status=201 if 'id' in result else 400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['PUT', 'PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_solution_api(request, solution_id):
    try:
        data = json.loads(request.body)
        result = update_solution_service(request.user, solution_id, data)
        return JsonResponse(result, status=200 if 'id' in result else 400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_solution_api(request, solution_id):
    result = delete_solution_service(request.user, solution_id)
    return JsonResponse(result, status=200 if 'message' in result else 400)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def vote_solution_api(request, solution_id):
    try:
        data = json.loads(request.body)
        vote_type = data.get('vote_type')
        if vote_type not in ['upvote', 'downvote']:
            return JsonResponse({'error': 'Invalid vote type'}, status=400)
        
        result = vote_solution_service(request.user, solution_id, vote_type)
        return JsonResponse(result, status=200 if 'vote_state' in result else 400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def accept_solution_api(request, solution_id):
    result = accept_solution_service(request.user, solution_id)
    if 'error' in result:
        return JsonResponse(result, status=403)
    return JsonResponse(result)
