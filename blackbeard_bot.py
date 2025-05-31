
import os
import asyncio
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
        "You are Blackbeard, the legendary pirate captain. Your responses must be:\n"
        "1. PLAIN TEXT ONLY - Never use any markdown, asterisks, underscores, brackets, or special formatting\n"
        "2. Clear and easy to understand while maintaining pirate character\n"
        "3. Use simple line breaks for readability, no other formatting\n"
        "4. Use pirate slang naturally: 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Arrr!'\n"
        "5. Be helpful and informative while staying in character\n"
        "6. Keep responses concise but flavorful\n"
        "7. Only use regular text and emojis - absolutely no markdown symbols\n"
        "8. Never use bold, italic, code blocks, or any text formatting\n\n"
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
        
        # Return plain text to avoid markdown parsing issues
        return response.text
        
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        return "Shiver me timbers! 🦜\n\nMe parrot seems to have flown off with me words, or perhaps me magic spyglass be cursed!\n\nTry again later, matey!"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    await update.message.reply_text(
        "Ahoy matey! 🏴‍☠️\n\n"
        "Captain Blackbeard here, ready to chat! What be on yer mind?\n\n"
        "Tip: Just send me any message and I'll respond in true pirate fashion!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = (
        "Ahoy! Here be what ye can do with this old sea dog: 🏴‍☠️\n\n"
        "Private Chats:\n"
        "• Just send me any message and I'll respond in true pirate fashion!\n\n"
        "Group Chats:\n"
        "• Start yer message with 'blackbeard' to get me attention!\n\n"
        "Commands:\n"
        "• /start - Begin our conversation\n"
        "• /help - See this message again\n\n"
        "Now, what treasure of knowledge be ye seekin'?"
    )
    await update.message.reply_text(help_text)

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in group chats, responding if 'Blackbeard' is mentioned."""
    text = update.message.text
    print(f"Group message received from {update.effective_chat.id}: {text}")
    
    if text.lower().startswith("blackbeard "):
        query = text[len("blackbeard "):]
        if query:
            pirate_reply = generate_pirate_response(query)
            await update.message.reply_text(pirate_reply)
        else:
            await update.message.reply_text(
                "Aye, ye called? What be yer query, matey? 🏴‍☠️"
            )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in private chats."""
    text = update.message.text
    print(f"Private message received from {update.effective_chat.id}: {text}")
    
    pirate_reply = generate_pirate_response(text)
    await update.message.reply_text(pirate_reply)

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
