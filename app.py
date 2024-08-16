import multiprocessing
import time
import re
from flask import Flask, render_template, request, redirect, url_for
import pyttsx3
import pytchat

app = Flask(__name__)

# Инициализация движка речи
engine = pyttsx3.init()

# Переменные для хранения состояния
chat_process = None
is_speaking = False
min_length = 0

# Функция для озвучивания текста
def speak(text):
    engine.say(text)
    engine.runAndWait()

# Функция для очистки комментариев от специальных символов
def clean_comment(comment):
    cleaned_comment = re.sub(r'[^\w\s\u1F600-\u1F64F]', '', comment)
    return cleaned_comment

# Функция для обработки чата
def process_chat(video_id, min_length):
    chat = pytchat.create(video_id=video_id)
    last_author = None
    while chat.is_alive():
        for c in chat.get().sync_items():
            message = clean_comment(c.message)
            if len(message) >= min_length:
                author = c.author.name
                if author != last_author:
                    speak(author)
                    time.sleep(0.5)
                speak(message)
                time.sleep(2)
                last_author = author

# Функция для запуска озвучивания в отдельном процессе
def start_speaking(video_id, min_length):
    global chat_process, is_speaking
    if not is_speaking:
        chat_process = multiprocessing.Process(target=process_chat, args=(video_id, min_length))
        chat_process.start()
        is_speaking = True

# Функция для остановки обработки
def stop_speaking():
    global chat_process, is_speaking
    if chat_process:
        chat_process.terminate()
        chat_process = None
    is_speaking = False

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_speaking, min_length
    if request.method == 'POST':
        if is_speaking:
            stop_speaking()
        else:
            video_id = request.form.get('video_id', '')
            min_length = int(request.form.get('min_length', 0))
            if video_id:
                start_speaking(video_id, min_length)
        return redirect(url_for('index'))
    return render_template('index.html', is_speaking=is_speaking, min_length=min_length)

if __name__ == '__main__':
    app.run(debug=True)