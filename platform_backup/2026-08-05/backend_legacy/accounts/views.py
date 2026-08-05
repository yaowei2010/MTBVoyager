# views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
import json
from django.contrib.auth import authenticate

@api_view(['POST'])
def register(request):
    print("=== DEBUG START ===")
    print("Content-Type:", request.content_type)
    print("Raw Body:", request.body)
    try:
        data = json.loads(request.body.decode('utf-8'))
        print("Parsed JSON:", data)
    except Exception as e:
        print("JSON Decode Error:", str(e))
        return Response({'error': 'Invalid JSON'}, status=400)


    username = data.get('username')
    password = data.get('password')
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)
    user = User.objects.create_user(username=username, password=password)
    return Response({'message': 'User created successfully'}, status=201)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    return Response({
        'username': user.username,
        'id': user.id,
    })


@api_view(['GET'])
def test_david_id(request):
    user = authenticate(username='david', password='REDACTED_SET_VIA_ENV')
    if user is not None:
        return Response({'user_id': user.id, 'username': user.username})
    else:
        return Response({'error': 'Invalid credentials or user not found'}, status=400)