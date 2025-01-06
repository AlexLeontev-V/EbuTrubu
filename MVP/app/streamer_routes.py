import re
import asyncio
import datetime
import jwt
from quart import Blueprint, websocket, jsonify, request, current_app
import pytchat
import httpx
from assistant import Assistant
import tempfile
import os
import json
from storage import storage

streamer_bp = Blueprint('streamer', __name__)

# Создаем экземпляр ассистента
assistant = Assistant()

# Хранилище активных чатов и их состояний
active_chats = {}
stream_states = {}

# Функция для извлечения ID видео из ссылки
def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

# Обработка подключения к трансляции
@streamer_bp.route('/connect_stream', methods=['POST'])
async def connect_stream():
    try:
        data = await request.get_json()
        video_url = data.get('video_url')
        token = request.cookies.get('token')
        
        if not token:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        try:
            data = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
            username = data.get('username')
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "message": "Invalid token"}), 401

        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"status": "error", "message": "Некорректная ссылка на видео"}), 400

        # Проверка доступности видео
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://www.youtube.com/watch?v={video_id}")
                response.raise_for_status()
        except httpx.HTTPError:
            return jsonify({"status": "error", "message": "Ошибка подключения к YouTube"}), 500

        try:
            # Инициализация чата YouTube
            chat = pytchat.create(video_id=video_id)
            if not chat.is_alive():
                return jsonify({"status": "error", "message": "Чат недоступен"}), 400
            
            # Сохраняем информацию о трансляции
            active_chats[video_id] = chat
            stream_states[username] = {
                'video_id': video_id,
                'url': video_url,
                'active': True
            }
            
            # Сохраняем URL трансляции для пользователя
            storage.set(f'stream:{username}:url', video_url)
            
            return jsonify({
                "status": "connected", 
                "video_id": video_id,
                "message": "Трансляция успешно подключена"
            }), 200
            
        except Exception as e:
            print(f"Ошибка подключения: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Ошибка подключения к трансляции: {str(e)}"
            }), 500
    except Exception as e:
        print(f"Общая ошибка: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Внутренняя ошибка сервера"
        }), 500

# WebSocket для чата
@streamer_bp.websocket('/ws/chat')
async def chat_websocket():
    try:
        # Получаем токен из параметров запроса
        token = websocket.args.get('token')
        if not token:
            await websocket.accept()
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Unauthorized"
            }))
            await websocket.close(1000)
            return

        try:
            # Проверяем токен
            data = jwt.decode(token, current_app.secret_key, algorithms=["HS256"])
            username = data.get('username')
        except jwt.InvalidTokenError:
            await websocket.accept()
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid token"
            }))
            await websocket.close(1000)
            return

        # Получаем информацию о трансляции пользователя
        stream_info = stream_states.get(username)
        if not stream_info:
            await websocket.accept()
            await websocket.send(json.dumps({
                "type": "error",
                "message": "No active stream"
            }))
            await websocket.close(1000)
            return

        video_id = stream_info['video_id']
        chat = active_chats.get(video_id)

        if not chat:
            await websocket.accept()
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Chat not found"
            }))
            await websocket.close(1000)
            return

        # Отправляем подтверждение подключения
        await websocket.accept()
        await websocket.send(json.dumps({
            "type": "connection",
            "status": "connected"
        }))

        while True:
            try:
                # Получаем новые сообщения
                chat_data = chat.get()
                if chat_data and chat_data.items:
                    messages = [{
                        'author': item.author.name,
                        'text': item.message,
                        'timestamp': item.timestamp
                    } for item in chat_data.items]

                    # Отправляем сообщения клиенту
                    await websocket.send(json.dumps({
                        'type': 'messages',
                        'messages': messages
                    }))

                # Небольшая задержка
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Ошибка обработки чата: {str(e)}")
                try:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                except:
                    pass
                break

    except Exception as e:
        print(f"Ошибка WebSocket: {str(e)}")
        try:
            await websocket.accept()
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            await websocket.close(1000)
        except:
            pass


@streamer_bp.route('/toggle_assistant', methods=['POST'])
async def toggle_assistant():
    data = await request.get_json()
    if data.get('active'):
        assistant.is_active = True
        response = "Ассистент активирован и готов помогать!"
    else:
        assistant.is_active = False
        response = "Ассистент деактивирован"
    return jsonify({'success': True, 'message': response})


@streamer_bp.route('/add_keyword', methods=['POST'])
async def add_keyword():
    data = await request.get_json()
    keyword = data.get('keyword')
    if keyword:
        assistant.add_keywords([keyword])
        return jsonify({'success': True})
    return jsonify({'success': False})


@streamer_bp.route('/get_keywords')
async def get_keywords():
    return jsonify({'keywords': list(assistant.keywords)})


@streamer_bp.route('/assistant_stats')
async def get_assistant_stats():
    return jsonify({
        'mood': assistant.analyze_chat_mood(),
        'activity': len(assistant.message_history),
        'alerts': assistant.get_alerts()
    })


@streamer_bp.route('/get_alerts')
async def get_alerts():
    return jsonify({'alerts': assistant.get_alerts()})


@streamer_bp.route('/process_command', methods=['POST'])
async def process_command():
    data = await request.get_json()
    command = data.get('command', '')
    
    # Обработка команды ассистентом
    response = assistant._process_streamer_command(command)
    
    return jsonify({
        'success': True,
        'response': response
    })


@streamer_bp.route('/process_transcript', methods=['POST'])
async def process_transcript():
    try:
        data = await request.get_json()
        transcript = data.get('transcript', '')
        
        # Обрабатываем транскрипт
        stats = assistant.process_audio_transcript(transcript)
        
        return jsonify({
            "success": True,
            "transcript": transcript,
            "stats": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
