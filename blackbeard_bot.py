import os
from telegraph import Telegraph, MessageHandler, Chat, Filter, Entity, Message
import google.generativeai as genai

# Hardcode the Telegram Bot Token as specified
TELEGRAM_BOT_TOKEN = "7947606721:AAGxfrYl1HI86IRkYKbIyhwkmq4cu2Pb-vo"
# Hardcode the Gemini API Key as specified
GEMINI_API_KEY = "AIzaSyCL0lyAzof7p-R8d8QhExCwNWiZE0WiaXQ"

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Create the Telegraph bot instance
bot = Telegraph(token=TELEGRAM_BOT_TOKEN)

def generate_pirate_response(user_input: str) -> str:
    """
    Generates a pirate-themed response using the Gemini API.
    """
    # The check for missing GEMINI_API_KEY is removed as it's now hardcoded.
    # If the hardcoded key is invalid, the API call will fail, which is handled by the try-except block.

    system_prompt = (
        "You are Blackbeard, the legendary pirate captain. Your voice is that of a seasoned sailor of the high seas, rough but clear. "
        "You are speaking to a curious matey. Always stay in character. "
        "Use plenty of pirate slang and phrases like 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Doubloons', 'Scallywag', 'Jolly Roger', etc. "
        "Your responses should be direct but colorful. Be confident, perhaps a little boastful, but not outright aggressive unless the user is challenging ye. "
        "If you don't understand something or it's a modern concept, express your confusion in a pirate way, like 'What be this newfangled contraption ye speak of?' or 'That be sorcery to me ears!'. "
        "Keep your responses relatively concise but flavorful. Never break character, not even for a king's ransom! "
        "Now, respond to this query from the user:\n"
    )
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(system_prompt + user_input)
        return response.text
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        # Consider a more user-friendly message if the API key is definitively invalid
        return "Shiver me timbers! Me parrot seems to have flown off with me words, or perhaps me magic spyglass (API Key) be cursed! Try again later, matey!"

async def group_message_handler(message: Message, chat: Chat, text: str, entity: Entity):
    """Handles messages in group chats, responding if 'Blackbeard' is mentioned."""
    print(f"Group message received from {chat.id}: {text}")
    if text.lower().startswith("blackbeard "):
        query = text[len("blackbeard "):]
        if query: # Ensure there's a query after "Blackbeard "
            pirate_reply = generate_pirate_response(query)
            await chat.reply(pirate_reply)
        else:
            await chat.reply("Aye, ye called? What be yer query, matey?")


async def private_message_handler(message: Message, chat: Chat, text: str, entity: Entity):
    """Handles messages in private chats."""
    print(f"Private message received from {chat.id}: {text}")
    pirate_reply = generate_pirate_response(text)
    await chat.reply(pirate_reply)

# Register the new handlers
bot.add_handler(MessageHandler(Filter.TEXT & (Filter.Chat.Type.GROUP | Filter.Chat.Type.SUPERGROUP), group_message_handler))
bot.add_handler(MessageHandler(Filter.TEXT & Filter.Chat.Type.PRIVATE, private_message_handler))

if __name__ == '__main__':
    print("Blackbeard Bot starting...")
    if not TELEGRAM_BOT_TOKEN: # Basic check for Telegram token
        print("Error: TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
    else:
        # Removed GEMINI_API_KEY specific checks/warnings from here as it's hardcoded
        print(f"Using Telegram Bot Token: ...{TELEGRAM_BOT_TOKEN[-6:]}")
        print("Gemini API Key is hardcoded.") # Indication that the key is hardcoded
        bot.start_polling()
        print("Blackbeard Bot is running and polling for messages...")