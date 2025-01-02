import random

class Assistant:
    def __init__(self):
        self.topics = ['Технологии', 'Игры', 'Новости']  # Фиксированные темы
        self.active = False  # Активен ли помощник

    def activate(self):
        """Активирует помощника"""
        self.active = True
        return "Помощник активирован. Какую тему вы хотите обсудить?"

    def deactivate(self):
        """Деактивирует помощника"""
        self.active = False
        return "Помощник отключен."

    def suggest_topics(self, messages):
        """
        Анализирует сообщения чата и предлагает темы для обсуждения.
        В данном примере анализируются ключевые слова в сообщениях.
        """
        topics = self.analyze_chat(messages)
        if topics:
            return f"На основе чата, вот темы для обсуждения: {', '.join(topics)}"
        else:
            return f"Вот предложенные темы: {', '.join(self.topics)}"

    def analyze_chat(self, messages):
        """Простой анализ чата для выявления ключевых слов"""
        keywords = []
        for msg in messages:
            if 'технологии' in msg.lower():
                keywords.append('Технологии')
            elif 'игра' in msg.lower():
                keywords.append('Игры')
            elif 'новость' in msg.lower():
                keywords.append('Новости')
        return keywords if keywords else self.topics

    def respond_to_command(self, command):
        """Ответ помощника на голосовые команды стримера"""
        if 'помощник' in command.lower():
            if 'темы' in command.lower():
                return self.suggest_topics([])
            elif 'статистика' in command.lower():
                return self.provide_statistics()
            elif 'пауза' in command.lower():
                return "Трансляция приостановлена."
            elif 'возобновить' in command.lower():
                return "Трансляция возобновлена."
        return "Команда не распознана."

    def provide_statistics(self):
        """Пример функции для возврата статистики трансляции"""
        viewers = random.randint(10, 100)  # Пример количества зрителей
        return f"Текущая статистика: {viewers} зрителей на стриме."
