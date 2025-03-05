import telebot
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from threading import Thread 
from flask import Flask 

# MongoDB Connection
MONGO_URL = "mongodb+srv://textbot:textbot@cluster0.afoyw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_collection = db["users"]

ADMIN_ID = 6897739611  # Replace with your Telegram ID

TOKEN = "8166833803:AAHcpRDyfyt5yE__AHAeu6oHul1hpmxduZ8"
bot = telebot.TeleBot(TOKEN)

@app.route('/')
def home():
    return "I am alive"

def run_http_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http_server)
    t.start()

# Dictionary to store user messages and file type
user_messages = {}
user_file_type = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    # Save user to MongoDB if not already registered
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

    # Send the welcome message with inline buttons
    markup = main_menu()
    bot.send_message(user_id, "Welcome! Choose an option below:", reply_markup=markup)


def main_menu():
    """Creates the main menu inline keyboard."""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📂 Choose a File Type", callback_data="choose_option"),
        InlineKeyboardButton("📢 Channel", url="https://t.me/yourchannel"),  # Replace with your channel
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/yourusername")  # Replace with your contact
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "choose_option")
def choose_option(call):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📄 Text (.txt)", callback_data="set_txt"),
        InlineKeyboardButton("🐍 Python (.py)", callback_data="set_py"),
        InlineKeyboardButton("🌐 HTML (.html)", callback_data="set_html"), 
        InlineKeyboardButton("🎨 CSS (.css)", callback_data="set_css"),
        InlineKeyboardButton("📝 JSON (.json)", callback_data="set_json"),
        InlineKeyboardButton("📜 JavaScript (.js)", callback_data="set_js"),
        InlineKeyboardButton("📝 XML (.xml)", callback_data="set_xml"),
        InlineKeyboardButton("📊 CSV (.csv)", callback_data="set_csv"),
        InlineKeyboardButton("⚙️ YAML (.yaml)", callback_data="set_yaml"),
        InlineKeyboardButton("🐘 PHP (.php)", callback_data="set_php"),
        InlineKeyboardButton("💻 Bash (.sh)", callback_data="set_sh"),
        InlineKeyboardButton("📜 Markdown (.md)", callback_data="set_md"),
        InlineKeyboardButton("🔙 Back", callback_data="back_to_main")  # Back button
    )

    bot.edit_message_text(
        "Select the file format you want:",
        call.message.chat.id, call.message.message_id, reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    bot.edit_message_text(
        "Welcome back! Choose an option below:",
        call.message.chat.id, call.message.message_id, reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def set_file_type(call):
    user_id = call.message.chat.id
    file_type = call.data.split("_")[1]  
    user_file_type[user_id] = file_type

    bot.edit_message_text(
        f"✅ File type set to **.{file_type}**. Send me messages, then type /done to receive your file.",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back", callback_data="choose_option"))
    )

@bot.message_handler(func=lambda message: message.text and not message.text.startswith("/") and message.chat.id not in waiting_for_filename)
def store_text(message):
    user_id = message.chat.id
    text = message.text.strip()

    if user_id not in user_messages:
        user_messages[user_id] = []

    if text:
        user_messages[user_id].append(text)
        bot.send_message(user_id, "✅ Message saved! Send more or type /done to get your file.")

        

# Dictionary to track user state for file naming
waiting_for_filename = {}

@bot.message_handler(commands=['done'])
def ask_file_name(message):
    user_id = message.chat.id

    if user_id in user_messages and user_messages[user_id]:
        waiting_for_filename[user_id] = True  # Set the state before asking for filename
        bot.send_message(user_id, "📂 Please enter a file name (without extension):")
    else:
        bot.send_message(user_id, "❌ You haven't sent any messages yet. Send some text first!")


@bot.message_handler(func=lambda message: message.chat.id in waiting_for_filename)
def save_file_with_name(message):
    user_id = message.chat.id
    file_extension = user_file_type.get(user_id, "txt")
    
    # Clean the file name (remove special characters)
    file_name = "".join(c for c in message.text if c.isalnum() or c in ("_", "-")).strip()
    
    # If empty, set a default name
    if not file_name:
        file_name = f"file_{user_id}"

    file_name = f"{file_name}.{file_extension}"

    # Write the file
    with open(file_name, "w", encoding="utf-8") as file:
        file.write("\n".join(user_messages[user_id]))

    with open(file_name, "rb") as file:
        bot.send_document(user_id, file)

    os.remove(file_name)  # Delete after sending
    user_messages[user_id] = []  # Clear messages
    waiting_for_filename.pop(user_id, None)  # Remove from waiting state
    bot.send_message(user_id, "✅ File sent! You can start a new session now.")



@bot.message_handler(func=lambda message: message.text and not message.text.startswith("/") and message.chat.id not in waiting_for_filename)
def store_text(message):
    user_id = message.chat.id
    text = message.text.strip()

    if user_id not in user_messages:
        user_messages[user_id] = []

    if text:
        user_messages[user_id].append(text)
        bot.send_message(user_id, "✅ Message saved! Send more or type /done to get your file.")



        
# Command to get the total number of users
@bot.message_handler(commands=['users'])
def users_count(message):
    if message.chat.id == ADMIN_ID:
        count = users_collection.count_documents({})
        bot.send_message(ADMIN_ID, f"👥 Total Users: {count}")
    else:
        bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")

# Command to send a broadcast message
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ You are not authorized to use this command.")
        return
    
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        bot.send_message(ADMIN_ID, "❌ Please provide a message. Example: `/broadcast Hello users!`")
        return

    broadcast_message = command_parts[1]
    users = users_collection.find({}, {"user_id": 1})

    sent, failed = 0, 0
    for user in users:
        try:
            bot.send_message(user["user_id"], f"📢 Broadcast:\n\n{broadcast_message}")
            sent += 1
        except:
            failed += 1

    bot.send_message(ADMIN_ID, f"✅ Broadcast sent!\n📤 Sent: {sent}\n❌ Failed: {failed}")
    
keep_alive()

bot.infinity_polling()
