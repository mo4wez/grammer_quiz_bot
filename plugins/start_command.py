from pyrogram import Client, filters
from pyrogram.types import Message
from models import User

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle the /start command"""
    user_id = message.from_user.id
    
    # Register the user if not already registered
    user, created = User.get_or_create(
        user_id=user_id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
    )
    
    # Send welcome message
    await message.reply_text(
        f"Welcome to the Passive Voice Grammar Quiz, {message.from_user.first_name}!\n\n"
        f"This bot will test your knowledge of passive voice in English grammar.\n\n"
        f"Commands:\n"
        f"/start - Show this message\n"
        f"/quiz - Start a new quiz\n"
        f"/stats - View your statistics"
    )