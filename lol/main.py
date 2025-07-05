import logging
import requests
import random
import os
import signal
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Получаем токен бота из переменных окружения
my_bot_token = os.environ.get('YOUR_BOT_TOKEN', '')
if not my_bot_token:
    raise ValueError("Не установлен токен бота. Добавьте YOUR_BOT_TOKEN в секреты.")

# Добавьте OPENWEATHER_API_KEY в секреты
openweather_api_key = os.environ.get('OPENWEATHER_API_KEY', '')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Словарь для отслеживания пользователей, которые уже вызывали /start
user_start_history = set()

# Переменная для отслеживания режима логирования
log_mode_enabled = True

# Списки мудрых советов и анекдотов
wise_advices = [
    "Будьте благодарны за то, что у вас есть. Цените то, что имеете, вместо того, чтобы всегда стремиться к большему.",
    "Не бойтесь ошибаться. Ошибки – это часть обучения и роста.",
    "Учитесь на своих ошибках. Не повторяйте одни и те же ошибки дважды.",
    "Не бойтесь просить о помощи. Обращение за помощью – признак силы, а не слабости.",
    "Всегда будьте честны. Честность – основа доверия и крепких отношений.",
    "Уважайте чужое мнение, даже если оно отличается от вашего.",
    "Будьте терпеливы. Не все происходит сразу.",
    "Не торопитесь с выводами. Дайте себе время обдумать ситуацию.",
    "Слушайте больше, чем говорите.",
    "Верьте в себя. Ваша уверенность в себе – ваш главный союзник.",
    "Не сравнивайте себя с другими. Сравнивайте себя только с собой вчерашним.",
    "Будьте добры. Доброта возвращается бумерангом.",
    "Находите время для себя. Забота о себе – залог вашего благополучия.",
    "Не забывайте о своих мечтах. Мечты придают смысл жизни.",
    "Не бойтесь перемен. Перемены – это возможность для роста."
]

jokes = [
    "Блондинка приходит в автосервис:\n— У меня машина не заводится.\n— А бензин есть?\n— Конечно, есть! Я даже полбака залила!",
    "Муж звонит жене:\n— Дорогая, я сегодня задержусь.\n— А ты где?\n— На работе, в кабинете.\n— А что у тебя за спиной?\n— Стенка.",
    "Учитель спрашивает ученика:\n— Почему ты опоздал?\n— У меня будильник сломался.\n— А почему ты не попросил маму тебя разбудить?\n— Она тоже опаздывала на работу.",
    "Новый русский приходит к врачу:\n— Доктор, у меня проблема. Я не могу заснуть!\n— А что вы делаете на ночь?\n— Ну, обычно я считаю деньги...\n— Так и считайте!\n— Так я уже весь день считаю, а мне все мало!",
    "Солдат спрашивает у сержанта:\n— Товарищ сержант, а что такое марш-бросок?\n— Это когда мы бежим, а вы, как хотите.",
    "Блондинка покупает карту. Продавец спрашивает:\n— Куда ехать будете?\n— Пока не знаю, но чтобы место было!",
    "Жена спрашивает мужа:\n— Дорогой, ты меня любишь?\n— Конечно, люблю. Ты же у меня самая лучшая!\n— А если я потолстею?\n— Ну, значит, у меня будет больше любимой женщины."
]

# Факты для команды .муфакт
interesting_facts = [
    "🦆 Утки не промокают в воде благодаря специальному маслу, которое выделяют железы у основания хвоста.",
    "🐙 Осьминоги имеют три сердца и голубую кровь.",
    "🌍 Земля вращается со скоростью примерно 1670 км/ч на экваторе.",
    "🧠 Человеческий мозг потребляет около 20% всей энергии организма.",
    "🍯 Мёд никогда не портится - археологи находили съедобный мёд в египетских пирамидах.",
    "🦋 Бабочки чувствуют вкус ногами.",
    "🐘 Слоны боятся пчёл и при их звуке могут убежать.",
    "❄️ Снежинки на 90% состоят из воздуха.",
    "🌙 На Луне ваш вес был бы в 6 раз меньше, чем на Земле.",
    "🐨 Коалы спят до 22 часов в день."
]

# Мотивационные цитаты для команды .муцитата
motivational_quotes = [
    "💪 'Успех - это способность идти от неудачи к неудаче, не теряя энтузиазма.' - Уинстон Черчилль",
    "🌟 'Единственный способ делать великую работу - любить то, что ты делаешь.' - Стив Джобс",
    "🚀 'Будущее принадлежит тем, кто верит в красоту своих мечтаний.' - Элеанор Рузвельт",
    "⭐ 'Не ждите идеального момента. Возьмите момент и сделайте его идеальным.'",
    "🎯 'Ваше ограничение - это только ваше воображение.'",
    "💎 'Великие дела совершаются не силой, а упорством.' - Сэмюэл Джонсон",
    "🔥 'Препятствия не должны вас останавливать. Если вы натыкаетесь на стену, не поворачивайтесь и не сдавайтесь.' - Майкл Джордан",
    "🌈 'Жизнь на 10% состоит из того, что с вами происходит, и на 90% из того, как вы на это реагируете.'",
    "💡 'Инновация отличает лидера от последователя.' - Стив Джобс",
    "🎪 'Мечтайте так, как будто будете жить вечно. Живите так, как будто умрёте сегодня.' - Джеймс Дин"
]

# Загадки для команды .музагадка
riddles = [
    {"question": "🤔 Что можно увидеть с закрытыми глазами?", "answer": "Сон"},
    {"question": "🤔 Что становится больше, если его поставить вверх ногами?", "answer": "Число 6"},
    {"question": "🤔 Что всегда идёт, но никогда не приходит?", "answer": "Завтра"},
    {"question": "🤔 У меня есть города, но нет домов. У меня есть горы, но нет деревьев. У меня есть вода, но нет рыбы. Что я?", "answer": "Карта"},
    {"question": "🤔 Что можно поймать, но нельзя бросить?", "answer": "Насморк"},
    {"question": "🤔 Чем больше из неё берёшь, тем больше она становится. Что это?", "answer": "Яма"},
    {"question": "🤔 Что имеет руки, но не может хлопать?", "answer": "Часы"},
    {"question": "🤔 Что поднимается вверх, но никогда не опускается вниз?", "answer": "Возраст"},
    {"question": "🤔 У меня есть ключи, но нет замков. У меня есть пространство, но нет места. Что я?", "answer": "Клавиатура"},
    {"question": "🤔 Что всегда перед вами, но вы этого не видите?", "answer": "Будущее"}
]

# Хранилище активных загадок для пользователей
user_riddles = {}

# Реплики для мини-общения в группах
chat_responses = [
    "Приветик! Как у тебя дела? 😊",
    "Привет! Как дела-то? 🌟",
    "Хей! Что нового? 😄",
    "Салют! Как настроение? 🎉",
    "Здравствуй! Как поживаешь? 👋",
    "Привет! Что происходит? 🤔",
    "Приветики! Как жизнь? 🌈",
    "Хай! Как сам? 😎",
    "Привет! Как дела, дорогой? 💕",
    "Здорово! Как твои дела? 🚀",
    "Привет! Что делаешь? 🤗",
    "Хэй! Как дела у тебя? 🌸",
    "Привет! Как проходит день? ☀️",
    "Салют! Как дела, друг? 🤝",
    "Приветствую! Как поживаешь? 🎊",
    "Привет! Что нового в жизни? 📚",
    "Хай! Как настроение сегодня? 😃",
    "Привет! Как дела, красавчик? 💪",
    "Здорово! Что у тебя нового? 🎯",
    "Привет! Как прошел день? 🌅",
    "Хэй! Как дела, милый? 💖",
    "Привет! Что интересного? 🎭",
    "Салют! Как твое настроение? 🎪",
    "Приветик! Как жизнь молодая? 🌺",
    "Привет! Как дела, чемпион? 🏆",
    "Хай! Что происходит в жизни? 🌍",
    "Привет! Как дела, солнышко? ☀️",
    "Здорово! Как поживаешь, дружок? 🐻",
    "Приветствую! Как дела идут? 🎸",
    "Привет! Что нового узнал? 🔍",
    "Хэй! Как дела, умница? 🧠",
    "Привет! Как настроение, красотка? 💄",
    "Салют! Что хорошего случилось? 🍀",
    "Приветик! Как дела, герой? 🦸",
    "Привет! Как жизнь течет? 🌊",
    "Хай! Что делаешь интересного? 🎨",
    "Привет! Как дела, звезда? ⭐",
    "Здорово! Как поживаешь, дорогой? 💝",
    "Приветствую! Как дела, капитан? ⚓",
    "Привет! Что нового в мире? 🌎",
    "Хэй! Как дела, мастер? 🛠️"
]


def check_openweather_status():
    """Проверить статус OpenWeather API."""
    try:
        if not openweather_api_key:
            return "недоступен", "API ключ не установлен"
        
        # Шаг 1: Проверяем доступность API с запросом к Москве
        moscow_url = f"http://api.openweathermap.org/data/2.5/weather?q=Moscow,RU&appid={openweather_api_key}&units=metric&lang=ru"
        moscow_response = requests.get(moscow_url, timeout=5)
        
        if moscow_response.status_code == 401:
            return "недоступен", "неверный API ключ"
        elif moscow_response.status_code != 200:
            return "доступен", "не обрабатывает"
        
        moscow_data = moscow_response.json()
        # Проверяем, что получили корректные данные для Москвы
        if 'main' not in moscow_data or 'temp' not in moscow_data['main']:
            return "доступен", "не обрабатывает"
        
        # Шаг 2: Проверяем совершенно другой город - Токио
        tokyo_url = f"http://api.openweathermap.org/data/2.5/weather?q=Tokyo,JP&appid={openweather_api_key}&units=metric&lang=ru"
        tokyo_response = requests.get(tokyo_url, timeout=5)
        
        if tokyo_response.status_code != 200:
            return "доступен", "не обрабатывает"
        
        tokyo_data = tokyo_response.json()
        # Проверяем, что получили корректные данные для Токио
        if 'main' not in tokyo_data or 'temp' not in tokyo_data['main']:
            return "доступен", "не обрабатывает"
        
        # Шаг 3: Сравниваем данные между Москвой и Токио
        moscow_temp = moscow_data['main']['temp']
        moscow_humidity = moscow_data['main']['humidity']
        moscow_pressure = moscow_data['main']['pressure']
        moscow_weather = moscow_data['weather'][0]['main']
        
        tokyo_temp = tokyo_data['main']['temp']
        tokyo_humidity = tokyo_data['main']['humidity']
        tokyo_pressure = tokyo_data['main']['pressure']
        tokyo_weather = tokyo_data['weather'][0]['main']
        
        # Проверяем точное совпадение данных (крайне маловероятно для таких удалённых городов)
        if (moscow_temp == tokyo_temp and 
            moscow_humidity == tokyo_humidity and 
            moscow_pressure == tokyo_pressure and
            moscow_weather == tokyo_weather):
            return "доступен", "не обрабатывает (идентичные данные)"
        
        # Дополнительная проверка: если разности слишком малы для городов на разных континентах
        temp_diff = abs(moscow_temp - tokyo_temp)
        humidity_diff = abs(moscow_humidity - tokyo_humidity)
        pressure_diff = abs(moscow_pressure - tokyo_pressure)
        
        # Для городов на расстоянии ~7000км в разных климатических зонах
        if (temp_diff < 1 and humidity_diff < 5 and pressure_diff < 5):
            return "доступен", "не обрабатывает (подозрительно схожие данные)"
        
        # Шаг 4: Дополнительная проверка с Зеленодольском для исходной задачи
        zelenodolsk_url = f"http://api.openweathermap.org/data/2.5/weather?q=Zelenodolsk,RU&appid={openweather_api_key}&units=metric&lang=ru"
        zelenodolsk_response = requests.get(zelenodolsk_url, timeout=5)
        
        if zelenodolsk_response.status_code == 200:
            zelenodolsk_data = zelenodolsk_response.json()
            if 'main' in zelenodolsk_data:
                zelenodolsk_temp = zelenodolsk_data['main']['temp']
                zelenodolsk_humidity = zelenodolsk_data['main']['humidity'] 
                zelenodolsk_pressure = zelenodolsk_data['main']['pressure']
                
                # Москва vs Зеленодольск
                if (moscow_temp == zelenodolsk_temp and 
                    moscow_humidity == zelenodolsk_humidity and 
                    moscow_pressure == zelenodolsk_pressure):
                    return "доступен", "не обрабатывает (Москва=Зеленодольск)"
        
        return "доступен", "работает (данные могут быть неточными)"
            
    except requests.exceptions.Timeout:
        return "недоступен", "таймаут соединения"
    except requests.exceptions.RequestException:
        return "недоступен", "ошибка сети"
    except Exception:
        return "недоступен", "неизвестная ошибка"


def get_weather(location):
    """Получить погоду для указанного места."""
    try:
        # Получаем данные о погоде от OpenWeather
        if openweather_api_key:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={openweather_api_key}&units=metric&lang=ru"
            response = requests.get(weather_url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Извлекаем данные о погоде
                temp = round(data['main']['temp'])
                feels_like = round(data['main']['feels_like'])
                humidity = data['main']['humidity']
                description = data['weather'][0]['description']
                wind_speed = data['wind']['speed']
                pressure = data['main']['pressure']
                
                # Получаем название города из ответа API
                city_name = data['name']
                country = data['sys']['country']

                # Получаем координаты
                lat = data['coord']['lat']
                lon = data['coord']['lon']

                weather_info = (
                    f"🌍 Погода в {city_name}, {country}:\n\n"
                    f"🌡️ Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"☁️ Описание: {description.capitalize()}\n"
                    f"💨 Скорость ветра: {wind_speed} м/с\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"🔽 Давление: {pressure} гПа\n"
                    f"📍 Координаты: {lat:.2f}, {lon:.2f}"
                )
                return weather_info
            elif response.status_code == 404:
                return f"❌ Город '{location}' не найден. Проверьте правильность написания или попробуйте формат 'Страна, Город'."
            else:
                return f"❌ Ошибка API OpenWeather (код {response.status_code}). Попробуйте позже."
        else:
            # Если нет API ключа, используем заглушку
            return f"⚠️ Демо-режим для {location}:\n🌤️ Температура: 15°C\n💨 Ветер: 5 м/с\n💧 Влажность: 60%\n\n📝 Для получения реальной погоды добавьте OPENWEATHER_API_KEY в секреты"
    except requests.exceptions.Timeout:
        logger.error(f"Таймаут при запросе погоды для {location}")
        return f"❌ Превышено время ожидания ответа для {location}. Попробуйте позже."
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при получении погоды: {e}")
        return f"❌ Ошибка сети при получении данных о погоде для {location}"
    except KeyError as e:
        logger.error(f"Неожиданный формат ответа API: {e}")
        return f"❌ Ошибка обработки данных о погоде для {location}"
    except Exception as e:
        logger.error(f"Неожиданная ошибка получения погоды: {e}")
        return f"❌ Неожиданная ошибка при получении данных о погоде для {location}"


def generate_password(length=12):
    """Генерирует случайный пароль."""
    import string
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))


def flip_coin():
    """Подбрасывает монетку."""
    result = random.choice(["Орёл", "Решка"])
    emoji = "🪙" if result == "Орёл" else "🎯"
    return f"{emoji} Результат: {result}!"


def roll_dice(sides=6):
    """Бросает кубик."""
    result = random.randint(1, sides)
    return f"🎲 Выпало: {result}"


def get_random_color():
    """Генерирует случайный цвет."""
    colors = [
        "🔴 Красный", "🟠 Оранжевый", "🟡 Жёлтый", "🟢 Зелёный", 
        "🔵 Синий", "🟣 Фиолетовый", "🟤 Коричневый", "⚫ Чёрный", 
        "⚪ Белый", "🩷 Розовый", "🩵 Голубой", "🟩 Салатовый"
    ]
    return f"🎨 Ваш случайный цвет: {random.choice(colors)}"


def get_number_fact(number):
    """Возвращает интересный факт о числе."""
    facts = {
        1: "1 - единственное число, которое не является ни простым, ни составным.",
        7: "7 считается счастливым числом во многих культурах.",
        13: "13 считается несчастливым числом в западной культуре.",
        42: "42 - 'ответ на главный вопрос жизни, вселенной и всего такого' по Дугласу Адамсу.",
        100: "100 - это совершенный квадрат (10²).",
        365: "365 дней в обычном году.",
        1000: "1000 - это куб числа 10."
    }
    
    if number in facts:
        return f"🔢 {facts[number]}"
    elif number % 2 == 0:
        return f"🔢 {number} - чётное число."
    else:
        return f"🔢 {number} - нечётное число."


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send a message when the command /start is issued."""
  user = update.effective_user
  user_id = user.id

  # Проверяем, вызывается ли команда в группе
  if update.message.chat.type in ['group', 'supergroup']:
    # Отправляем приветственное сообщение для группы с анекдотом
    random_joke = random.choice(jokes)
    welcome_message = (
      "👋 Привет! Я бот который может показывать погоду, а также мудрые советы и анекдоты! 🤖✨\n\n"
      "🌤️ Чтобы узнать погоду в регионе напишите: .мупогодка Страна, Город\n\n"
      "😄 Анекдот для поднятия настроения:\n\n"
      f"😂 {random_joke}\n\n"
      "👥 Создатели:\n"
      "🎨 Лина (@star_linochka дизайнер)\n"
      "💻 Тархун (@debilww999 программист)\n\n"
      "💬 Приятного общения! 🎉\n"
      "Этот бот был создан с любовью и заботой о вашем комфорте! 💖"
    )
    await update.message.reply_text(welcome_message)
  else:
    # Проверяем, второй ли раз пользователь вызывает /start
    if user_id in user_start_history:
      # Отправляем случайный мудрый совет и анекдот
      random_advice = random.choice(wise_advices)
      random_joke = random.choice(jokes)

      message = (
        f"✨ Мудрый совет для {user.mention_html()}:\n\n"
        f"🧠 {random_advice}\n\n"
        f"😄 А вот анекдот для поднятия настроения:\n\n"
        f"😂 {random_joke}\n\n"
        f"🎭 Хорошего дня! 🌟"
      )

      await update.message.reply_html(message)
    else:
      # Добавляем пользователя в историю и отправляем стандартное приветствие
      user_start_history.add(user_id)

      welcome_message = f"Добро пожаловать, {user.mention_html()}! 🎉 Я бот который может показывать погоду через команду .мупогодка Страна, Город"

      # Создаем inline клавиатуру с кнопкой "Добавить в чат"
      keyboard = [
        [InlineKeyboardButton("➕ Добавить в чат", url=f"https://t.me/{context.bot.username}?startgroup=true")]
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)

      await update.message.reply_html(
          welcome_message,
          reply_markup=reply_markup,
      )


async def new_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send welcome message when bot is added to a chat."""
  # Проверяем, что бот был добавлен в чат
  for member in update.message.new_chat_members:
    if member.id == context.bot.id:
      welcome_message = (
        "👋 Привет! Я бот который может показывать погоду, а также мудрые советы и анекдоты! 🤖✨\n\n"
        "🌤️ Чтобы узнать погоду в регионе напишите: .мупогодка Страна, Город\n\n"
        "👥 Создатели:\n"
        "🎨 Лина (@star_linochka дизайнер)\n"
        "💻 Тархун (@debilww999 программист)\n\n"
        "💬 Приятного общения! 🎉"
      )
      await update.message.reply_text(welcome_message)
      break


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send a message when the command /help is issued."""
  help_text = (
    "📋 Доступные команды:\n\n"
    "🏠 /start - Приветствие\n"
    "❓ /help - Список команд\n\n"
    "🌤️ .мупогодка [город] - Показать погоду\n"
    "🏓 .мупинг - Проверить статус бота\n"
    "😂 .муанекдот - Случайный анекдот\n"
    "💡 .мусовет - Мудрый совет\n"
    "🌟 .муцитата - Мотивационная цитата\n"
    "🧠 .муфакт - Интересный факт\n"
    "🤔 .музагадка - Загадка\n"
    "🪙 .муорёл - Подбросить монетку\n"
    "🎲 .мукубик [число] - Бросить кубик\n"
    "🔐 .мупароль [длина] - Генератор паролей\n"
    "🎨 .муцвет - Случайный цвет\n"
    "🔢 .мучисло [число] - Факт о числе\n"
    "⭐ .оценить - Оценить бота\n\n"
    "💬 В группах бот отвечает на упоминания!"
  )
  await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  global last_active_chat_id
  user_message = update.message.text

  # Сохраняем ID последнего активного чата
  last_active_chat_id = update.message.chat_id

  # Проверяем, что сообщение содержит текст
  if not user_message:
    await update.message.reply_text("Отправьте текст для создания стилизованного изображения.")
    return

  # Добавляем отладочный вывод
  if log_mode_enabled:
    logger.info(f"Получено сообщение: '{user_message}' от пользователя {update.message.from_user.id}")

  # Проверяем команду пинга ПЕРВЫМ
  if user_message.startswith('.мупинг'):
    # Проверяем права доступа
    user_id = update.message.from_user.id
    if user_id != 7312342436:
      await update.message.reply_text("❌ Только создатель тархун может использовать эту команду")
      return
    
    # Измеряем время отклика (псевдо-пинг)
    import time
    start_time = time.time()
    
    # Сначала отправляем быстрый ответ с базовой информацией
    log_status = "on" if log_mode_enabled else "off"
    quick_ping = round((time.time() - start_time) * 1000)
    
    await update.message.reply_text(f"🏓 PING: {quick_ping}ms\n🔍 Проверяю OpenWeather...")
    
    # Проверяем статус OpenWeather
    openweather_status, openweather_details = check_openweather_status()
    
    end_time = time.time()
    total_time = round((end_time - start_time) * 1000)  # в миллисекундах
    
    # Получаем дополнительную информацию о системе
    import platform
    import psutil
    import sys
    from datetime import datetime
    
    # Получаем информацию о системе
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    memory_usage = psutil.virtual_memory().percent
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Отправляем полный ответ
    ping_response = (
        f"✅ Полная диагностика ({total_time}ms):\n"
        f"🏓 PING: {quick_ping}ms\n"
        f"🌤️ OPENWEATHER: {openweather_status}, {openweather_details}\n"
        f"📋 Log mode: {log_status}\n"
        f"🖥️ CPU: {cpu_usage}%\n"
        f"💾 RAM: {memory_usage}%\n"
        f"🐍 Python: {sys.version.split()[0]}\n"
        f"⏱️ Uptime: {str(uptime).split('.')[0]}\n"
        f"📊 Active users: {len(user_start_history)}\n"
        f"🔧 Platform: {platform.system()} {platform.release()}"
    )
    
    await update.message.reply_text(ping_response)
    return

  # Новые команды
  if user_message == '.муанекдот':
    joke = random.choice(jokes)
    await update.message.reply_text(f"😂 {joke}")
    return

  if user_message == '.мусовет':
    advice = random.choice(wise_advices)
    await update.message.reply_text(f"💡 {advice}")
    return

  if user_message == '.муцитата':
    quote = random.choice(motivational_quotes)
    await update.message.reply_text(quote)
    return

  if user_message == '.муфакт':
    fact = random.choice(interesting_facts)
    await update.message.reply_text(fact)
    return

  if user_message == '.музагадка':
    user_id = update.message.from_user.id
    riddle = random.choice(riddles)
    user_riddles[user_id] = riddle["answer"].lower()
    await update.message.reply_text(f"{riddle['question']}\n\n💭 Напишите ваш ответ!")
    return

  if user_message == '.муорёл':
    result = flip_coin()
    await update.message.reply_text(result)
    return

  if user_message.startswith('.мукубик'):
    parts = user_message.split()
    sides = 6
    if len(parts) > 1 and parts[1].isdigit():
      sides = int(parts[1])
      if sides < 2:
        sides = 6
      elif sides > 100:
        sides = 100
    result = roll_dice(sides)
    await update.message.reply_text(result)
    return

  if user_message.startswith('.мупароль'):
    parts = user_message.split()
    length = 12
    if len(parts) > 1 and parts[1].isdigit():
      length = int(parts[1])
      if length < 4:
        length = 4
      elif length > 50:
        length = 50
    password = generate_password(length)
    await update.message.reply_text(f"🔐 Ваш пароль: `{password}`", parse_mode='Markdown')
    return

  if user_message == '.муцвет':
    color = get_random_color()
    await update.message.reply_text(color)
    return

  if user_message.startswith('.мучисло'):
    parts = user_message.split()
    if len(parts) > 1 and parts[1].isdigit():
      number = int(parts[1])
      fact = get_number_fact(number)
      await update.message.reply_text(fact)
    else:
      await update.message.reply_text("🔢 Использование: .мучисло [число]\nНапример: .мучисло 42")
    return

  if user_message == '.оценить':
    # Создаем клавиатуру с кнопками оценки от 1 до 6
    keyboard = [
      [
        InlineKeyboardButton("1", callback_data="rating_1"),
        InlineKeyboardButton("2", callback_data="rating_2"),
        InlineKeyboardButton("3", callback_data="rating_3")
      ],
      [
        InlineKeyboardButton("4", callback_data="rating_4"),
        InlineKeyboardButton("5", callback_data="rating_5"),
        InlineKeyboardButton("6", callback_data="rating_6")
      ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    rating_message = (
      "⭐ Вам нравится бот? Поставьте оценку этому боту!\n\n"
      "1 - ужасный\n"
      "3 - не плохо\n"
      "6 - превосходный\n\n"
      "👇 Выберите оценку:"
    )
    
    await update.message.reply_text(rating_message, reply_markup=reply_markup)
    return

  # Проверяем ответы на загадки
  user_id = update.message.from_user.id
  if user_id in user_riddles:
    correct_answer = user_riddles[user_id]
    user_answer = user_message.lower().strip()
    
    if user_answer == correct_answer:
      await update.message.reply_text("🎉 Правильно! Отличная работа! 👏")
      del user_riddles[user_id]
      return
    elif len(user_answer) > 2:  # Только если ответ не слишком короткий
      await update.message.reply_text(f"❌ Неправильно. Правильный ответ: {user_riddles[user_id].title()}")
      del user_riddles[user_id]
      return

  # Проверяем команды погоды
  if user_message.startswith('.погода ') or user_message.startswith('.мупогодка '):
    # Обработка команды погоды
    if user_message.startswith('.погода '):
      location = user_message[8:]  # Убираем ".погода "
    elif user_message.startswith('.мупогодка '):
      location = user_message[11:]  # Убираем ".мупогодка "
    else:
      location = ""

    if not location.strip():
      await update.message.reply_text("Используйте команду: .мупогодка Страна, Город\nНапример: .мупогодка Россия, Москва")
      return

    # Получаем реальную погоду
    weather_info = get_weather(location.strip())
    await update.message.reply_text(weather_info)
    return

  # Проверяем, упоминается ли бот в группе
  if update.message.chat.type in ['group', 'supergroup']:
    bot_username = context.bot.username
    message_lower = user_message.lower()
    user_id = update.message.from_user.id

    # Проверяем различные способы упоминания бота
    mention_patterns = [
        f"@{bot_username}",
        f"@{bot_username.lower()}",
        "бот",
        "bot",
        "привет",
        "hi",
        "hello"
    ]

    # Специальная обработка для пользователя Лины (ID: 7617284608)

    # Также проверяем прямые упоминания через Telegram API
    mentioned = False
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                mention_text = user_message[entity.offset:entity.offset + entity.length]
                if mention_text.lower() == f"@{bot_username.lower()}":
                    mentioned = True
                    break

    # Проверяем текстовые упоминания
    if not mentioned:
        for pattern in mention_patterns:
            if pattern in message_lower:
                mentioned = True
                break

    if mentioned:
        # Специальная обработка для пользователя Лины (ID: 7617284608)
        if user_id == 7617284608:
            lina_responses = [
                "Приветик, Лина! Как у тебя дела? 😊",
                "Привет, Линочка! Как дела-то? 🌟", 
                "Хей, Лина! Что нового? 😄",
                "Салют, Линочка! Как настроение? 🎉",
                "Здравствуй, Лина! Как поживаешь? 👋",
                "Привет, Линочка! Что происходит? 🤔",
                "Приветики, Лина! Как жизнь? 🌈",
                "Хай, Линочка! Как сам? 😎",
                "Привет, Лина! Как дела, дорогая? 💕",
                "Здорово, Линочка! Как твои дела? 🚀",
                "Привет, Лина! Что делаешь? 🤗",
                "Хэй, Линочка! Как дела у тебя? 🌸",
                "Привет, Лина! Как проходит день? ☀️",
                "Салют, Линочка! Как дела, друг? 🤝",
                "Приветствую, Лина! Как поживаешь? 🎊",
                "Привет, Линочка! Что нового в жизни? 📚",
                "Хай, Лина! Как настроение сегодня? 😃",
                "Привет, Линочка! Как дела, красавица? 💪",
                "Здорово, Лина! Что у тебя нового? 🎯",
                "Привет, Линочка! Как прошел день? 🌅"
            ]
            response = random.choice(lina_responses)
        else:
            # Отвечаем случайной репликой для остальных
            response = random.choice(chat_responses)

        await update.message.reply_text(response)
        return


# Переменная для хранения последнего чата, где бот был активен
last_active_chat_id = None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks for rating."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("rating_"):
        rating = query.data.split("_")[1]
        
        # Создаем ответное сообщение в зависимости от оценки
        if rating == "1":
            response = "😔 Спасибо за честность! Мы будем работать над улучшением бота."
        elif rating == "2":
            response = "😐 Спасибо за отзыв! Мы стараемся стать лучше."
        elif rating == "3":
            response = "🙂 Спасибо! Рады, что бот вам не плохо подходит."
        elif rating == "4":
            response = "😊 Отлично! Спасибо за хорошую оценку!"
        elif rating == "5":
            response = "😄 Замечательно! Очень рады, что вам нравится!"
        elif rating == "6":
            response = "🤩 Превосходно! Спасибо за высшую оценку! Вы лучшие!"
        else:
            response = "❓ Неожиданная оценка, но спасибо!"
        
        response += f"\n\n⭐ Ваша оценка: {rating}/6"
        
        # Редактируем сообщение, убирая кнопки
        await query.edit_message_text(text=response)


async def send_goodbye_message(application):
    """Отправить прощальное сообщение в последний активный чат."""
    global last_active_chat_id
    if last_active_chat_id:
        try:
            await application.bot.send_message(
                chat_id=last_active_chat_id,
                text="🌙 бот спит!"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить прощальное сообщение: {e}")

def main() -> None:
  """Start the bot."""
  # Create the Application and pass it your bot's token.
  application = Application.builder().token(my_bot_token).build()

  # on different commands - answer in Telegram
  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("help", help_command))

  # handle new chat members (when bot is added to group)
  application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_member))

  # handle button callbacks
  application.add_handler(CallbackQueryHandler(button_callback))

  # on non command i.e message - handle weather or stylize text
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

  # Добавляем обработчик завершения работы приложения
  async def post_stop_callback(app):
      """Callback который вызывается после остановки приложения."""
      await send_goodbye_message(app)
      logger.info("🌙 бот спит!")

  application.post_stop = post_stop_callback

  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()