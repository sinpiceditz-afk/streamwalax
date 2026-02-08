import os
import asyncio
import logging
import time
import boto3
import urllib.parse
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Cloudflare R2
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_PUBLIC_DOMAIN = os.environ.get("R2_PUBLIC_DOMAIN", "") 

# Website URL
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://apki-website.netlify.app")

PORT = int(os.environ.get("PORT", 8080))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT SETUP ---
app = Client("R2Uploader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- R2 CLIENT ---
s3_client = boto3.client(
    's3',
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# --- WEB SERVER ---
routes = web.RouteTableDef()
@routes.get("/")
async def status(request): return web.Response(text="Bot Running 24/7")

# --- SAFE EDIT FUNCTION (Ye Error Roke Ga) ---
async def safe_edit(message, text, markup=None):
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except errors.MessageNotModified:
        pass # Agar same message hai to ignore karo
    except Exception as e:
        logger.error(f"Edit Error: {e}")

# --- UPLOAD FUNCTION ---
async def upload_to_r2(file_path, object_name, mime_type):
    try:
        s3_client.upload_file(
            file_path, 
            R2_BUCKET_NAME, 
            object_name,
            ExtraArgs={'ContentType': mime_type, 'ACL': 'public-read'}
        )
        return True
    except Exception as e:
        logger.error(f"R2 Upload Error: {e}")
        return False

# --- COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Video bhejo, main Cloudflare R2 par upload kar dunga.")

@app.on_message(filters.private & (filters.video | filters.document))
async def handle_video(client, message):
    msg = await message.reply_text("📥 **Processing...**")
    
    try:
        # 1. File Details
        media = message.video or message.document
        file_name = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
        mime_type = getattr(media, "mime_type", "video/mp4") or "video/mp4"
        
        await safe_edit(msg, "📥 **Downloading to Server...**")
        
        # 2. Download
        download_path = await app.download_media(message)
        
        await safe_edit(msg, "☁️ **Uploading to Cloudflare R2...**")
        
        # 3. Upload
        unique_name = f"{int(time.time())}_{file_name}"
        success = await upload_to_r2(download_path, unique_name, mime_type)
        
        # 4. Cleanup
        if os.path.exists(download_path): os.remove(download_path)

        if success:
            # Links Banana
            raw_link = f"{R2_PUBLIC_DOMAIN}/{unique_name}"
            safe_name = urllib.parse.quote(file_name)
            final_link = f"{WEB_APP_URL}/?src={raw_link}&name={safe_name}"
            
            await safe_edit(msg, 
                f"✅ **Upload Complete!**\n\n📂 `{file_name}`\n👇 Click below to watch:",
                markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Watch Video", url=final_link)]])
            )
        else:
            await safe_edit(msg, "❌ Upload Failed. Check R2 Keys.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await safe_edit(msg, f"❌ Error: {str(e)}")

# --- RUNNER ---
async def start_services():
    app_runner = web.AppRunner(web.Application())
    app_runner.app.add_routes(routes)
    await app_runner.setup()
    site = web.TCPSite(app_runner, "0.0.0.0", PORT)
    await site.start()
    await app.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
