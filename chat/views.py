import requests
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Conversation, Message


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('chat')
        error = 'Неверное имя пользователя или пароль'

    return render(request, 'chat/login.html', {'error': error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username or not password:
            error = 'Заполните все поля'
        elif password != password2:
            error = 'Пароли не совпадают'
        elif len(password) < 8:
            error = 'Пароль должен содержать минимум 8 символов'
        elif User.objects.filter(username=username).exists():
            error = 'Пользователь с таким именем уже существует'
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('chat')

    return render(request, 'chat/register.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='/login/')
@ensure_csrf_cookie
def chat_view(request):
    profile = request.user.profile
    profile.reset_tokens_if_needed()
    tokens_limit = profile.get_token_limit()
    tokens_used = profile.tokens_used_today
    tokens_percent = min(100, round(tokens_used / tokens_limit * 100)) if tokens_limit > 0 else 0

    return render(request, 'chat/index.html', {
        'profile': profile,
        'conversations': request.user.conversations.all(),
        'tokens_limit': tokens_limit,
        'tokens_used': tokens_used,
        'tokens_remaining': profile.tokens_remaining(),
        'tokens_percent': tokens_percent,
    })


@csrf_exempt
@login_required(login_url='/login/')
def new_conversation(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            consultant = data.get('consultant', Conversation.CONSULTANT_BUSINESS)
        except (json.JSONDecodeError, AttributeError):
            consultant = Conversation.CONSULTANT_BUSINESS

        if consultant not in dict(Conversation.CONSULTANT_CHOICES):
            consultant = Conversation.CONSULTANT_BUSINESS

        conv = Conversation.objects.create(user=request.user, title='Новый чат', consultant=consultant)
        return JsonResponse({'conversation_id': conv.id, 'title': conv.title,
                             'consultant': conv.consultant, 'status': 'success'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required(login_url='/login/')
def get_conversations(request):
    convs = list(request.user.conversations.values('id', 'title', 'updated_at'))
    return JsonResponse({'conversations': convs})


@login_required(login_url='/login/')
def get_conversation_messages(request, conversation_id):
    conv = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    messages = list(conv.messages.values('role', 'content'))
    return JsonResponse({'messages': messages, 'title': conv.title,
                         'consultant': conv.consultant, 'status': 'success'})


@csrf_exempt
@login_required(login_url='/login/')
def delete_conversation(request, conversation_id):
    if request.method == 'POST':
        conv = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        conv.delete()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@login_required(login_url='/login/')
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен', 'status': 'error'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')

        if not user_message:
            return JsonResponse({'error': 'Сообщение не может быть пустым', 'status': 'error'}, status=400)

        profile = request.user.profile
        if not profile.can_send_message():
            return JsonResponse({
                'error': f'Достигнут дневной лимит ({profile.get_token_limit():,} токенов). '
                         f'Обновите план до Премиум или подождите следующего дня.',
                'status': 'limit_exceeded'
            }, status=429)

        consultant = data.get('consultant', Conversation.CONSULTANT_BUSINESS)
        if consultant not in dict(Conversation.CONSULTANT_CHOICES):
            consultant = Conversation.CONSULTANT_BUSINESS

        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create(
                    user=request.user, title='Новый чат', consultant=consultant)
        else:
            conversation = Conversation.objects.create(
                user=request.user, title='Новый чат', consultant=consultant)

        messages_qs = conversation.messages.order_by('timestamp')
        history = [{'role': m.role, 'content': m.content} for m in messages_qs]
        is_first_message = len(history) == 0

        Message.objects.create(conversation=conversation, role='user', content=user_message)

        if is_first_message:
            conversation.title = user_message[:60] + ('...' if len(user_message) > 60 else '')

        try:
            response = requests.post(
                settings.COLAB_API_URL,
                json={'message': user_message, 'history': history, 'consultant': conversation.consultant},
                timeout=90
            )

            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data.get('response', '')

                if not ai_response:
                    return JsonResponse({'error': 'Модель вернула пустой ответ', 'status': 'error'}, status=500)

                Message.objects.create(conversation=conversation, role='assistant', content=ai_response)

                # Rough token estimate: 1 token ≈ 4 characters
                tokens_estimate = max(1, (len(user_message) + len(ai_response)) // 4)
                profile.tokens_used_today += tokens_estimate
                profile.save(update_fields=['tokens_used_today'])

                # Always save conversation to update updated_at (and title on first message)
                conversation.save()

                return JsonResponse({
                    'response': ai_response,
                    'conversation_id': conversation.id,
                    'conversation_title': conversation.title,
                    'consultant': conversation.consultant,
                    'tokens_remaining': profile.tokens_remaining(),
                    'status': 'success'
                })
            else:
                return JsonResponse(
                    {'error': f'Ошибка сервера модели: {response.status_code}', 'status': 'error'},
                    status=500
                )

        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Превышено время ожидания', 'status': 'error'}, status=504)
        except requests.exceptions.ConnectionError:
            return JsonResponse({'error': 'Не удалось подключиться к модели', 'status': 'error'}, status=503)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных', 'status': 'error'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'status': 'error'}, status=500)
