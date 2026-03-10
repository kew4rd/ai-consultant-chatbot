# AI Chatbot — Django + Google Colab

Веб-приложение на Django с AI-чат-ботом. Модель запускается на Google Colab и общается с сервером через ngrok.

## Архитектура

```
[Браузер] → [Django сервер] → [Google Colab (AI модель + ngrok)]
```

- **Django** — веб-интерфейс, авторизация, история чатов
- **colab_server.ipynb** — запускает AI модель на Colab и открывает HTTP API через ngrok
- **lora-project.ipynb** — обучение LoRA-адаптеров для модели

## Возможности

- Регистрация и авторизация пользователей
- Два режима консультанта: **Бизнес** и **Юридический**
- История диалогов с возможностью удаления
- Дневные лимиты токенов (Free: 10 000 / Premium: 100 000)

## Структура проекта

```
chatbot_project/
├── chat/                    # Django-приложение
│   ├── models.py            # UserProfile, Conversation, Message
│   ├── views.py             # Логика запросов
│   ├── urls.py
│   ├── templates/chat/
│   └── static/chat/
├── chatbot_project/
│   ├── settings.py
│   └── urls.py
├── colab_server.ipynb       # Сервер AI модели (запускать в Colab)
├── lora-project.ipynb       # Обучение LoRA-адаптеров (опционально)
└── manage.py
```

## Запуск

### 1. Клонировать репозиторий

```bash
git clone <url>
cd chatbot_project
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 3. Установить зависимости

```bash
pip install django requests
```

### 4. Настроить SECRET_KEY

В файле `chatbot_project/settings.py` замените `SECRET_KEY` на свой (никогда не публикуй исходный ключ):

```python
SECRET_KEY = 'your-secret-key-here'
```

Сгенерировать можно командой:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Запустить Colab-сервер

1. Открыть `colab_server.ipynb` в Google Colab
2. Выбрать Runtime → **GPU**
3. Запустить все ячейки
4. Скопировать ngrok URL из вывода (вида `https://xxxx.ngrok-free.app`)
5. Вставить URL в `chatbot_project/settings.py`:

```python
COLAB_API_URL = 'https://xxxx.ngrok-free.app/generate'
```

### 7. Запустить Django

```bash
python manage.py runserver
```

Открыть: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Обучение LoRA-адаптеров (опционально)

`lora-project.ipynb` содержит код для дообучения языковой модели с помощью LoRA-адаптеров. Запускать в Google Colab с GPU.

## Важно

- Django-сервер должен быть запущен **после** того, как Colab-сервер уже работает
- Colab отключается после ~90 минут бездействия — при переподключении ngrok URL изменится
- Не публикуй `SECRET_KEY` и не коммить файл `.env` с секретами
