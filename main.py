import telebot
import sqlite3
from telebot import types, util


from add_work import add_work_handler, confirm_artwork_callback, cancel_artwork_callback, get_user_info
import watch
from watch import my_artworks_callback, send_artwork_preview


bot = telebot.TeleBot('Your_bot_token')



@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def confirm_callback_handler(call):
    confirm_artwork_callback(call, bot)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def cancel_callback_handler(call):
    cancel_artwork_callback(call, bot)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('prev_', 'next_', 'edit_', 'delete_')))
def callback_my_artworks(call):
    user_id = call.from_user.id
    watch.my_artworks_callback(call)
    # watch.send_my_artworks(user_id)


@bot.message_handler(commands=['start'])
def main(message):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()

    cur.execute('CREATE TABLE IF NOT EXISTS artists (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name varchar(100), number varchar(100), balance REAL)')
    conn.commit()

    if not is_registered(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn = types.KeyboardButton('Реєстрація')
        markup.add(btn)
        bot.send_message(message.chat.id, f'Привіт, {message.from_user.first_name}, ти ще не зареєстрований як митець.', reply_markup=markup)
        bot.register_next_step_handler(message, reg)
    else:
        user_info = get_user_info(message.from_user.id)
        bot.send_message(message.chat.id, f'Вітаю, {user_info["name"]}!')
        main_menu(message.from_user.id)


def is_registered(user_id):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM artists WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None


def get_user_info(user_id):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM artists WHERE user_id = ?', (user_id,))
    user_info = cur.fetchone()
    cur.close()
    conn.close()

    if user_info is not None:
        return {"name": user_info[2], "number": user_info[3], "balance": user_info[4]}
    else:
        return None


def reg(message):
    if message.text == 'Реєстрація':
        bot.send_message(message.chat.id, 'Розпочнемо. Напиши своє ім\'я або псевдонім')
        bot.register_next_step_handler(message, get_name)


def get_name(message):
    name = message.text
    bot.send_message(message.chat.id, 'Тепер натискайте кнопку, щоб відправити свій номер телефону', reply_markup=get_phone_button())
    bot.register_next_step_handler(message, get_phone, name)


def get_phone(message, name):
    if message.contact is not None:
        phone_number = message.contact.phone_number
        save_user(message.from_user.id, name, phone_number, 0.0)
        bot.send_message(message.chat.id, f'Дякую, {name}! Ти зареєстрований з номером телефону {phone_number}')
        main_menu(message.from_user.id)
    else:
        bot.send_message(message.chat.id, 'Будь ласка, використовуй кнопку для відправки номера телефону.')


def get_phone_button():
    button = types.KeyboardButton('Відправити номер телефону', request_contact=True)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(button)
    return markup


def save_user(user_id, name, phone_number, balance):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO artists (user_id, name, number, balance) VALUES (?, ?, ?, ?)', (user_id, name, phone_number, balance))
    conn.commit()
    cur.close()
    conn.close()


def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Добавити роботу')
    btn2 = types.KeyboardButton('Мої роботи')
    btn3 = types.KeyboardButton('Баланс')
    btn4 = types.KeyboardButton('Підтримка')

    markup.add(btn1, btn2)
    markup.add(btn3, btn4)

    bot.send_message(user_id, 'Що бажаєш зробити? Натискай кнопки:', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Підтримка')
def support(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Назад')
    btn2 = types.KeyboardButton('Змінити ім\'я')

    markup.add(btn1, btn2)

    bot.send_message(message.chat.id, 'Маєш питання/пропозиції/бажання - переходь в бот підтримки: BotName', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Назад')
def back_to_main_menu(message):
    main_menu(message.chat.id)

@bot.message_handler(func=lambda message: message.text == 'Відмінити')
def back_to_main_menu(message):
    main_menu(message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Змінити ім\'я')
def change_name(message):
    bot.send_message(message.chat.id, 'Введи нове ім\'я:')
    bot.register_next_step_handler(message, update_name)


def update_name(message):
    if message.text != 'Назад' and message.text != 'Змінити ім\'я':
        new_name = message.text
        user_info = get_user_info(message.from_user.id)
        save_user(message.from_user.id, new_name, user_info["number"], user_info["balance"])
        bot.send_message(message.chat.id, f'Ім\'я оновлено на {new_name}')
        main_menu(message.from_user.id)
    if str(message.text) == 'Змінити ім\'я':
        bot.send_message(message.chat.id, 'Просто відправте мені нове і\'я')
        bot.register_next_step_handler(message, update_name)
    else:
        main_menu(message.from_user.id)


@bot.message_handler(func=lambda message: message.text == 'Баланс')
def check_balance(message):
    user_info = get_user_info(message.from_user.id)
    if user_info["balance"] == 0.0:
        bot.send_message(message.chat.id, 'Твій баланс пустий, немає що виводити.')
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton('Назад')
        btn2 = types.KeyboardButton('Вивести')
        markup.add(btn1, btn2)
        bot.send_message(message.chat.id, f'Твій баланс (з урахуванням комісії): {user_info["balance"]}', reply_markup=markup)
        bot.register_next_step_handler(message, withdraw)


def withdraw(message):
    if message.text == 'Назад':
        main_menu(message.chat.id)
    elif message.text == 'Вивести':
        bot.send_message(message.chat.id, 'Введи свій номер карти:')
        bot.register_next_step_handler(message, process_withdraw)


def process_withdraw(message):
    card_number = message.text
    user_info = get_user_info(message.from_user.id)

    # Операція виведення коштів
    bot.send_message(message.chat.id, f'Сума виведена на карту {card_number}')
    save_user(message.from_user.id, user_info["name"], user_info["number"], 0.0)  # Обнулення балансу
    main_menu(message.from_user.id)


@bot.message_handler(func=lambda message: message.text == 'Мої роботи')
def my_artworks(message):
    try:
        send_artwork_preview.last_message_id = None
    except:
        print("не вийшло(")
    watch.send_my_artworks(message.from_user.id)
    bot.callback_query_handlers.append(my_artworks_callback)


@bot.message_handler(func=lambda message: message.text == 'Добавити роботу')
def add_work(message):
    add_work_handler(message, bot)
    # Реєстрація обробників для підтвердження або скасування дії
    bot.message_handlers.append(confirm_artwork_callback)
    bot.message_handlers.append(cancel_artwork_callback)


@bot.message_handler(commands=['money'])
def add_money(message):
    command_parts = message.text.split()

    if len(command_parts) == 2 and command_parts[1].isdigit():
        amount = int(command_parts[1])
        change_balance(message.from_user.id, amount)
        bot.send_message(message.chat.id, f'Баланс збільшено на {amount}.')
        main_menu(message.from_user.id)
    else:
        bot.send_message(message.chat.id, 'Невірний формат команди. Використовуйте /money <сума>.')


def change_balance(user_id, amount):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('UPDATE artists SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    cur.close()
    conn.close()


@bot.message_handler(func=lambda message: message.text == 'Теленик')
def some_text_egg(message):
    bot.reply_to(message, 'Сергій Федорович?')
    bot.send_message(message.chat.id, 'Чудовий викладач!')


@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    bot.send_message(message.chat.id, 'Вибачте, давайте почнем з початку')
    main(message)


if __name__ == "__main__":
    bot.polling(none_stop=True)
