import asyncio
import re
import logging
from quart import Quart, render_template, request, redirect, url_for, session
import pyttsx3
import pytchat

app = Quart(__name__)
app.secret_key = 'your_secret_key'  # Необходимо для использования сессий

# Настройка базового логирования
logging.basicConfig(
    filename='app.log',  # Файл для записи логов
    level=logging.INFO,  # Уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s'  # Формат записи
)

# Инициализация движка речи
engine = pyttsx3.init()

# Получение списка доступных голосов
voices = engine.getProperty('voices')

# Список для хранения задач
tasks = []

# Функция для озвучивания текста
async def speak(text, voice_index):
    engine.setProperty('voice', voices[voice_index].id)
    engine.say(text)
    engine.runAndWait()

# Функция для очистки комментариев от специальных символов
def clean_comment(comment):
    cleaned_comment = re.sub(r'[^\w\s\u1F600-\u1F64F]', '', comment)
    return cleaned_comment

# Функция для извлечения идентификатора видео из ссылки
def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

# Функция для обработки чата
async def process_chat(video_id, min_length, voice_index):
    try:
        chat = pytchat.create(video_id=video_id)
        last_author = None
        logging.info('Обработка чата для видео ID: %s', video_id)
        while chat.is_alive():
            for c in chat.get().sync_items():
                message = clean_comment(c.message)
                if len(message) >= min_length:
                    author = c.author.name
                    logging.info('Получено сообщение от %s: %s', author, message)
                    action = "спрашивает" if "?" in message else "говорит"
                    if author != last_author:
                        await speak(f"{author} {action}", voice_index)
                        await asyncio.sleep(0.5)
                    await speak(message, voice_index)
                    await asyncio.sleep(2)
                    last_author = author
                else:
                    logging.warning('Сообщение слишком короткое: %s', message)
    except Exception as e:
        logging.error('Ошибка при обработке чата: %s', str(e))

# Функция для запуска озвучивания
async def start_speaking(video_id, min_length, voice_index):
    task = asyncio.create_task(process_chat(video_id, min_length, voice_index))
    tasks.append(task)
    session['is_speaking'] = True
    logging.info('Запустили озвучивание для видео ID: %s', video_id)

# Функция для остановки всех процессов
async def stop_all_processes():
    for task in tasks:
        task.cancel()  # Отменяем задачу
        try:
            await task  # Ждем завершения задачи
        except asyncio.CancelledError:
            logging.info('Задача была отменена.')
    tasks.clear()
    session['is_speaking'] = False
    logging.info('Остановили все процессы озвучивания.')

@app.route('/', methods=['GET', 'POST'])
async def index():
    logging.info('Пользователь зашел на сайт.')

    if 'is_speaking' not in session:
        session['is_speaking'] = False

    if request.method == 'POST':
        if session.get('is_speaking', False):
            await stop_all_processes()
            logging.info('Пользователь нажал кнопку: Выключить.')
        else:
            form = await request.form
            video_url = form.get('video_url', '')
            logging.info('Пользователь ввел URL видео: %s', video_url)
            session['video_url'] = video_url
            session['min_length'] = int(form.get('min_length', 0))
            session['voice_index'] = int(form.get('voice_index', 0))
            video_id = extract_video_id(session['video_url'])
            if video_id:
                await start_speaking(video_id, session['min_length'], session['voice_index'])
            else:
                logging.warning('Не удалось извлечь идентификатор видео из URL: %s', video_url)
        return redirect(url_for('index'))

    min_length = session.get('min_length', 0)
    selected_voice_index = session.get('voice_index', 0)
    video_url = session.get('video_url', '')
    is_speaking = session.get('is_speaking', False)

    voices_with_index = [(index, voice) for index, voice in enumerate(voices)]

    return await render_template(
        'index.html',
        video_url=video_url,
        min_length=min_length,
        voices=voices_with_index,
        selected_voice_index=selected_voice_index,
        is_speaking=is_speaking
    )

if __name__ == '__main__':
    app.run(debug=True)