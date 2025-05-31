
const TelegramBot = require('node-telegram-bot-api');
const sqlite3 = require('sqlite3').verbose();
const express = require('express');
const path = require('path');
const fs = require('fs');
// Using built-in fetch (available in Node.js 18+)

// Hardcoded credentials as specified
const TELEGRAM_BOT_TOKEN = "7932939642:AAHJGbqUb1ojESr9eMCvwXEobeGGpVznwC4";
const GEMINI_API_KEY = "AIzaSyCL0lyAzof7p-R8d8QhExCwNWiZE0WiaXQ";

// Bot configuration for webhook mode
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, {
  webHook: false, // We'll handle webhooks manually
  request: {
    agentOptions: {
      keepAlive: true,
      maxSockets: 50 // High connection pool
    }
  }
});

// Database initialization with performance optimizations
let db;

function initDatabase() {
  return new Promise((resolve, reject) => {
    db = new sqlite3.Database('./blackbeard_memory.db', (err) => {
      if (err) {
        reject(err);
        return;
      }
      
      // Performance optimizations
      db.run("PRAGMA journal_mode = WAL;");
      db.run("PRAGMA synchronous = NORMAL;");
      db.run("PRAGMA cache_size = 10000;");
      db.run("PRAGMA temp_store = MEMORY;");
      
      // Create tables
      const queries = [
        `CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          chat_id INTEGER,
          user_id INTEGER,
          message TEXT,
          response TEXT,
          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )`,
        `CREATE TABLE IF NOT EXISTS stats (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          total_messages INTEGER DEFAULT 0,
          total_replies INTEGER DEFAULT 0,
          last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )`,
        `CREATE INDEX IF NOT EXISTS idx_conversations_chat_user ON conversations(chat_id, user_id);`,
        `CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);`
      ];
      
      let completed = 0;
      queries.forEach(query => {
        db.run(query, (err) => {
          if (err) console.error('Database setup error:', err);
          completed++;
          if (completed === queries.length) {
            // Initialize stats if empty
            db.get('SELECT COUNT(*) as count FROM stats', (err, row) => {
              if (!err && row.count === 0) {
                db.run('INSERT INTO stats (total_messages, total_replies) VALUES (0, 0)');
              }
              resolve();
            });
          }
        });
      });
    });
  });
}

// Optimized memory cache for frequent operations
const memoryCache = new Map();
const CACHE_TTL = 300000; // 5 minutes

function getCachedContext(chat_id, user_id) {
  const key = `${chat_id}_${user_id}`;
  const cached = memoryCache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }
  return null;
}

function setCachedContext(chat_id, user_id, data) {
  const key = `${chat_id}_${user_id}`;
  memoryCache.set(key, {
    data,
    timestamp: Date.now()
  });
}

// Ultra-fast conversation context retrieval
function getConversationContext(chat_id, user_id, limit = 3) {
  return new Promise((resolve) => {
    // Check cache first
    const cached = getCachedContext(chat_id, user_id);
    if (cached) {
      resolve(cached);
      return;
    }
    
    db.all(
      `SELECT message, response FROM conversations 
       WHERE chat_id = ? AND user_id = ? 
       ORDER BY timestamp DESC LIMIT ?`,
      [chat_id, user_id, limit],
      (err, rows) => {
        if (err) {
          resolve("");
          return;
        }
        
        let context = "";
        rows.reverse().forEach(row => {
          context += `Previous: ${row.message}\nBlackbeard: ${row.response}\n\n`;
        });
        
        setCachedContext(chat_id, user_id, context);
        resolve(context);
      }
    );
  });
}

// Async database operations for non-blocking performance
function saveConversationAsync(chat_id, user_id, message, response) {
  setImmediate(() => {
    db.run(
      'INSERT INTO conversations (chat_id, user_id, message, response) VALUES (?, ?, ?, ?)',
      [chat_id, user_id, message, response]
    );
    // Update cache
    setCachedContext(chat_id, user_id, null);
  });
}

function updateStatsAsync(messageReceived = false, replySent = false) {
  setImmediate(() => {
    if (messageReceived) {
      db.run('UPDATE stats SET total_messages = total_messages + 1, last_updated = CURRENT_TIMESTAMP');
    }
    if (replySent) {
      db.run('UPDATE stats SET total_replies = total_replies + 1, last_updated = CURRENT_TIMESTAMP');
    }
  });
}

// Optimized Gemini API call with connection pooling
async function generatePirateResponse(userInput, chat_id, user_id) {
  try {
    const context = await getConversationContext(chat_id, user_id);
    
    const systemPrompt = `You are Blackbeard, the legendary pirate captain. Your responses must be:
1. PLAIN TEXT ONLY - Never use markdown, asterisks, underscores, brackets, or special formatting
2. Clear and easy to understand while maintaining pirate character
3. Brief by default unless longer responses are specifically requested
4. Use pirate slang naturally: 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Arrr!'
5. Remember previous conversations: ${context}
6. Be helpful and informative while staying in character
7. Only use regular text and emojis - absolutely no markdown symbols
8. Keep responses concise and punchy

Respond to: ${userInput}`;

    const requestBody = {
      contents: [{
        role: "user",
        parts: [{ text: systemPrompt }]
      }],
      generationConfig: {
        maxOutputTokens: 800,
        responseMimeType: "text/plain"
      }
    };

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        timeout: 8000 // Fast timeout
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    const generatedText = data.candidates?.[0]?.content?.parts?.[0]?.text || 
                         "Arrr! Me parrot's got me tongue! Try again, matey! 🦜";

    // Save conversation asynchronously
    saveConversationAsync(chat_id, user_id, userInput, generatedText);
    
    return generatedText;
  } catch (error) {
    console.error('Gemini API error:', error);
    return "Shiver me timbers! The winds be against me! Try again in a moment, matey! ⚡";
  }
}

// Webhook setup function
async function setupWebhook() {
  try {
    // Use the correct Replit URL format
    const webhookUrl = `https://${process.env.REPLIT_DEV_DOMAIN || 'your-repl-name.your-username.repl.co'}/webhook`;
    
    await bot.setWebHook(webhookUrl);
    console.log(`🌐 Webhook set to: ${webhookUrl}`);
  } catch (error) {
    console.error('❌ Error setting webhook:', error);
  }
}

// High-performance dashboard server
const app = express();

// Webhook endpoint for Telegram
app.post('/webhook', express.json(), async (req, res) => {
  try {
    const update = req.body;
    
    if (update.message) {
      await processMessage(update.message);
    }
    
    res.status(200).send('OK');
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).send('Error processing update');
  }
});

// Process Telegram messages manually
async function processMessage(msg) {
  if (msg.text?.startsWith('/')) {
    // Handle commands
    if (msg.text === '/start') {
      const response = "Ahoy matey! Blackbeard here, ready for adventure! What be on yer mind? 🏴‍☠️";
      await bot.sendMessage(msg.chat.id, response);
      updateStatsAsync(true, true);
      return;
    } else if (msg.text === '/help') {
      const helpText = `Ahoy! Here be what ye can do with this old sea dog:

• In private chats: Just send me any message!
• In groups: Start yer message with 'blackbeard'!
• Reply to me messages to continue our conversation!

I remember our past conversations, so feel free to reference what we talked about before! ⚓`;
      await bot.sendMessage(msg.chat.id, helpText);
      updateStatsAsync(true, true);
      return;
    }
    return;
  }
  
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const text = msg.text || "";
  const isPrivate = msg.chat.type === 'private';
  const isGroup = msg.chat.type === 'group' || msg.chat.type === 'supergroup';
  
  updateStatsAsync(true);
  
  let shouldRespond = false;
  let query = text;
  
  if (isPrivate) {
    shouldRespond = true;
  } else if (isGroup) {
    // Check for mentions or replies
    if (text.toLowerCase().startsWith('blackbeard ')) {
      query = text.substring(11);
      shouldRespond = true;
    } else if (text.toLowerCase().startsWith('blackbeard')) {
      query = text.substring(10).trim();
      shouldRespond = true;
    } else if (msg.reply_to_message?.from?.is_bot) {
      shouldRespond = true;
    }
  }
  
  if (shouldRespond && query.trim()) {
    try {
      const response = await generatePirateResponse(query, chatId, userId);
      await bot.sendMessage(chatId, response);
      updateStatsAsync(false, true);
    } catch (error) {
      console.error('Error processing message:', error);
      await bot.sendMessage(chatId, "Arrr! Something went awry! Try again, matey! ⚡");
    }
  } else if (shouldRespond) {
    await bot.sendMessage(chatId, "Aye, ye called? What be yer query, matey? 🏴‍☠️");
    updateStatsAsync(false, true);
  }
}

// In-memory stats cache
let statsCache = { total_messages: 0, total_replies: 0, last_updated: new Date() };
let statsCacheTime = 0;

function getStats() {
  return new Promise((resolve) => {
    // Use cache if recent
    if (Date.now() - statsCacheTime < 2000) {
      resolve(statsCache);
      return;
    }
    
    db.get('SELECT total_messages, total_replies FROM stats ORDER BY id DESC LIMIT 1', (err, row) => {
      if (!err && row) {
        statsCache = {
          total_messages: row.total_messages,
          total_replies: row.total_replies,
          last_updated: new Date()
        };
        statsCacheTime = Date.now();
      }
      resolve(statsCache);
    });
  });
}

app.get('/api/stats', async (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Content-Type', 'application/json');
  
  try {
    const stats = await getStats();
    res.json(stats);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

app.get('/', (req, res) => {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Blackbeard's Supercharged Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #2c3e50, #34495e); color: #ecf0f1; margin: 0; padding: 20px; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; background: rgba(52, 73, 94, 0.9); border-radius: 15px; padding: 30px; box-shadow: 0 0 30px rgba(0,0,0,0.5); backdrop-filter: blur(10px); }
        h1 { color: #f39c12; text-align: center; margin-bottom: 40px; font-size: 2.8rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .performance-badge { background: linear-gradient(45deg, #e74c3c, #f39c12); padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: bold; display: inline-block; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-bottom: 40px; }
        .stat-card { background: linear-gradient(145deg, #2c3e50, #34495e); padding: 25px; border-radius: 15px; border-left: 5px solid #f39c12; text-align: center; transition: transform 0.3s ease; }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-number { font-size: 2.5rem; color: #f1c40f; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
        .stat-label { color: #bdc3c7; margin-top: 8px; font-size: 1.1rem; }
        .live-indicator { display: inline-block; width: 12px; height: 12px; background: linear-gradient(45deg, #27ae60, #2ecc71); border-radius: 50%; animation: pulse 1.5s infinite; margin-right: 12px; }
        @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.7; } }
        .update-time { text-align: center; color: #bdc3c7; font-size: 1rem; margin-top: 30px; padding: 15px; background: rgba(44, 62, 80, 0.5); border-radius: 10px; }
        .status-bar { background: linear-gradient(90deg, #27ae60, #2ecc71); height: 4px; border-radius: 2px; margin-bottom: 20px; animation: loading 2s ease-in-out infinite; }
        @keyframes loading { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="status-bar"></div>
        <h1>⚡ Blackbeard's Supercharged Dashboard</h1>
        <div class="performance-badge">🚀 Ultra-High Performance Mode Active</div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalMessages">0</div>
                <div class="stat-label">⚡ Messages Processed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalReplies">0</div>
                <div class="stat-label">🏴‍☠️ Pirate Replies Sent</div>
            </div>
        </div>
        
        <div class="update-time">
            <span class="live-indicator"></span>
            <span>⚡ Real-time Dashboard - Updates every 2 seconds - Last update: <span id="lastUpdate">Never</span></span>
        </div>
    </div>

    <script>
        let updateCount = 0;
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('totalMessages').textContent = data.total_messages;
                    document.getElementById('totalReplies').textContent = data.total_replies;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    updateCount++;
                })
                .catch(error => console.error('Error fetching stats:', error));
        }
        updateStats();
        setInterval(updateStats, 2000); // Ultra-fast 2-second updates
    </script>
</body>
</html>`;
  res.send(html);
});

// Start the optimized bot system
async function startBot() {
  try {
    console.log('🚀 Initializing Supercharged Blackbeard Bot...');
    
    await initDatabase();
    console.log('⚡ Database optimized with performance settings');
    
    // Start dashboard server
    const server = app.listen(5000, '0.0.0.0', async () => {
      console.log('🌐 Ultra-fast dashboard running on http://0.0.0.0:5000');
      
      // Set up webhook after server starts
      await setupWebhook();
    });
    
    // Optimize server settings
    server.keepAliveTimeout = 65000;
    server.headersTimeout = 66000;
    
    console.log('🏴‍☠️ Blackbeard Bot is SUPERCHARGED and ready!');
    console.log('⚡ Performance optimizations: ✅ Active');
    console.log('🚀 Webhook mode: ✅ Active');
    console.log('📊 Real-time dashboard: ✅ Running');
    
  } catch (error) {
    console.error('❌ Error starting bot:', error);
    process.exit(1);
  }
}

// Cloudflare Workers compatibility layer
if (typeof addEventListener !== 'undefined') {
  // Cloudflare Workers environment
  addEventListener('fetch', event => {
    event.respondWith(handleCloudflareRequest(event.request));
  });
  
  async function handleCloudflareRequest(request) {
    const url = new URL(request.url);
    
    if (url.pathname === '/webhook' && request.method === 'POST') {
      try {
        const update = await request.json();
        // Process Telegram webhook update
        if (update.message) {
          // Handle message processing for Cloudflare Workers
          await processMessage(update.message);
        }
        return new Response('OK', { status: 200 });
      } catch (error) {
        return new Response('Error', { status: 500 });
      }
    }
    
    return new Response('Not Found', { status: 404 });
  }
} else {
  // Regular Node.js environment (Replit)
  startBot();
}

module.exports = { bot, app };
