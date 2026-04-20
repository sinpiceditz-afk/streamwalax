import telebot
import requests
import os
from flask import Flask
from threading import Thread

# Environment variable se Bot Token lena
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Flask app banayenge taaki Render crash na ho (Render needs a web server)
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
        
        # Unique file name banana (taaki multiple users me clash na ho)
        file_name = f"temp_{message.message_id}.jpg"
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Telegraph API par upload karna
        with open(file_name, 'rb') as f:
            response = requests.post("https://telegra.ph/upload", files={'file': ('file', f, 'image/jpeg')})
            
        if response.status_code == 200:
            # Link generate karna
            json_response = response.json()
            if isinstance(json_response, list) and 'src' in json_response[0]:
                link = "https://telegra.ph" + json_response[0]['src']
                bot.edit_message_text(f"✅ **Image Uploaded!**\n\n🔗 Link: {link}", message.chat.id, msg.message_id)
            else:
                bot.edit_message_text("❌ Upload failed. Please try again.", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Server error. Try again later.", message.chat.id, msg.message_id)
            
        # Local file delete karna
        os.remove(file_name)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

if __name__ == "__main__":
    # Flask server ko background me start karna
    t = Thread(target=run_server)
    t.start()
    
    # Bot ko start karna
    print("Bot is running...")
    bot.infinity_polling()
