import re
import asyncio
from quart import Blueprint, websocket, jsonify, request
import pytchat
import httpx

streamer_bp = Blueprint('streamer', __name__)


# Функция для извлечения ID видео из ссылки
def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


# Хранилище для активных чатов
active_chats = {}


# Обработка подключения к трансляции
@streamer_bp.route('/connect_stream', methods=['POST'])
async def connect_stream():
    data = await request.get_json()
    video_url = data.get('video_url')
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

    # Инициализация чата
    active_chats[video_id] = pytchat.create(video_id=video_id)
    return jsonify({"status": "connected", "video_id": video_id}), 200


# WebSocket для чата
@streamer_bp.websocket('/ws/chat')
async def chat_websocket():
    video_id = websocket.args.get("video_id")  # Используем аргументы WebSocket

    if video_id not in active_chats:
        await websocket.send_json({"error": "Трансляция не подключена"})
        await websocket.close(1000)
        return

    active_chat = active_chats[video_id]

    try:
        while active_chat.is_alive():
            messages = []
            for chat_message in active_chat.get().items:
                messages.append({
                    "author": chat_message.author.name,
                    "text": chat_message.message
                })

            await websocket.send_json({"messages": messages})
            await asyncio.sleep(1)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close(1000)
