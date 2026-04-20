import telebot
import requests
import os
from flask import Flask
from threading import Thread

# Environment variable se Bot Token lena
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Flask app for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Successfully!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# /start command handle karna
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "👋 Hello! Mujhe koi bhi Image (Photo) bhejo aur main use direct Link me convert kar dunga.")

# Image handle karna
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        msg = bot.reply_to(message, "⏳ Processing image...")
        
        # Image download karna
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Unique file name banana
        file_name = f"temp_{message.message_id}.jpg"
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Catbox.moe API par upload karna (Works 100% on Render)
        with open(file_name, 'rb') as f:
            url = "https://catbox.moe/user/api.php"
            data = {"reqtype": "fileupload"}
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files)
            
        if response.status_code == 200:
            # Catbox direct link return karta hai plain text me
            link = response.text
            bot.edit_message_text(f"✅ **Image Uploaded!**\n\n🔗 Link: {link}", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ Upload failed. Server returned code: {response.status_code}", message.chat.id, msg.message_id)
            
        # Local file delete karna taaki storage full na ho
        if os.path.exists(file_name):
            os.remove(file_name)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)

if __name__ == "__main__":
    # Flask server ko background me start karna
    t = Thread(target=run_server)
    t.start()
    
    # Bot ko start karna
    print("Bot is running...")
    bot.infinity_polling()
