import base64
from decimal import Context
import os
from elevenlabs.client import ElevenLabs
from telegram import Update
from telegram.ext import ContextTypes

from aws_telegram_bot.application.conversation_service.generate_response import get_agent_response
from aws_telegram_bot.infrastructure.clients import elevenlabs
from aws_telegram_bot.infrastructure.clients.elevenlabs import get_elevenlabs_client
from aws_telegram_bot.infrastructure.clients.openai import get_openai_client

openai_client = get_openai_client()
elevenlabs_client = get_elevenlabs_client()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    response = get_agent_response({"messages": user_message}, user_id=update.message.from_user.id)

    await send_response(update, context, response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = "/tmp/voice.ogg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as audio_file:
        transcription = openai_client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
        )
    os.remove(file_path)

    response = get_agent_response({"messages": transcription.text}, user_id=update.message.from_user.id)

    await send_response(update, context, response)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = "/tmp/image.jpg"
    await file.download_to_drive(file_path)

    with open(file_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")

    os.remove(file_path)

    # Step 1: Get vision response
    vision_response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what you see in the picture"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
    )

    description = vision_response.choices[0].message.content.strip()

    # Step 2: Extract user caption if provided
    user_caption = update.message.caption or ""

    # Step 3: Compose full message for graph
    combined_message = f"{user_caption} [IMAGE_ANALYSIS] {description}".strip()

    # Step 4: Invoke graph
    response = get_agent_response({"messages": combined_message}, user_id=update.message.from_user.id)

    # Step 5: Add description as caption for the outgoing image response
    if "messages" in response and isinstance(response["messages"][-1], dict):
        response["messages"][-1]["caption"] = description

    await send_response(update, context, response)


async def send_response(update: Update, context: ContextTypes.DEFAULT_TYPE, response: dict):
    last_message = response["messages"][-1]
    content = last_message.content
    response_type = response["response_type"]

    if response_type == "text":
        await update.message.reply_text(content)

    elif response_type == "audio":
        audio_bytes = response.get("audio_buffer")
        if audio_bytes:
            await update.message.reply_voice(voice=audio_bytes)

    else:
        await update.message.reply_text("Sorry, I can't talk right now buddy! 😔")