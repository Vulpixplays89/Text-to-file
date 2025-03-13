import telebot
import os
import zipfile
import rarfile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from flask import Flask
from threading import Thread
# Stores text messages for each user
user_messages = {}

# Stores the selected file type (.txt, .py, etc.) for each user
user_file_type = {}

# Stores uploaded files for each user
user_files = {}

# Stores the compression type (zip/rar) for each user
user_compression_type = {}

# Tracks whether the bot is waiting for a filename from the user
waiting_for_filename = {}


# MongoDB Connection
MONGO_URL = "mongodb+srv://textbot:textbot@cluster0.afoyw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_collection = db["users"]

ADMIN_ID = 6897739611  # Replace with your Telegram ID

TOKEN = "8166833803:AAFLY0AIcnAkXnuihSDAbgpNJ-vsXVgwUdM"
bot = telebot.TeleBot(TOKEN)

app = Flask(' ')

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
        InlineKeyboardButton("📢 Channel", url="https://t.me/join_hyponet"),  # Replace with your channel
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/botplays90")  # Replace with your contact
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

        
@bot.message_handler(commands=['done'])
def send_done(message):
    user_id = message.chat.id

    # ✅ Case 1: If the user has sent text messages, ask for a filename
    if user_id in user_messages and user_messages[user_id]:  
        waiting_for_filename[user_id] = "text_file"  # Mark that we are waiting for text file name
        bot.send_message(user_id, "📂 Enter a name for your file (without extension):")
        return  

    # ✅ Case 2: If the user has uploaded files, ask for a filename for compression
    if user_id in user_files and user_files[user_id]:  
        waiting_for_filename[user_id] = "compressed_file"  # Mark that we are waiting for a compressed file name
        bot.send_message(user_id, "📂 Enter a name for the compressed file (without extension):")
        return  

    # ❌ If neither text nor files exist
    bot.send_message(user_id, "❌ You haven't sent any text or uploaded files!")

@bot.message_handler(func=lambda message: message.chat.id in waiting_for_filename)
def process_filename(message):
    user_id = message.chat.id
    file_name = "".join(c for c in message.text if c.isalnum() or c in ("_", "-")).strip()

    if not file_name:
        file_name = f"default_{user_id}"  # Fallback name

    if waiting_for_filename[user_id] == "text_file":
        file_type = user_file_type.get(user_id, "txt")  # Default to .txt
        full_filename = f"{file_name}.{file_type}"

        with open(full_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(user_messages[user_id]))  

        with open(full_filename, "rb") as f:
            bot.send_document(user_id, f)

        # 🔥 Delete the file after sending
        try:
            os.remove(full_filename)
        except Exception as e:
            print(f"❌ Error deleting file {full_filename}: {e}")

        user_messages[user_id] = []  # Clear stored text

    elif waiting_for_filename[user_id] == "compressed_file":
        archive_format = user_compression_type.get(user_id, "zip")
        full_filename = f"user_files/{file_name}.{archive_format}"
        user_folder = f"user_files/{user_id}"

        if archive_format == "zip":
            with zipfile.ZipFile(full_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in user_files[user_id]:
                    zipf.write(file_path, os.path.basename(file_path))
        elif archive_format == "rar":
            with rarfile.RarFile(full_filename, 'w') as rarf:
                for file_path in user_files[user_id]:
                    rarf.write(file_path, os.path.basename(file_path))

        with open(full_filename, "rb") as file:
            bot.send_document(user_id, file)

        # 🔥 Delete user-uploaded files and archive after sending
        for file_path in user_files[user_id]:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"❌ Error deleting file {file_path}: {e}")

        try:
            os.remove(full_filename)
        except Exception as e:
            print(f"❌ Error deleting archive {full_filename}: {e}")

        # 🔥 Delete user folder if empty
        if os.path.exists(user_folder) and not os.listdir(user_folder):  
            os.rmdir(user_folder)  

        user_files.pop(user_id, None)
        user_compression_type.pop(user_id, None)

    # 🔹 Reset the waiting status
    waiting_for_filename.pop(user_id, None)

    bot.send_message(user_id, "✅ File successfully created and sent!")








        
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

import os
import zipfile
import rarfile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Dictionaries to track user uploads and compression preferences
user_files = {}
user_compression_type = {}
waiting_for_filename = {}
@bot.message_handler(commands=['convert'])
def convert_files(message):
    user_id = message.chat.id
    
    if user_id not in user_files:
        user_files[user_id] = []  # Initialize only if not existing
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🗜 ZIP", callback_data=f"set_zip_{user_id}"),
        InlineKeyboardButton("📦 RAR", callback_data=f"set_rar_{user_id}")
    )

    bot.send_message(user_id, "Choose the compression format:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_zip") or call.data.startswith("set_rar"))
def set_compression_format(call):
    user_id = call.message.chat.id  # Fix: Get directly from message context
    user_compression_type[user_id] = "zip" if "set_zip" in call.data else "rar"

    bot.send_message(user_id, "✅ Format selected! Now send the files you want to compress. When done, type /done.")

@bot.message_handler(content_types=['document'])
def receive_files(message):
    user_id = message.chat.id

    if user_id not in user_files:
        bot.send_message(user_id, "❌ Please use /convert first.")
        return

    file_id = message.document.file_id
    file_name = message.document.file_name
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    user_folder = f"user_files/{user_id}"
    os.makedirs(user_folder, exist_ok=True)  # Ensure the folder exists
    file_path = os.path.join(user_folder, file_name)

    with open(file_path, "wb") as f:
        f.write(downloaded_file)

    if user_id not in user_files:
        user_files[user_id] = []  # Ensure list exists

    user_files[user_id].append(file_path)  # Store the file path
    bot.send_message(user_id, f"📄 File `{file_name}` received! Send more or type /done.", parse_mode="Markdown")

    # Debugging print
    print(f"User {user_id} uploaded {file_name}. Files stored: {user_files[user_id]}")


@bot.message_handler(commands=['done'])
def ask_file_name(message):
    user_id = message.chat.id

    # Check if user has sent any files
    if user_id not in user_files or not user_files[user_id]:  
        bot.send_message(user_id, "❌ You haven't sent any files! Please send some files first.")
        return

    waiting_for_filename[user_id] = True
    bot.send_message(user_id, "📂 Enter a name for the compressed file (without extension):")
@bot.message_handler(func=lambda message: message.chat.id in waiting_for_filename)
def create_archive(message):
    user_id = message.chat.id
    file_name = "".join(c for c in message.text if c.isalnum() or c in ("_", "-")).strip()

    if not file_name:
        file_name = f"archive_{user_id}"

    archive_format = user_compression_type.get(user_id, "zip")
    archive_path = f"user_files/{file_name}.{archive_format}"
    user_folder = f"user_files/{user_id}"

    if user_id not in user_files or not user_files[user_id]:
        bot.send_message(user_id, "❌ No files to compress. Please send files first.")
        return  

    # Create ZIP or RAR archive
    if archive_format == "zip":
        with zipfile.ZipFile(archive_path, 'w') as zipf:
            for file_path in user_files[user_id]:
                zipf.write(file_path, os.path.basename(file_path))
    elif archive_format == "rar":
        with rarfile.RarFile(archive_path, 'w') as rarf:
            for file_path in user_files[user_id]:
                rarf.write(file_path, os.path.basename(file_path))

    # Send the archive
    with open(archive_path, "rb") as file:
        bot.send_document(user_id, file)

    # 🔥 Delete user-uploaded files immediately after sending
    for file_path in user_files[user_id]:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"❌ Error deleting file {file_path}: {e}")

    # 🔥 Delete the archive after sending
    try:
        os.remove(archive_path)
    except Exception as e:
        print(f"❌ Error deleting archive {archive_path}: {e}")

    # 🔥 Delete user folder if empty
    if os.path.exists(user_folder) and not os.listdir(user_folder):  
        os.rmdir(user_folder)  

    # 🔹 Reset user data
    waiting_for_filename.pop(user_id, None)
    user_files.pop(user_id, None)
    user_compression_type.pop(user_id, None)

    bot.send_message(user_id, "✅ Compression complete! File sent and deleted successfully.")





    
keep_alive()

bot.infinity_polling()
