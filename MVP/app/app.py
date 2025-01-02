import re
import asyncio
import jwt
import datetime
import redis
import pytchat
import hashlib
import httpx
from quart import Quart, request, jsonify, make_response, render_template, websocket, redirect, url_for, flash
from streamer_routes import streamer_bp  # Блупринт для стримера
from advertiser_routes import advertiser_bp  # Блупринт для рекламодателя

app = Quart(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

# Регистрируем блупринты
app.register_blueprint(streamer_bp, url_prefix='/streamer')
app.register_blueprint(advertiser_bp, url_prefix='/advertiser')

# Настройка подключения к Redis
try:
    r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
except redis.ConnectionError:
    print("Ошибка подключения к Redis. Убедитесь, что сервер Redis запущен.")

# Таймаут для WebSocket и HTTP-запросов
REQUEST_TIMEOUT = 120

# Функция для хеширования паролей
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        data = await request.form
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        print("POST-запрос на регистрацию")
        print("Полученная роль:", role)
        print("Имя пользователя:", username)

        # Проверка на корректность роли
        if role not in ['streamer', 'advertiser']:
            await flash('Некорректная роль', 'error')
            return await render_template('register.html', role=role)

        # Проверка на существование пользователя
        if r.hget(f'user:{username}', 'password'):
            await flash('Пользователь уже существует', 'error')
            return await render_template('register.html', role=role)

        # Хеширование пароля и сохранение в базе данных
        hashed_password = hash_password(password)
        r.hset(f'user:{username}', mapping={'password': hashed_password, 'role': role})

        await flash('Успешная регистрация! Войдите в систему.', 'success')
        return redirect(url_for('login'))

    role = request.args.get('role')
    return await render_template('register.html', role=role)

# Авторизация пользователя
@app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        data = await request.form
        username = data.get('username')
        password = data.get('password')

        stored_data = r.hgetall(f'user:{username}')
        stored_password = stored_data.get('password')
        role = stored_data.get('role')

        if not stored_password or stored_password != hash_password(password):
            await flash('Неверный логин или пароль', 'error')
            return await render_template('login.html')

        token = jwt.encode({
            'username': username,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.secret_key)

        r.set(f'session:{username}', token, ex=3600)
        response = await make_response(redirect(url_for('dashboard')))
        response.set_cookie('token', token)
        return response

    return await render_template('login.html')

# Перенаправление на страницу Dashboard в зависимости от роли
@app.route('/dashboard')
async def dashboard():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        role = data.get('role')
        if role == 'streamer':
            return await render_template('streamer_dashboard.html', username=data["username"])
        elif role == 'advertiser':
            return await render_template('advertiser_dashboard.html', username=data["username"])
    except jwt.InvalidTokenError:
        await flash('Неверный токен', 'error')
        return redirect(url_for('login'))

# Главная страница
@app.route('/')
async def index():
    return await render_template('index.html')

# Выход из системы
@app.route('/logout')
async def logout():
    token = request.cookies.get('token')
    if not token:
        await flash('Токен отсутствует', 'error')
        return redirect(url_for('login'))

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        r.delete(f'session:{data["username"]}')
        response = await make_response(redirect(url_for('login')))
        response.delete_cookie('token')
        return response
    except jwt.InvalidTokenError:
        await flash('Неверный токен', 'error')
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
