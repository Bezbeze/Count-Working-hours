import telebot
import sqlite3
from datetime import datetime, timedelta
from time import sleep
from telebot import types

# Создаем бота с помощью токена
bot = telebot.TeleBot(TOKEN)


# Создаем базу данных SQL для хранения информации о рабочих часах
conn = sqlite3.connect('work_hours.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS workers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_name TEXT NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT
    )
''')
conn.commit()
conn.close()

# Функция для записи начала рабочего дня
def start_workday(worker_name):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    start_time = now.strftime("%H:%M:%S")

    # Проверяем, что строка с указанной датой еще не существует 
    cursor.execute('SELECT * FROM workers WHERE date = ? AND worker_name = ?', (date, worker_name))
    existing_row = cursor.fetchone()
    if existing_row:
        conn.close()
        return f"Для {worker_name} уже начат рабочий день {existing_row[2]} в {existing_row[3]}"

    # Если строка с указанной датой отсутствует, добавляем новую строку
    cursor.execute('''
        INSERT INTO workers (worker_name, date, start_time)
        VALUES (?, ?, ?)
    ''', (worker_name, date, start_time))
    conn.commit()
    conn.close()
    return f"Рабочий день начат для {worker_name} в {start_time}"

# Функция для записи окончания рабочего дня
def end_workday(worker_name):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    yesterday = now + timedelta(days=-1)
    yesterday = yesterday.strftime("%Y-%m-%d")
    end_time = now.strftime("%H:%M:%S")
    
    cursor.execute('''
        SELECT * FROM workers 
        WHERE worker_name = ? AND date = ?
    ''', (worker_name, yesterday,))
    chec_end = cursor.fetchone()
    
    #если закрывать смену после полуночи.  
    if chec_end and chec_end[4] == None:
        cursor.execute('''
            UPDATE workers
            SET end_time = ?
            WHERE worker_name = ? AND date = ?
        ''', (end_time, worker_name, yesterday))
        conn.commit()
        conn.close()
        return f"Рабочий день завершен для {worker_name} в {end_time}"        
        
    cursor.execute('''
        UPDATE workers
        SET end_time = ?
        WHERE worker_name = ? AND date = ?
    ''', (end_time, worker_name, date))
    conn.commit()
    conn.close()
    
    total_hours_today = get_worker_info(worker_name, date)
    if total_hours_today:
        total_hours = count_hours(total_hours_today)
        return f"Рабочий день завершен для {worker_name} в {end_time},\n Всего часов сегодня: {total_hours[0]}ч {total_hours[1]}мин"
    return"Вы не начинали день"

# Функция для получения информации о рабочем дне
def get_worker_info(worker_name, date):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM workers
        WHERE worker_name = ? AND date = ?
    ''', (worker_name, date))
    worker_info = cursor.fetchone()
    conn.close()
    return worker_info

# Подсчет рабочих часов, принимает всю строку из SQL таблицы
def count_hours(worker_date):
    start_today = datetime.strptime(worker_date[3], "%H:%M:%S")
    end_today = datetime.strptime(worker_date[4], "%H:%M:%S")
    if end_today < start_today:
        end_today += timedelta(days=1)
    hours_time = end_today - start_today
    hours_time = hours_time.total_seconds() 
    hours = int(hours_time // 3600)
    minut = int(hours_time % 3600 // 60)
    total_hours  = (hours, minut, hours_time) # hours_time - всего в секундах
    return total_hours

#всего выводит по строкам сколько каждый день за месяц работал
def hours_month(worker_name, month):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, start_time, end_time
        FROM workers
        WHERE worker_name = ? AND strftime('%m', date) = ?
        GROUP BY date
    ''', (worker_name, month))
    total_hours = cursor.fetchall()
    conn.close()
    if len(total_hours) > 0:
        reply = "Ваши рабочие часы:\n"
        for row in total_hours:
            date = row[0]
            if row[1] and row[2]:
                format_row = [''] + [''] + list(row)          #функция count_hours принимает массив из 5-ти эл-тов
                res_hours = count_hours(format_row)
                hours = str(res_hours[0]) + 'ч ' + str(res_hours[1]) + 'мин'
            
            else: hours = 'нет данных об ч.'
            if row[1] and row[2]:
                reply += f"{date[5:]}: с {row[1][:5]} до {row[2][:5]}, {hours}\n"
    else:
        reply = "Нет данных о рабочих часах."
    return reply

#итого часов за месяц
def total_hours_month(worker_name, month):
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, start_time, end_time
        FROM workers
        WHERE worker_name = ?  AND strftime('%m', date) = ?
        GROUP BY date
    ''', (worker_name, month))
    total_hours = cursor.fetchall()
    conn.close()
    if total_hours is not None:
        reply = 0
        for row in total_hours:
            if row[1] and row[2]:
                format_row = [''] + [''] + list(row)          #функция count_hours принимает массив из 5-ти эл-тов
                reply += count_hours(format_row)[2]
        reply = f'Вы отработали {int(reply // 3600)} ч.'
    else:
        reply = "Нет данных о рабочих часах."
    return reply
    

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_handler(message):
    keyboard = types.ReplyKeyboardMarkup()
    start_button = types.KeyboardButton('Начать рабочий день')
    stop_button = types.KeyboardButton('Остановить рабочий день')
    dates_button = types.KeyboardButton('Показать даты и часы')
    total_last_month_button = types.KeyboardButton('итого в прош.мес')
    total_button = types.KeyboardButton('Итого часов')
    change_time_button = types.KeyboardButton('Изменить время')
    keyboard.row(start_button, stop_button,  change_time_button)
    keyboard.add(dates_button, total_button, total_last_month_button)
    bot.send_message(
        message.chat.id, 
        "Привет! Я бот для записи рабочих часов. Чтобы начать рабочий день, нажмите кнопку 'Начать', а чтобы закончить - кнопку 'Остановить'. 'Показать дату и время' для отображения даты-времени, 'Итого часов' для отображения общего числа часов за месяц.",
        reply_markup=keyboard
    )

# Обработчик кнопки "Старт"
@bot.message_handler(func=lambda message: message.text == 'Начать рабочий день')
def start_workday_handler(message):
    worker_name = message.from_user.first_name
    reply = start_workday(worker_name)
    bot.send_message(message.chat.id, reply)

# Обработчик кнопки "Стоп"
@bot.message_handler(func=lambda message: message.text == 'Остановить рабочий день')
def end_workday_handler(message):
    worker_name = message.from_user.first_name
    reply = end_workday(worker_name)
    bot.send_message(message.chat.id, reply)

# Обработчик кнопки "Итого"
@bot.message_handler(func=lambda message: message.text == 'Итого часов')
def total_hours_handler(message):
    worker_name = message.from_user.first_name
    now = datetime.now()
    month = now.strftime("%m")
    reply = total_hours_month(worker_name, month)
    bot.send_message(message.chat.id, reply)

# Обработчик кнопки "Даты"
@bot.message_handler(func=lambda message: message.text == 'Показать даты и часы')
def total_hours_handler(message):
    worker_name = message.from_user.first_name
    now = datetime.now()
    month = now.strftime("%m")
    reply = hours_month(worker_name, month)
    bot.send_message(message.chat.id, reply) 
    
# Обработчик кнопки "итого в прош.меc"
@bot.message_handler(func=lambda message: message.text == 'итого в прош.мес')
def total_hours_handler(message):
    worker_name = message.from_user.first_name
    now = datetime.now()
    previous_month = (now.month -1) % 12
    if previous_month ==  0:
        previous_month = 12
    previous_month = "{:02d}".format(previous_month)
    reply = total_hours_month(worker_name, previous_month)
    bot.send_message(message.chat.id, reply)        
    reply = hours_month(worker_name, previous_month)
    bot.send_message(message.chat.id, reply)     
    
# Обработчик кнопки 'Изменить время'
@bot.message_handler(func=lambda message: message.text == 'Изменить время')
def change_time_handler(message):
    bot.send_message(message.chat.id, 'Введите дату, время начала раб.дняб время окончания раб.дня разделив пробелами в формате год-месяц-число\n 2023-01-31 08:00 18:00')
    user_input = bot.register_next_step_handler(message, process_date_input)
    
def process_date_input(message):
    worker_name = message.from_user.first_name
    user_input_date = message.text
    user_input = user_input_date.split()
    conn = sqlite3.connect('work_hours.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT date, start_time, end_time
    FROM workers
    WHERE worker_name = ? AND date = ?
    ''', (worker_name, user_input[0]))
    need_change = cursor.fetchall()
    if need_change and len(user_input[1]) == len(user_input[2]) == 5 and user_input_date.replace(':', '').replace(' ', '').replace('-', '').isdigit():
        cursor.execute('''
        UPDATE workers
        SET start_time = ?, end_time = ?
        WHERE worker_name = ? AND date = ?
        ''', (user_input[1]+':00', user_input[2]+':00', worker_name, user_input[0]))
        
        bot.send_message(message.chat.id, f'{user_input[0]} время изменено на:\n{user_input_date[-11:]}\nсохранено\nЧтобы вернуть панель кнопок, нажмите символ справа в строке "сообщение" с четырьмя кружочками')
    else:
        bot.send_message(message.chat.id, f'нет информации о дате {user_input} в таблице или неверный формат. Нажмите кнопку "изменить время" ещё раз и введите корректный формат.\nЧтобы вернуть панель кнопок, нажмите символ справа в строке "сообщение" с четырьмя кружочками')
    conn.commit()
    conn.close()


# Обработчик неизвестных команд и сообщений
@bot.message_handler(func=lambda message: True)
def unknown_handler(message):
    bot.send_message(message.chat.id, "Извините, я не понимаю вашу команду. Попробуйте еще раз.")

# Запускаем бота
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as _ex:
        print(_ex)
        sleep(15)
