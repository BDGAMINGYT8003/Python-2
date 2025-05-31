
// Cloudflare Workers version of Blackbeard Bot
// This file is optimized for Cloudflare Workers deployment

const TELEGRAM_BOT_TOKEN = "7947606721:AAGxfrYl1HI86IRkYKbIyhwkmq4cu2Pb-vo";
const GEMINI_API_KEY = "AIzaSyCL0lyAzof7p-R8d8QhExCwNWiZE0WiaXQ";

// In-memory cache for conversation context (Workers KV can be added for persistence)
const conversationCache = new Map();

async function generatePirateResponse(userInput, chatId, userId) {
  try {
    const context = getConversationContext(chatId, userId);
    
    const systemPrompt = `You are Blackbeard, the legendary pirate captain. Your responses must be:
1. PLAIN TEXT ONLY - Never use markdown, asterisks, underscores, brackets, or special formatting
2. Clear and easy to understand while maintaining pirate character
3. Brief by default unless longer responses are specifically requested
4. Use pirate slang naturally: 'Ahoy!', 'Matey', 'Shiver me timbers!', 'Me hearty', 'Arrr!'
5. Remember context: ${context}
6. Be helpful and informative while staying in character
7. Only use regular text and emojis - absolutely no markdown symbols

Respond to: ${userInput}`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: systemPrompt }] }],
          generationConfig: { maxOutputTokens: 800, responseMimeType: "text/plain" }
        })
      }
    );

    const data = await response.json();
    const generatedText = data.candidates?.[0]?.content?.parts?.[0]?.text || 
                         "Arrr! Me parrot's got me tongue! Try again, matey! 🦜";

    saveConversationContext(chatId, userId, userInput, generatedText);
    return generatedText;
  } catch (error) {
    return "Shiver me timbers! The winds be against me! Try again, matey! ⚡";
  }
}

function getConversationContext(chatId, userId) {
  const key = `${chatId}_${userId}`;
  const cached = conversationCache.get(key);
  return cached ? cached.slice(-3).map(c => `Previous: ${c.message}\nBlackbeard: ${c.response}`).join('\n') : "";
}

function saveConversationContext(chatId, userId, message, response) {
  const key = `${chatId}_${userId}`;
  if (!conversationCache.has(key)) {
    conversationCache.set(key, []);
  }
  const history = conversationCache.get(key);
  history.push({ message, response, timestamp: Date.now() });
  if (history.length > 5) history.shift(); // Keep last 5 conversations
}

async function sendTelegramMessage(chatId, text) {
  await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text })
  });
}

async function processUpdate(update) {
  const message = update.message;
  if (!message || !message.text) return;

  const chatId = message.chat.id;
  const userId = message.from.id;
  const text = message.text;
  const isPrivate = message.chat.type === 'private';
  const isGroup = message.chat.type === 'group' || message.chat.type === 'supergroup';

  let shouldRespond = false;
  let query = text;

  if (isPrivate) {
    shouldRespond = true;
  } else if (isGroup) {
    if (text.toLowerCase().startsWith('blackbeard ')) {
      query = text.substring(11);
      shouldRespond = true;
    } else if (text.toLowerCase().startsWith('blackbeard')) {
      query = text.substring(10).trim();
      shouldRespond = true;
    } else if (message.reply_to_message?.from?.is_bot) {
      shouldRespond = true;
    }
  }

  if (shouldRespond && query.trim()) {
    const response = await generatePirateResponse(query, chatId, userId);
    await sendTelegramMessage(chatId, response);
  } else if (shouldRespond) {
    await sendTelegramMessage(chatId, "Aye, ye called? What be yer query, matey? 🏴‍☠️");
  }
}

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  
  if (url.pathname === '/webhook' && request.method === 'POST') {
    try {
      const update = await request.json();
      await processUpdate(update);
      return new Response('OK', { status: 200 });
    } catch (error) {
      return new Response('Error processing update', { status: 500 });
    }
  }
  
  if (url.pathname === '/') {
    return new Response(`
<!DOCTYPE html>
<html>
<head><title>⚡ Blackbeard Bot - Cloudflare Workers</title></head>
<body style="font-family: Arial; background: #2c3e50; color: #ecf0f1; text-align: center; padding: 50px;">
  <h1>🏴‍☠️ Blackbeard Bot Active</h1>
  <p>⚡ Supercharged on Cloudflare Workers</p>
  <p>🚀 Ultra-fast global deployment</p>
</body>
</html>
    `, { headers: { 'Content-Type': 'text/html' } });
  }
  
  return new Response('Not Found', { status: 404 });
}
