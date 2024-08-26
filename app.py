import time
import re
import logging
from quart import Quart, render_template, request, redirect, url_for, session
import pyttsx3
import pytchat
import asyncio

# Глобальная функция для очистки комментариев от специальных символов
def clean_comment(comment):
    cleaned_comment = re.sub(r'[^\w\s\u1F600-\u1F64F]', '', comment)
    return cleaned_comment

# Функция для озвучивания текста
async def speak(text):
    logging.info(f"Воспроизведение текста: {text}")
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)  # Устанавливаем первый голос как основной
    engine.say(text)  # Воспроизводим текст
    engine.runAndWait()

# Функция обработки чата и воспроизведения сообщений
async def process_chat(video_id, min_length):
    try:
        logging.info('Попытка создать чат для видео ID: %s', video_id)
        chat = pytchat.create(video_id=video_id)
        if chat.is_alive():
            logging.info('Успешно создан чат для видео ID: %s', video_id)
        else:
            logging.error('Не удалось подключиться к чату. Проверьте правильность video_id.')
            return

        while chat.is_alive() and session.get('is_speaking', False):
            try:
                items = chat.get().sync_items()
                if not items:
                    logging.info('Сообщения пока не поступили. Ожидание...')
                    await asyncio.sleep(2)  # Задержка перед следующим запросом
                    continue

                for c in items:
                    message = clean_comment(c.message)
                    logging.info(f"Получено сообщение: '{message}' от автора: {c.author.name}")

                    if len(message) >= min_length:
                        full_message = f"{c.author.name} говорит {message}"
                        await speak(full_message)
                        await asyncio.sleep(2)  # Добавляем небольшую задержку перед следующим сообщением
                    else:
                        logging.warning('Сообщение слишком короткое: %s', message)
            except Exception as e:
                logging.error(f'Ошибка при обработке сообщений: {str(e)}. Повторная попытка через 5 секунд.')
                await asyncio.sleep(5)
    except Exception as e:
        logging.error(f'Ошибка при подключении к чату: {str(e)}')

def create_app():
    app = Quart(__name__)
    app.secret_key = 'your_secret_key'  # Необходимо для использования сессий

    # Настройка базового логирования для вывода в консоль
    logging.basicConfig(
        level=logging.INFO,  # Уровень логирования
        format='%(asctime)s - %(levelname)s - %(message)s',  # Формат записи
        handlers=[logging.StreamHandler()]  # Вывод логов в консоль
    )

    @app.route('/', methods=['GET', 'POST'])
    async def index():
        logging.info('Пользователь зашел на сайт.')

        if request.method == 'POST':
            form = await request.form
            video_url = form.get('video_url', '')
            min_length = int(form.get('min_length', 0))
            logging.info('Пользователь ввел URL видео: %s', video_url)
            session['video_url'] = video_url
            session['min_length'] = min_length
            video_id = extract_video_id(video_url)
            if video_id:
                session['is_speaking'] = not session.get('is_speaking', False)  # Переключаем состояние
                if session['is_speaking']:
                    asyncio.create_task(process_chat(video_id, min_length))
            else:
                logging.warning('Не удалось извлечь идентификатор видео из URL: %s', video_url)
            return redirect(url_for('index'))

        min_length = session.get('min_length', 0)
        video_url = session.get('video_url', '')
        is_speaking = session.get('is_speaking', False)

        return await render_template(
            'index.html',
            video_url=video_url,
            min_length=min_length,
            is_speaking=is_speaking
        )

    @app.route('/stop', methods=['POST'])
    async def stop():
        session['is_speaking'] = False
        return redirect(url_for('index'))

    return app

# Функция для извлечения идентификатора видео из ссылки
def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
