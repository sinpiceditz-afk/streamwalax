import telebot
import requests
import os
from flask import Flask
from threading import Thread

# Environment variables se Tokens lena
TOKEN = os.environ.get("BOT_TOKEN")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY") # Naya variable ImgBB ke liye

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
        msg = bot.reply_to(message, "⏳ Uploading to server, please wait...")
        
        # Image download karna
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Unique file name banana
        file_name = f"temp_{message.message_id}.jpg"
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # ImgBB API par upload karna (100% Works on Render)
        with open(file_name, 'rb') as f:
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": IMGBB_API_KEY
            }
            files = {
                "image": f
            }
            response = requests.post(url, data=payload, files=files)
            
        if response.status_code == 200:
            # ImgBB direct link nikalna
            json_data = response.json()
            link = json_data['data']['url']
            bot.edit_message_text(f"✅ **Image Successfully Uploaded!**\n\n🔗 Direct Link: {link}", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ Upload failed. Server Error: {response.status_code}\nEnsure your ImgBB API key is correct.", message.chat.id, msg.message_id)
            
        # Local file delete karna taaki storage full na ho
        if os.path.exists(file_name):
            os.remove(file_name)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)

if __name__ == "__main__":
    if not TOKEN or not IMGBB_API_KEY:
        print("ERROR: BOT_TOKEN or IMGBB_API_KEY is missing!")
    else:
        # Flask server ko background me start karna
        t = Thread(target=run_server)
        t.start()
        
        # Bot ko start karna
        print("Bot is running...")
        bot.infinity_polling()
