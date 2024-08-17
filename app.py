import multiprocessing
import time
import re
from flask import Flask, render_template, request, redirect, url_for, session
import pyttsx3
import pytchat

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Необходимо для использования сессий

# Инициализация движка речи
engine = pyttsx3.init()

# Получение списка доступных голосов
voices = engine.getProperty('voices')

# Переменные для хранения состояния
chat_processes = []

# Функция для озвучивания текста
def speak(text, voice_index):
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
def process_chat(video_id, min_length, voice_index):
    chat = pytchat.create(video_id=video_id)
    last_author = None
    while chat.is_alive():
        for c in chat.get().sync_items():
            message = clean_comment(c.message)
            if len(message) >= min_length:
                author = c.author.name
                if author != last_author:
                    speak(f"{author} говорит", voice_index)
                    time.sleep(0.5)
                speak(message, voice_index)
                time.sleep(2)
                last_author = author

# Функция для запуска озвучивания в отдельном процессе
def start_speaking(video_id, min_length, voice_index):
    process = multiprocessing.Process(target=process_chat, args=(video_id, min_length, voice_index))
    process.start()
    chat_processes.append(process)
    session['is_speaking'] = True  # Обновляем состояние в сессии

# Функция для остановки всех процессов
def stop_all_processes():
    global chat_processes
    for process in chat_processes:
        process.terminate()
    chat_processes = []
    session['is_speaking'] = False  # Обновляем состояние в сессии

@app.route('/', methods=['GET', 'POST'])
def index():
    # Устанавливаем состояние is_speaking в False, если оно не определено
    if 'is_speaking' not in session:
        session['is_speaking'] = False

    if request.method == 'POST':
        if session.get('is_speaking', False):
            stop_all_processes()
        else:
            session['video_url'] = request.form.get('video_url', '')
            session['min_length'] = int(request.form.get('min_length', 0))
            session['voice_index'] = int(request.form.get('voice_index', 0))
            video_id = extract_video_id(session['video_url'])
            if video_id:
                start_speaking(video_id, session['min_length'], session['voice_index'])
        return redirect(url_for('index'))

    # Загружаем настройки из сессии, если они существуют
    min_length = session.get('min_length', 0)
    selected_voice_index = session.get('voice_index', 0)
    video_url = session.get('video_url', '')
    is_speaking = session.get('is_speaking', False)

    # Создание списка кортежей (индекс, голос)
    voices_with_index = [(index, voice) for index, voice in enumerate(voices)]

    return render_template(
        'index.html',
        video_url=video_url,
        min_length=min_length,
        voices=voices_with_index,
        selected_voice_index=selected_voice_index,
        is_speaking=is_speaking
    )

if __name__ == '__main__':
    app.run(debug=True)