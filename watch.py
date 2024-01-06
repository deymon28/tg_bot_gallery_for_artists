import sqlite3
import telebot
from telebot import types
from datetime import datetime
import re

from add_work import get_user_info


bot = telebot.TeleBot('Your_bot_token')


last_message_id = None

def my_artworks_callback(call):
    # print(call.data)
    user_id = call.from_user.id
    user_chat_id = call.message.chat.id

    match = re.match(r'delete_confirm_(\d+)', call.data) or re.match(r'delete_cancel_(\d+)', call.data)
    if match:
        action, suf, artwork_id = call.data.split('_')
        action = action + '_' + suf
    else:
        action, artwork_id = call.data.split('_')

    if action == 'delete_confirm':
        confirm_delete_artwork(user_chat_id, artwork_id, user_id, action)
        return
    elif action == 'delete_cancel':
        confirm_delete_artwork(user_chat_id, artwork_id, user_id, action)
        return


    artworks = get_user_artworks(user_id)

    if not artworks:
        bot.send_message(user_chat_id, 'Ви ще не додали робіт.')
        return

    current_index = next((i for i, artwork in enumerate(artworks) if artwork[0] == int(artwork_id)), None)

    if current_index is not None:
        if action == 'prev':
            prev_index = (current_index - 1) % len(artworks)
            send_artwork_preview(user_chat_id, artworks[prev_index])
        elif action == 'next':
            next_index = (current_index + 1) % len(artworks)
            send_artwork_preview(user_chat_id, artworks[next_index])
        elif action == 'edit':
            edit_artwork(user_chat_id, artworks[current_index])
        elif action == 'delete':
            delete_artwork(user_chat_id, artworks[current_index])



def send_my_artworks(user_id):
    artworks = get_user_artworks(user_id)
    # print(artworks)

    if not artworks:
        bot.send_message(user_id, 'Ви ще не додали жодної роботи.')
        return

    # Відправлення першої роботи
    send_artwork_preview(user_id, artworks[0])


def get_user_artworks(user_id):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM artworks WHERE author_id = ?', (user_id,))
    artworks = cur.fetchall()
    cur.close()
    conn.close()
    return artworks


def send_artwork_preview(chat_id, artwork):
    # Format artwork information
    artwork_info = (
        f'<b>ID:</b> {artwork[0]}\n'
        f'<b>Назва:</b> {artwork[2]}\n'
        f'<b>Опис:</b> {artwork[3]}\n'
        f'<b>Тип:</b> {artwork[4]}\n'
        f'<b>Ціна:</b> {artwork[5]} грн\n'
        f'<b>Автор:</b> {get_user_info(artwork[6])["name"]}\n'
        f'<b>Статус:</b> {artwork[7]}\n'
        f'\n<i>Оновлено: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>'
    )

    markup = types.InlineKeyboardMarkup()

    btn_prev = types.InlineKeyboardButton('<<', callback_data=f'prev_{artwork[0]}')
    btn_next = types.InlineKeyboardButton('>>', callback_data=f'next_{artwork[0]}')
    # btn_edit = types.InlineKeyboardButton('Редагувати', callback_data=f'edit_{artwork[0]}')
    btn_delete = types.InlineKeyboardButton('Видалити', callback_data=f'delete_{artwork[0]}')

    markup.row(btn_prev, btn_next)
    # markup.row(btn_edit, btn_delete)
    markup.row(btn_delete)

    if send_artwork_preview.last_message_id is not None:
        try:
            bot.edit_message_media(chat_id=chat_id, message_id=send_artwork_preview.last_message_id,
                                    media=types.InputMediaPhoto(media=types.InputFile(artwork[1]),
                                                               caption=artwork_info, parse_mode='HTML'),
                                    reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            if "message to edit not found" in str(e):
                message = bot.send_photo(chat_id, open(artwork[1], 'rb'), caption=artwork_info, parse_mode='HTML',
                                         reply_markup=markup)
                send_artwork_preview.last_message_id = message.message_id
            else:
                raise
    else:
        message = bot.send_photo(chat_id, open(artwork[1], 'rb'), caption=artwork_info, parse_mode='HTML',
                                 reply_markup=markup)
        send_artwork_preview.last_message_id = message.message_id


# delete

def delete_artwork(chat_id, artwork):
    confirmation_text = f'Ви дійсно бажаєте видалити роботу з ID {artwork[0]}?'

    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton('Так', callback_data=f'delete_confirm_{artwork[0]}')
    btn_no = types.InlineKeyboardButton('Ні', callback_data=f'delete_cancel_{artwork[0]}')
    markup.row(btn_yes, btn_no)

    message = bot.send_message(chat_id, confirmation_text, reply_markup=markup)
    global last_message_id
    last_message_id = message.message_id


def confirm_delete_artwork(chat_id, artwork_id, user_id, action):
    global last_message_id

    if action == 'delete_confirm':
        delete_artwork_from_database(artwork_id, user_id)


        bot.send_message(chat_id, f'Artwork with ID {artwork_id} has been deleted.')

        user_id = bot.get_chat(chat_id).id
        artworks = get_user_artworks(user_id)

        if artworks:
            send_artwork_preview(chat_id, artworks[0])
    elif action == 'delete_cancel':
        if last_message_id:
            bot.delete_message(chat_id, last_message_id)
        bot.send_message(chat_id, 'Видалення роботи відмінено')

def delete_artwork_from_database(artwork_id, user_id):
    conn = sqlite3.connect('artists.sql')
    cur = conn.cursor()
    cur.execute('DELETE FROM artworks WHERE id = ? AND author_id = ?', (artwork_id, user_id))
    conn.commit()
    cur.close()
    conn.close()


# edit
def edit_artwork(chat_id, artwork):
    bot.send_message(chat_id, 'Ця функція поки що не доступна')
