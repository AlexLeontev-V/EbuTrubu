import os
from collections import deque, Counter
import pytchat
import json
import re
import random

class Assistant:
    def __init__(self):
        self.is_active = False
        self.keywords = set()
        self.message_history = []
        self.transcribed_words = []
        self.word_frequency = Counter()
        
        # Инициализация остальных атрибутов
        self.commands = {
            "статистика": self.get_stats,
            "очистить чат": self.clear_chat,
            "мут": self.mute_user,
            "размут": self.unmute_user,
            "бан": self.ban_user,
            "разбан": self.unban_user,
            "режим чата": self.set_chat_mode,
            "медленный режим": self.slow_mode,
            "эмодзи": self.toggle_emoji,
            "подписчики": self.subscribers_only,
            "фолловеры": self.followers_only,
            "таймер": self.set_timer,
            "напоминание": self.set_reminder,
            "опрос": self.create_poll,
            "розыгрыш": self.start_giveaway,
            "команда": self.add_command,
            "удалить команду": self.remove_command,
            "модератор": self.add_moderator,
            "снять модератора": self.remove_moderator,
            "помощь": self.show_help
        }
        self.muted_users = set()
        self.banned_users = set()
        self.chat_mode = "normal"
        self.slow_mode_delay = 0
        self.emoji_enabled = True
        self.custom_commands = {}
        self.moderators = set()
        self.active_polls = {}
        self.active_giveaways = {}
        self.timers = {}
        self.reminders = {}

    def activate(self):
        self.active = True
        return "Ассистент активирован и готов помогать!"

    def deactivate(self):
        self.active = False
        return "Ассистент деактивирован."

    def process_message(self, message, author):
        """Обработка входящего сообщения"""
        if not self.active:
            return None

        self.message_history.append({"author": author, "text": message})
        
        # Проверка ключевых слов
        for keyword in self.keywords:
            if keyword.lower() in message.lower():
                self.alerts.append(f"Обнаружено ключевое слово: {keyword}")

        # Анализ настроения чата
        if self._is_negative_message(message):
            return self._generate_mood_improvement_response()

        # Ответ на команды стримера
        if author == "streamer":
            return self._process_streamer_command(message)

        return None

    def add_keywords(self, keywords):
        """Добавление ключевых слов для отслеживания"""
        self.keywords.update(keywords)

    def get_alerts(self):
        """Получение накопленных уведомлений"""
        alerts = self.alerts.copy()
        self.alerts = []
        return alerts

    def analyze_chat_mood(self):
        """Анализ общего настроения чата"""
        if not self.message_history:
            return "Недостаточно данных для анализа"

        # Простой анализ по ключевым словам
        positive = 0
        negative = 0
        for msg in self.message_history:
            if self._is_positive_message(msg['text']):
                positive += 1
            elif self._is_negative_message(msg['text']):
                negative += 1

        total = len(self.message_history)
        mood = (positive - negative) / total if total > 0 else 0

        if mood > 0.2:
            return "Позитивное настроение в чате"
        elif mood < -0.2:
            return "Негативное настроение в чате"
        return "Нейтральное настроение в чате"

    def _is_positive_message(self, message):
        positive_words = {'круто', 'супер', 'класс', 'отлично', 'хорошо', '👍', '❤️'}
        return any(word in message.lower() for word in positive_words)

    def _is_negative_message(self, message):
        negative_words = {'плохо', 'ужас', 'отстой', 'фу', 'бан', '👎'}
        return any(word in message.lower() for word in negative_words)

    def _generate_mood_improvement_response(self):
        responses = [
            "Давайте сохранять позитивный настрой!",
            "Предлагаю обсудить это конструктивно",
            "Помните о правилах чата и взаимоуважении"
        ]
        return random.choice(responses)

    def _process_streamer_command(self, command_text):
        command_text = command_text.lower().strip()
        
        # Проверяем прямые команды
        for cmd, func in self.commands.items():
            if command_text.startswith(cmd):
                args = command_text[len(cmd):].strip()
                return func(args) if args else func()
        
        # Проверяем пользовательские команды
        if command_text in self.custom_commands:
            return self.custom_commands[command_text]
        
        return "Команда не распознана. Используйте 'помощь' для списка команд."

    def get_stats(self):
        return f"Статистика чата:\nМодераторов: {len(self.moderators)}\nЗамученных: {len(self.muted_users)}\nЗабаненных: {len(self.banned_users)}"

    def clear_chat(self):
        return "Чат очищен"

    def mute_user(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.muted_users.add(username)
        return f"Пользователь {username} замучен"

    def unmute_user(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.muted_users.discard(username)
        return f"Пользователь {username} размучен"

    def ban_user(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.banned_users.add(username)
        return f"Пользователь {username} забанен"

    def unban_user(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.banned_users.discard(username)
        return f"Пользователь {username} разбанен"

    def set_chat_mode(self, mode):
        valid_modes = ["normal", "subscribers", "followers", "emote"]
        if mode not in valid_modes:
            return f"Доступные режимы: {', '.join(valid_modes)}"
        self.chat_mode = mode
        return f"Установлен режим чата: {mode}"

    def slow_mode(self, seconds=None):
        if not seconds:
            return "Медленный режим выключен"
        try:
            self.slow_mode_delay = int(seconds)
            return f"Медленный режим: {seconds} секунд"
        except ValueError:
            return "Укажите время в секундах"

    def toggle_emoji(self):
        self.emoji_enabled = not self.emoji_enabled
        return f"Эмодзи {'включены' if self.emoji_enabled else 'выключены'}"

    def subscribers_only(self):
        self.chat_mode = "subscribers"
        return "Включен режим только для подписчиков"

    def followers_only(self):
        self.chat_mode = "followers"
        return "Включен режим только для фолловеров"

    def set_timer(self, args):
        try:
            name, duration = args.split(maxsplit=1)
            duration = int(duration)
            self.timers[name] = duration
            return f"Таймер {name} установлен на {duration} секунд"
        except:
            return "Формат: таймер [название] [секунды]"

    def set_reminder(self, message):
        if not message:
            return "Укажите текст напоминания"
        reminder_id = len(self.reminders) + 1
        self.reminders[reminder_id] = message
        return f"Напоминание #{reminder_id} создано: {message}"

    def create_poll(self, args):
        try:
            question, *options = args.split('|')
            poll_id = len(self.active_polls) + 1
            self.active_polls[poll_id] = {
                'question': question.strip(),
                'options': [opt.strip() for opt in options],
                'votes': {opt.strip(): 0 for opt in options}
            }
            return f"Опрос #{poll_id} создан: {question}"
        except:
            return "Формат: опрос Вопрос | Вариант 1 | Вариант 2 | ..."

    def start_giveaway(self, prize):
        if not prize:
            return "Укажите приз"
        giveaway_id = len(self.active_giveaways) + 1
        self.active_giveaways[giveaway_id] = {
            'prize': prize,
            'participants': set()
        }
        return f"Розыгрыш #{giveaway_id} начат: {prize}"

    def add_command(self, args):
        try:
            name, response = args.split(maxsplit=1)
            self.custom_commands[name.lower()] = response
            return f"Команда !{name} добавлена"
        except:
            return "Формат: команда [название] [ответ]"

    def remove_command(self, name):
        if not name:
            return "Укажите название команды"
        name = name.lower()
        if name in self.custom_commands:
            del self.custom_commands[name]
            return f"Команда !{name} удалена"
        return "Команда не найдена"

    def add_moderator(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.moderators.add(username)
        return f"{username} назначен модератором"

    def remove_moderator(self, username):
        if not username:
            return "Укажите имя пользователя"
        self.moderators.discard(username)
        return f"{username} больше не модератор"

    def show_help(self):
        commands_list = "\n".join([f"• {cmd}" for cmd in self.commands.keys()])
        return f"Доступные команды:\n{commands_list}"

    def process_command(self, command, username):
        """Обработка команд от стримера"""
        command = command.lower().strip()
        
        # Базовые команды
        if command == "статистика":
            return self.get_stats()
        elif command.startswith("мут"):
            user = command.replace("мут", "").strip()
            return self.mute_user(user)
        elif command.startswith("бан"):
            user = command.replace("бан", "").strip()
            return self.ban_user(user)
        elif command == "очистить чат":
            return self.clear_chat()
        elif command == "помощь":
            return self.show_help()
        
        # Проверяем пользовательские команды
        if command in self.custom_commands:
            return self.custom_commands[command]
        
        return "Команда не распознана. Используйте 'помощь' для списка команд."

    def process_audio_transcript(self, transcript):
        """Обработка транскрибированного текста"""
        words = transcript.lower().split()
        self.transcribed_words.extend(words)
        self.word_frequency.update(words)
        
        # Анализируем частоту слов
        common_words = self.word_frequency.most_common(10)
        return {
            "common_words": common_words,
            "total_words": len(self.transcribed_words)
        }

    def get_word_stats(self):
        """Получение статистики по словам"""
        return {
            "total_words": len(self.transcribed_words),
            "unique_words": len(self.word_frequency),
            "common_words": self.word_frequency.most_common(10)
        }
