
import os
import asyncio
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import google.generativeai as genai

# Hardcode the Telegram Bot Token as specified
TELEGRAM_BOT_TOKEN = "7947606721:AAGxfrYl1HI86IRkYKbIyhwkmq4cu2Pb-vo"
# Hardcode the Gemini API Key as specified
GEMINI_API_KEY = "AIzaSyCL0lyAzof7p-R8d8QhExCwNWiZE0WiaXQ"

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

def generate_pirate_response(user_input: str) -> str:
    """
    Generates a pirate-themed response using the Gemini API.
    """
    system_prompt = (
        "You are Blackbeard, the legendary pirate captain. Your responses should be:\n"
        "1. Clear and easy to understand while maintaining pirate character\n"
        "2. Use Telegram markdown formatting (bold **text**, italic *text*, code `text`)\n"
        "3. Structure longer responses with line breaks for readability\n"
        "4. Use pirate slang naturally: 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Arrr!'\n"
        "5. Be helpful and informative while staying in character\n"
        "6. For lists, use bullet points or numbered lists\n"
        "7. Emphasize important words with **bold** text\n"
        "8. Keep responses concise but flavorful\n\n"
        "Example formatting:\n"
        "**Ahoy matey!** Here be what ye need to know:\n"
        "• First point about treasure\n"
        "• Second point about sailing\n\n"
        "*Remember:* Always stay in character as a helpful pirate captain!\n\n"
        "Now respond to this query from the user:\n"
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Create the request in the format matching your curl example
        response = model.generate_content(
            system_prompt + user_input,
            generation_config={
                "max_output_tokens": 1000,
                "response_mime_type": "text/plain"
            }
        )
        return response.text
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        return "**Shiver me timbers!** 🦜\n\nMe parrot seems to have flown off with me words, or perhaps me magic spyglass *(API Key)* be cursed!\n\n*Try again later, matey!*"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text(
        "**Ahoy matey!** 🏴‍☠️\n\n"
        "Captain Blackbeard here, ready to chat! What be on yer mind?\n\n"
        "*Tip:* Just send me any message and I'll respond in true pirate fashion!",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = (
        "**Ahoy! Here be what ye can do with this old sea dog:** 🏴‍☠️\n\n"
        "**Private Chats:**\n"
        "• Just send me any message and I'll respond in true pirate fashion!\n\n"
        "**Group Chats:**\n"
        "• Start yer message with `blackbeard` to get me attention!\n\n"
        "**Commands:**\n"
        "• `/start` - Begin our conversation\n"
        "• `/help` - See this message again\n\n"
        "*Now, what treasure of knowledge be ye seekin'?*"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in group chats, responding if 'Blackbeard' is mentioned."""
    text = update.message.text
    print(f"Group message received from {update.effective_chat.id}: {text}")
    
    if text.lower().startswith("blackbeard "):
        query = text[len("blackbeard "):]
        if query:
            pirate_reply = generate_pirate_response(query)
            await update.message.reply_text(pirate_reply, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(
                "**Aye, ye called?** What be yer query, matey? 🏴‍☠️", 
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in private chats."""
    text = update.message.text
    print(f"Private message received from {update.effective_chat.id}: {text}")
    
    pirate_reply = generate_pirate_response(text)
    await update.message.reply_text(pirate_reply, parse_mode=ParseMode.MARKDOWN)

def main():
    """Start the bot."""
    print("Blackbeard Bot starting...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
        return
    
    print(f"Using Telegram Bot Token: ...{TELEGRAM_BOT_TOKEN[-6:]}")
    print("Gemini API Key is hardcoded.")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handlers
    # Group messages (only respond when mentioned)
    application.add_handler(MessageHandler(
        filters.TEXT & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
        handle_group_message
    ))
    
    # Private messages (respond to all)
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE,
        handle_private_message
    ))
    
    # Start polling
    print("Blackbeard Bot is running and polling for messages...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
