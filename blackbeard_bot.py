
import os
import asyncio
import requests
import json
import sqlite3
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socketserver

# Hardcode the Telegram Bot Token as specified
TELEGRAM_BOT_TOKEN = "7947606721:AAGxfrYl1HI86IRkYKbIyhwkmq4cu2Pb-vo"
# Hardcode the Gemini API Key as specified
GEMINI_API_KEY = "AIzaSyCL0lyAzof7p-R8d8QhExCwNWiZE0WiaXQ"

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Initialize database for persistent memory and stats
def init_database():
    conn = sqlite3.connect('blackbeard_memory.db')
    cursor = conn.cursor()
    
    # Create conversation memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_messages INTEGER DEFAULT 0,
            total_replies INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize stats if empty
    cursor.execute('SELECT COUNT(*) FROM stats')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO stats (total_messages, total_replies) VALUES (0, 0)')
    
    conn.commit()
    conn.close()

def get_conversation_context(chat_id, user_id, limit=5):
    """Get recent conversation context for memory"""
    conn = sqlite3.connect('blackbeard_memory.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT message, response FROM conversations 
        WHERE chat_id = ? AND user_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    ''', (chat_id, user_id, limit))
    
    history = cursor.fetchall()
    conn.close()
    
    context = ""
    for msg, resp in reversed(history):
        context += f"Previous message: {msg}\nYour previous response: {resp}\n\n"
    
    return context

def save_conversation(chat_id, user_id, message, response):
    """Save conversation to memory"""
    conn = sqlite3.connect('blackbeard_memory.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO conversations (chat_id, user_id, message, response)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, user_id, message, response))
    
    conn.commit()
    conn.close()

def update_stats(message_received=False, reply_sent=False):
    """Update bot statistics"""
    conn = sqlite3.connect('blackbeard_memory.db')
    cursor = conn.cursor()
    
    if message_received:
        cursor.execute('UPDATE stats SET total_messages = total_messages + 1, last_updated = CURRENT_TIMESTAMP')
    if reply_sent:
        cursor.execute('UPDATE stats SET total_replies = total_replies + 1, last_updated = CURRENT_TIMESTAMP')
    
    conn.commit()
    conn.close()

def get_stats():
    """Get current bot statistics"""
    conn = sqlite3.connect('blackbeard_memory.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT total_messages, total_replies FROM stats ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    
    # Get recent chats
    cursor.execute('''
        SELECT DISTINCT chat_id, MAX(timestamp) as last_message 
        FROM conversations 
        GROUP BY chat_id 
        ORDER BY last_message DESC 
        LIMIT 5
    ''')
    recent_chats = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_messages': result[0] if result else 0,
        'total_replies': result[1] if result else 0,
        'recent_chats': recent_chats
    }

def generate_pirate_response(user_input: str, chat_id: int, user_id: int) -> str:
    """Generates a pirate-themed response using the Gemini API with memory"""
    
    # Get conversation context for memory
    context = get_conversation_context(chat_id, user_id)
    
    system_prompt = (
        "You are Blackbeard, the legendary pirate captain. Your responses must be:\n"
        "1. PLAIN TEXT ONLY - Never use any markdown, asterisks, underscores, brackets, or special formatting\n"
        "2. Clear and easy to understand while maintaining pirate character\n"
        "3. Brief by default unless longer responses are specifically requested\n"
        "4. Use pirate slang naturally: 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Arrr!'\n"
        "5. Remember previous conversations - here's the recent context:\n"
        f"{context}\n"
        "6. Be helpful and informative while staying in character\n"
        "7. Only use regular text and emojis - absolutely no markdown symbols\n"
        "8. Never use bold, italic, code blocks, or any text formatting\n\n"
        "Now respond to this query from the user:\n"
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        response = model.generate_content(
            system_prompt + user_input,
            generation_config={
                "max_output_tokens": 1000,
                "response_mime_type": "text/plain"
            }
        )
        
        # Save conversation to memory
        save_conversation(chat_id, user_id, user_input, response.text)
        
        return response.text
    except Exception as e:
        print(f"Error generating response from Gemini: {e}")
        return "Shiver me timbers! Me parrot seems to have flown off with me words! Try again later, matey! 🦜"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    response = "Ahoy matey! Blackbeard here, ready to chat! What be on yer mind? 🏴‍☠️"
    await update.message.reply_text(response)
    
    # Update stats
    update_stats(message_received=True, reply_sent=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = (
        "Ahoy! Here be what ye can do with this old sea dog:\n\n"
        "• In private chats: Just send me any message and I'll respond in true pirate fashion!\n"
        "• In groups: Start yer message with 'blackbeard' to get me attention!\n"
        "• Reply to me messages to continue our conversation!\n"
        "• Use /start to begin our conversation\n"
        "• Use /help to see this message again\n\n"
        "I remember our past conversations, so feel free to reference what we talked about before! ⚓"
    )
    await update.message.reply_text(help_text)
    
    # Update stats
    update_stats(message_received=True, reply_sent=True)

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in group chats, responding if 'Blackbeard' is mentioned or if replying to bot."""
    text = update.message.text or ""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    print(f"Group message received from {chat_id}: {text}")
    
    # Update message count
    update_stats(message_received=True)
    
    should_respond = False
    query = text
    
    # Check if message starts with "blackbeard"
    if text.lower().startswith("blackbeard "):
        query = text[len("blackbeard "):]
        should_respond = True
    elif text.lower().startswith("blackbeard"):
        query = text[len("blackbeard"):].strip()
        should_respond = True
    
    # Check if replying to bot
    if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
        should_respond = True
        query = text
    
    if should_respond and query.strip():
        pirate_reply = generate_pirate_response(query, chat_id, user_id)
        await update.message.reply_text(pirate_reply)
        update_stats(reply_sent=True)
    elif should_respond:
        await update.message.reply_text("Aye, ye called? What be yer query, matey? 🏴‍☠️")
        update_stats(reply_sent=True)

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in private chats."""
    text = update.message.text or ""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    print(f"Private message received from {chat_id}: {text}")
    
    # Update stats
    update_stats(message_received=True)
    
    pirate_reply = generate_pirate_response(text, chat_id, user_id)
    await update.message.reply_text(pirate_reply)
    update_stats(reply_sent=True)

# Dashboard HTTP Handler
class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stats':
            # API endpoint for stats
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            stats = get_stats()
            self.wfile.write(json.dumps(stats).encode())
        elif self.path == '/' or self.path == '/index.html':
            # Serve dashboard HTML
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blackbeard's Live Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #2c3e50;
            color: #ecf0f1;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #34495e;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(0,0,0,0.5);
        }
        h1 {
            color: #e67e22;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background-color: #2c3e50;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #e67e22;
            text-align: center;
        }
        .stat-number {
            font-size: 2rem;
            color: #f1c40f;
            font-weight: bold;
        }
        .stat-label {
            color: #bdc3c7;
            margin-top: 5px;
        }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background-color: #27ae60;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .update-time {
            text-align: center;
            color: #bdc3c7;
            font-size: 0.9rem;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏴‍☠️ Blackbeard's Live Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalMessages">0</div>
                <div class="stat-label">Total Messages Received</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalReplies">0</div>
                <div class="stat-label">Replies Sent by Blackbeard</div>
            </div>
        </div>
        
        <div class="update-time">
            <span class="live-indicator"></span>
            <span>Live Dashboard - Last updated: <span id="lastUpdate">Never</span></span>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('totalMessages').textContent = data.total_messages;
                    document.getElementById('totalReplies').textContent = data.total_replies;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Error fetching stats:', error);
                });
        }

        // Update stats immediately and then every 5 seconds
        updateStats();
        setInterval(updateStats, 5000);
    </script>
</body>
</html>
            """
            self.wfile.write(html_content.encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_dashboard_server():
    """Start the dashboard web server"""
    try:
        with socketserver.TCPServer(("0.0.0.0", 5000), DashboardHandler) as httpd:
            print("Dashboard server running on http://0.0.0.0:5000")
            httpd.serve_forever()
    except Exception as e:
        print(f"Error starting dashboard server: {e}")

def main():
    """Start the bot and dashboard."""
    print("Initializing Blackbeard Bot with dashboard...")
    
    # Initialize database
    init_database()
    
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
        return
    
    print(f"Using Telegram Bot Token: ...{TELEGRAM_BOT_TOKEN[-6:]}")
    print("Gemini API Key is hardcoded.")
    
    # Start dashboard server in a separate thread
    dashboard_thread = threading.Thread(target=start_dashboard_server, daemon=True)
    dashboard_thread.start()
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handlers
    # Group messages (respond when mentioned or replied to)
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
    print("Blackbeard Bot is running with live dashboard on port 5000...")
    print("Dashboard URL: http://0.0.0.0:5000")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
