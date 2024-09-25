import re
import asyncio
import jwt
import datetime
import redis
import pytchat
import hashlib
import httpx
from quart import Quart, request, jsonify, make_response, render_template, websocket, redirect, url_for

app = Quart(__name__)
app.secret_key = 'your_secret_key'

# Настройка подключения к Redis
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# Таймаут для WebSocket и HTTP-запросов
REQUEST_TIMEOUT = 10


# Функция для хеширования паролей
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Функция для извлечения ID видео из YouTube ссылки
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        data = await request.form
        username = data.get('username')
        password = data.get('password')

        if r.hget('users', username):
            return jsonify({'message': 'Пользователь уже существует'}), 400

        hashed_password = hash_password(password)
        r.hset('users', username, hashed_password)

        return redirect(url_for('login'))

    return await render_template('register.html')


# Авторизация пользователя
@app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        data = await request.form
        username = data.get('username')
        password = data.get('password')

        stored_password = r.hget('users', username)

        if not stored_password or stored_password != hash_password(password):
            return jsonify({'message': 'Неверный логин или пароль'}), 401

        token = jwt.encode({
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.secret_key)

        r.set(f'session:{username}', token, ex=3600)

        response = await make_response(redirect(url_for('protected')))
        response.set_cookie('token', token)

        return response

    return await render_template('login.html')


# Защищённая страница
@app.route('/protected')
async def protected():
    token = request.cookies.get('token')

    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        stored_token = r.get(f'session:{data["username"]}')
        if stored_token != token:
            return jsonify({'message': 'Неверный токен'}), 403

        return await render_template('protected.html', username=data["username"])

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Токен истек'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Неверный токен'}), 401


# WebSocket для чата
@app.websocket('/ws')
async def ws():
    video_url = websocket.args.get('video_url')
    if not video_url:
        await websocket.send_json({'message': 'Ошибка: Не указана ссылка на видео'})
        return

    video_id = extract_video_id(video_url)
    if not video_id:
        await websocket.send_json({'message': 'Ошибка: Не удалось извлечь ID видео'})
        return

    await websocket.send_json({'message': f'Подключение к видео ID: {video_id}'})

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(f"https://www.youtube.com/embed/{video_id}")
            response.raise_for_status()
    except httpx.RequestError as exc:
        await websocket.send_json({'message': f"Ошибка соединения: {str(exc)}"})
        return
    except httpx.HTTPStatusError as exc:
        await websocket.send_json({'message': f"Ошибка HTTP: {str(exc)}"})
        return
    except asyncio.TimeoutError:
        await websocket.send_json({'message': 'Таймаут подключения к YouTube'})
        return

    chat = pytchat.create(video_id=video_id)

    while chat.is_alive():
        try:
            for c in chat.get().items:
                await websocket.send_json({'message': f'{c.author.name}: {c.message}'})
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            await websocket.send_json({'message': f'Ошибка в чате: {str(e)}'})
            break

    await websocket.send_json({'message': 'Чат завершён'})


# Выход из системы
@app.route('/logout')
async def logout():
    token = request.cookies.get('token')
    if not token:
        return jsonify({'message': 'Токен отсутствует'}), 400

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        r.delete(f'session:{data["username"]}')

        response = await make_response(redirect(url_for('login')))
        response.delete_cookie('token')

        return response
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Неверный токен'}), 401


# Главная страница
@app.route('/')
async def index():
    return await render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
