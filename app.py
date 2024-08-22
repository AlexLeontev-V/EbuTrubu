import multiprocessing
import time
import re
import logging
from quart import Quart, render_template, request, redirect, url_for, session
import pyttsx3
import pytchat

# Глобальная функция для очистки комментариев от специальных символов
def clean_comment(comment):
    cleaned_comment = re.sub(r'[^\w\s\u1F600-\u1F64F]', '', comment)
    return cleaned_comment

# Глобальная функция для озвучивания текста
def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)  # Устанавливаем первый голос как основной
    engine.say(text)
    engine.runAndWait()
    time.sleep(1)  # Добавляем задержку для завершения воспроизведения

# Глобальная функция для обработки чата
def process_chat(video_id, min_length):
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
                    # Определение действия в зависимости от наличия вопросительного знака
                    action = 'спрашивает' if '?' in message else 'говорит'
                    if author != last_author:
                        speak(f"{author} {action}")
                        time.sleep(0.5)
                    speak(message)
                    time.sleep(2)
                    last_author = author
                else:
                    logging.warning('Сообщение слишком короткое: %s', message)
    except Exception as e:
        logging.error('Ошибка при обработке чата: %s', str(e))

def create_app():
    app = Quart(__name__)
    app.secret_key = 'your_secret_key'  # Необходимо для использования сессий

    # Настройка базового логирования
    logging.basicConfig(
        filename='app.log',  # Файл для записи логов
        level=logging.INFO,  # Уровень логирования
        format='%(asctime)s - %(levelname)s - %(message)s'  # Формат записи
    )

    # Переменные для хранения состояния
    chat_processes = []

    # Функция для извлечения идентификатора видео из ссылки
    def extract_video_id(url):
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        return match.group(1) if match else None

    # Функция для запуска озвучивания в отдельном процессе
    def start_speaking(video_id, min_length):
        process = multiprocessing.Process(target=process_chat, args=(video_id, min_length))
        process.start()
        chat_processes.append(process)
        session['is_speaking'] = True
        logging.info('Запустили озвучивание для видео ID: %s', video_id)

    # Функция для остановки всех процессов
    def stop_all_processes():
        nonlocal chat_processes  # Используем nonlocal для изменения внешней переменной
        for process in chat_processes:
            process.terminate()
        chat_processes = []
        session['is_speaking'] = False
        logging.info('Остановили все процессы озвучивания.')

    @app.route('/', methods=['GET', 'POST'])
    async def index():
        logging.info('Пользователь зашел на сайт.')

        if 'is_speaking' not in session:
            session['is_speaking'] = False

        if request.method == 'POST':
            if session.get('is_speaking', False):
                stop_all_processes()
                logging.info('Пользователь нажал кнопку: Выключить.')
            else:
                form = await request.form
                video_url = form.get('video_url', '')
                min_length = int(form.get('min_length', 0))
                logging.info('Пользователь ввел URL видео: %s', video_url)
                session['video_url'] = video_url
                session['min_length'] = min_length
                video_id = extract_video_id(video_url)
                if video_id:
                    start_speaking(video_id, min_length)
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

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
