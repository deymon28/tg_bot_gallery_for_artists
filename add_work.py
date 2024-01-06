import sqlite3
import os
import telebot
from telebot import types


bot = telebot.TeleBot('Your_bot_token')


artwork_id = 0


def test_min(message):
    if message.text == 'Відмінити':
        print("Натиснули відмінити")
        return True

def create_artworks_table_if_not_exists():
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS artworks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_url TEXT,
            title TEXT,
            description TEXT,
            type TEXT,
            price REAL,
            author_id INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()



def add_work_handler(message, bot):
    new_artwork = {"user_id": message.from_user.id, "status": "На перевірці"}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    create_artworks_table_if_not_exists()

    cancel_btn = types.KeyboardButton('Відмінити')
    markup.add(cancel_btn)
    bot.send_message(message.chat.id, 'Надішліть фото роботи:', reply_markup=markup)

    bot.register_next_step_handler(message, process_photo, new_artwork, bot)


def send_preview(new_artwork, bot, message, artwork_id):
    # Отримання інформації про автора
    author_info = get_user_info(new_artwork["user_id"])
    print('send_preview', author_info)

    # Формування тексту для попереднього перегляду
    preview_text = (
        f'<b>Попередній перегляд роботи:</b>\n\n'
        f'<b>Назва:</b> {new_artwork["title"]}\n'
        f'<b>Опис:</b> {new_artwork["description"]}\n'
        f'<b>Тип:</b> {new_artwork["type"]}\n'
        f'<b>Ціна:</b> {new_artwork["price"]} грн\n'
        f'<b>Автор:</b> {author_info["name"]}\n\n'
        f'<i>Виберіть дію:</i>'
    )

    # Створення Inline-клавіатури для попереднього перегляду
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Все вірно', callback_data=f'confirm_{new_artwork["user_id"]}')
    btn2 = types.InlineKeyboardButton('Відмінити', callback_data=f'cancel_{new_artwork["user_id"]}')
    markup.add(btn1, btn2)

    # Запис роботи в базу даних
    # save_artwork_to_database(new_artwork)

    # Відправлення попереднього перегляду користувачу
    bot.send_photo(message.chat.id, open(new_artwork["photo_url"], 'rb'), caption=preview_text, parse_mode='HTML', reply_markup=markup)


def process_photo(message, new_artwork, bot):
    if test_min(message):
        return


    if message.photo is None or len(message.photo) == 0:
        bot.send_message(message.chat.id, 'Будь ласка, відправте фото роботи.')
        return

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path

    photo_path = download_photo(file_path)

    new_artwork["photo_url"] = photo_path

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_btn = types.KeyboardButton('Відмінити')
    markup.add(cancel_btn)

    bot.send_message(message.chat.id, 'Напишіть назву роботи:', reply_markup=markup)
    bot.register_next_step_handler(message, process_title, new_artwork, bot)


def download_photo(file_path):
    # Автоматичне створення папки якщо її немає 'imgs/photos/'
    os.makedirs('imgs/photos/', exist_ok=True)

    downloaded_file = bot.download_file(file_path)

    # Генерація унікального імені для файлу
    _, ext = os.path.splitext(file_path)
    filename = f'{os.urandom(16).hex()}{ext}'

    unique_filename = os.path.join('imgs/photos', filename)

    with open(unique_filename, 'wb') as new_file:
        new_file.write(downloaded_file)

    return unique_filename


def process_title(message, new_artwork, bot):
    new_artwork["title"] = message.text

    bot.send_message(message.chat.id, 'Введіть опис роботи:')
    bot.register_next_step_handler(message, process_description, new_artwork, bot)


def process_description(message, new_artwork, bot):
    new_artwork["description"] = message.text

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('картина')
    btn2 = types.KeyboardButton('скульптура')
    btn3 = types.KeyboardButton('фото')
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, 'Вкажіть тип роботи:', reply_markup=markup)
    bot.register_next_step_handler(message, process_type, new_artwork, bot)


def process_type(message, new_artwork, bot):
    print(message.text, type(message.text))
    if message.text != 'картина' and message.text != 'скульптура' and message.text != 'фото':
        bot.send_message(message.chat.id, 'Не коректний тип, спробуйте ще раз:')
        process_description(message, new_artwork, bot)
        return
    else:
        new_artwork["type"] = message.text

    # bot.delete_message(message.chat.id, message.message_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_btn = types.KeyboardButton('Відмінити')
    markup.add(cancel_btn)
    bot.send_message(message.chat.id, 'Введіть ціну роботи (з урахуванням комісії):', reply_markup=markup)

    bot.register_next_step_handler(message, process_price, new_artwork, bot)


def process_price(message, new_artwork, bot):
    # Перевірка, чи введена коректна ціна
    if not message.text.replace('.', '').isdigit():
        bot.send_message(message.chat.id, 'Некоректно введена ціна. Спробуйте ще раз.')
        process_type(message, new_artwork, bot)
        return

    new_artwork["price"] = float(message.text)

    fill_and_save_artwork(new_artwork, bot, message)


def fill_and_save_artwork(new_artwork, bot, message):
    # Заповнення інших полів
    new_artwork["author_id"] = new_artwork["user_id"]

    global artwork_id
    artwork_id = save_artwork_to_database(new_artwork)
    print('fill_and_save_artwork ', artwork_id)

    send_preview(new_artwork, bot, message, artwork_id)


def save_artwork_to_database(new_artwork):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO artworks (photo_url, title, description, type, price, author_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (new_artwork["photo_url"], new_artwork["title"], new_artwork["description"], new_artwork["type"], new_artwork["price"], new_artwork["author_id"], new_artwork["status"]))

    artwork_id = cur.lastrowid

    conn.commit()
    cur.close()
    conn.close()

    print('id: ', artwork_id)
    return artwork_id


def confirm_artwork_callback(callback_query, bot):
    user_id = callback_query.data.split('_')[-1]

    artwork_info = get_artwork_info(user_id)
    print('confirm_artwork_callback: ', artwork_info)

    if artwork_info:
        update_artwork_status(artwork_info[0], 'На перевірці')

        bot.send_message(callback_query.message.chat.id, 'Artwork has been saved!')
    else:
        bot.send_message(callback_query.message.chat.id, 'Artwork information not found. Cannot confirm.')



def cancel_artwork_callback(callback_query, bot):
    user_id = callback_query.data.split('_')[-1]
    global artwork_id
    print('global ', artwork_id)
    artwork_info = get_artwork_info(user_id)
    # print('cancel_artwork_callback: ', artwork_info)

    if artwork_info:
        delete_artwork(artwork_id, user_id)

        bot.send_message(callback_query.message.chat.id, 'Artwork addition has been canceled.')
    else:
        bot.send_message(callback_query.message.chat.id, 'Artwork information not found. Cannot cancel.')



def get_artwork_info(user_id):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM artworks WHERE author_id = ? AND status = ?', (user_id, 'На перевірці'))
    #cur.execute('SELECT * FROM artworks WHERE author_id = ? AND id = ?', (user_id, ))
    artwork_info = cur.fetchone()
    cur.close()
    conn.close()

    return artwork_info



def update_artwork_status(author_id, status):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('UPDATE artworks SET status = ? WHERE author_id = ?', (status, author_id))
    conn.commit()
    cur.close()
    conn.close()
    print("видалення з бд")


def delete_artwork(artwork_id, user_id):
    print('delete_artwork, artwork_id: ',artwork_id)
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('DELETE FROM artworks WHERE id = ? AND author_id = ?', (artwork_id, user_id))
    # cur.execute('DELETE FROM artworks WHERE author_id = ?', (artwork_id,))
    conn.commit()
    cur.close()
    conn.close()


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


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(callback_query):
    if callback_query.data.startswith('confirm_'):
        confirm_artwork_callback(callback_query, bot)
    elif callback_query.data.startswith('cancel_'):
        cancel_artwork_callback(callback_query, bot)


@bot.message_handler(commands=['add_work'])
def add_work(message):
    add_work_handler(message, bot)

