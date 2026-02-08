import os
import asyncio
import logging
import time
import boto3
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- CONFIGURATION (Render Environment Variables se lega) ---
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Cloudflare R2 Credentials
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
R2_PUBLIC_DOMAIN = os.environ.get("R2_PUBLIC_DOMAIN", "") 
# Example Domain: https://pub-xxxx.r2.dev (R2 settings me 'Public Access' on karein)

PORT = int(os.environ.get("PORT", 8080))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT SETUP ---
app = Client("R2Uploader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- R2 CLIENT SETUP ---
s3_client = boto3.client(
    's3',
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# --- WEB SERVER (Render ko Jaga rakhne ke liye) ---
routes = web.RouteTableDef()

@routes.get("/")
async def status(request):
    return web.Response(text="R2 Uploader Bot is Running 24/7!")

# --- UPLOAD LOGIC ---
async def upload_to_r2(file_path, object_name, mime_type):
    try:
        # File upload kar raha hai...
        s3_client.upload_file(
            file_path, 
            R2_BUCKET_NAME, 
            object_name,
            ExtraArgs={'ContentType': mime_type, 'ACL': 'public-read'} # Browser me play hone ke liye
        )
        return True
    except Exception as e:
        logger.error(f"R2 Upload Error: {e}")
        return False

# --- BOT COMMANDS ---
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 **Hello!**\nSend me a video, I will upload it to Cloudflare R2 for Fast Streaming.")

@app.on_message(filters.private & (filters.video | filters.document))
async def handle_video(client, message):
    try:
        msg = await message.reply_text("📥 **Downloading to Server...** (Please Wait)")
        
        # 1. File Details
        media = message.video or message.document
        file_name = getattr(media, "file_name", f"video_{message.id}.mp4") or f"video_{message.id}.mp4"
        mime_type = getattr(media, "mime_type", "video/mp4") or "video/mp4"
        
        # 2. Download to Render (Temporary Storage)
        # Note: Render Free tier par disk space kam hoti hai, 500MB se badi file fail ho sakti hai
        download_path = await app.download_media(message)
        
        await msg.edit_text("☁️ **Uploading to Cloudflare R2...**")
        
        # 3. Upload to R2
        start_time = time.time()
        unique_name = f"{int(start_time)}_{file_name}" # Unique name taki overwrite na ho
        
        success = await upload_to_r2(download_path, unique_name, mime_type)
        
        # 4. Clean up (Render ki disk saaf karein)
        if os.path.exists(download_path):
            os.remove(download_path)

        if success:
            # 5. Generate Web App Link
            # Pehle R2 ka direct link banao
            raw_r2_link = f"{R2_PUBLIC_DOMAIN}/{unique_name}"
            
            # Phir usse Web App URL ke sath jodo
            # NOTE: Yaha apni Netlify/Blogger site ka link dalein
            MY_WEBSITE = "https://apki-website.netlify.app" 
            
            import urllib.parse
            safe_name = urllib.parse.quote(file_name)
            
            # Final Link jo Ads dikhayega aur Video chalayega
            web_app_link = f"{MY_WEBSITE}/?src={raw_r2_link}&name={safe_name}"
            
            await msg.edit_text(
                f"✅ **Video Ready to Watch!**\n\n"
                f"📂 **File:** `{file_name}`\n"
                f"👇 **Click to Watch & Download:**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Play Online (Fast)", url=web_app_link)]
                ])
            )
        else:
            await msg.edit_text("❌ Upload Failed. Check Logs.")

    except Exception as e:
        logger.error(e)
        await message.reply_text(f"❌ Error: {str(e)}")

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
