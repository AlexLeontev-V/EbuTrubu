import jwt
import datetime
import redis
import pytchat
import hashlib
import httpx
from quart import Quart, request, jsonify, make_response, render_template, websocket, redirect, url_for, flash
from datetime import UTC
import os
from storage import storage
from assistant import Assistant

app = Quart(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'
app.static_folder = 'static'
app.static_url_path = '/static'

# Создаем экземпляр ассистента
assistant = Assistant()

# Импортируем блупринты
from streamer_routes import streamer_bp
from advertiser_routes import advertiser_bp

# Регистрируем блупринты
app.register_blueprint(streamer_bp, url_prefix='/streamer')
app.register_blueprint(advertiser_bp, url_prefix='/advertiser')

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
        if storage.hget(f'user:{username}', 'password'):
            await flash('Пользователь уже существует', 'error')
            return await render_template('register.html', role=role)

        # Хеширование пароля и сохранение в базе данных
        hashed_password = hash_password(password)
        storage.hset(f'user:{username}', mapping={'password': hashed_password, 'role': role})

        await flash('Успешная регистрация! Войдите в систему.', 'success')
        return redirect(url_for('login'))

    role = request.args.get('role')
    return await render_template('register.html', role=role)

# Авторизация пользователя
@app.route('/auth', methods=['GET', 'POST'])
async def auth():
    register = request.args.get('register', 'false') == 'true'
    role = request.args.get('role', 'streamer')
    
    if request.method == 'POST':
        data = await request.form
        username = data.get('username')
        password = data.get('password')
        is_register = data.get('register') == 'true'
        role = data.get('role', 'streamer')

        if is_register:
            # Регистрация
            if storage.hget(f'user:{username}', 'password'):
                await flash('Пользователь уже существует', 'error')
                return await render_template('auth.html', register=True, role=role)

            hashed_password = hash_password(password)
            storage.hset(f'user:{username}', mapping={
                'password': hashed_password,
                'role': role
            })
            await flash('Регистрация успешна! Войдите в систему.', 'success')
            return redirect(url_for('auth'))
        else:
            # Вход
            stored_data = storage.hgetall(f'user:{username}')
            stored_password = stored_data.get('password')
            role = stored_data.get('role')

            if not stored_password or stored_password != hash_password(password):
                await flash('Неверный логин или пароль', 'error')
                return await render_template('auth.html', register=False)

            token = jwt.encode({
                'username': username,
                'role': role,
                'exp': datetime.datetime.now(UTC) + datetime.timedelta(hours=1)
            }, app.secret_key)

            storage.set(f'session:{username}', token, ex=3600)
            response = await make_response(redirect(url_for('dashboard')))
            response.set_cookie('token', token)
            return response

    return await render_template('auth.html', register=register, role=role)

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
            return redirect(url_for('studio'))
        elif role == 'advertiser':
            return redirect(url_for('advertiser_studio'))
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
        storage.delete(f'session:{data["username"]}')
        response = await make_response(redirect(url_for('login')))
        response.delete_cookie('token')
        return response
    except jwt.InvalidTokenError:
        await flash('Неверный токен', 'error')
        return redirect(url_for('login'))

# После существующих маршрутов добавим новый
@app.route('/studio')
async def studio():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        if data.get('role') != 'streamer':
            await flash('Доступ запрещен', 'error')
            return redirect(url_for('dashboard'))
        return await render_template('streamer-studio.html', username=data["username"])
    except jwt.InvalidTokenError:
        await flash('Неверный токен', 'error')
        return redirect(url_for('login'))

@app.route('/advertiser-studio')
async def advertiser_studio():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        if data.get('role') != 'advertiser':
            await flash('Доступ запрещен', 'error')
            return redirect(url_for('dashboard'))
        return await render_template('advertiser-studio.html', username=data["username"])
    except jwt.InvalidTokenError:
        await flash('Неверный токен', 'error')
        return redirect(url_for('login'))

@app.route('/settings')
async def settings():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))
    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        return await render_template('settings.html', username=data["username"], role=data["role"])
    except jwt.InvalidTokenError:
        return redirect(url_for('login'))

@app.route('/analytics')
async def analytics():
    token = request.cookies.get('token')
    if not token:
        return redirect(url_for('login'))
    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        return await render_template('analytics.html', username=data["username"], role=data["role"])
    except jwt.InvalidTokenError:
        return redirect(url_for('login'))

@app.route('/api/stats')
async def get_stats():
    token = request.cookies.get('token')
    if not token:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        username = data.get('username')
        
        stats = {
            "viewers": storage.get(f'stream:{username}:viewers') or 0,
            "messages": storage.get(f'stream:{username}:messages') or 0,
            "uptime": storage.get(f'stream:{username}:uptime') or "00:00:00"
        }
        return jsonify(stats)
    except:
        return jsonify({"error": "Invalid token"}), 401

@app.route('/api/commands', methods=['POST'])
async def execute_command():
    token = request.cookies.get('token')
    if not token:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        username = data.get('username')
        
        command_data = await request.get_json()
        command = command_data.get('command')
        
        response = assistant.process_command(command, username)
        return jsonify({"response": response})
    except:
        return jsonify({"error": "Error processing command"}), 500

@app.errorhandler(404)
async def not_found_error(error):
    if request.path.startswith('/static/'):
        return await make_response(
            jsonify({"error": "File not found"}),
            404
        )
    return await render_template('error.html', error=error), 404

@app.errorhandler(500)
async def internal_error(error):
    return await render_template('error.html', error=error), 500

if __name__ == '__main__':
    app.run(debug=True)
