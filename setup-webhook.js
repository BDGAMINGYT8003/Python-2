
const TelegramBot = require('node-telegram-bot-api');

const TELEGRAM_BOT_TOKEN = "7932939642:AAHJGbqUb1ojESr9eMCvwXEobeGGpVznwC4";

async function setupWebhook() {
  const bot = new TelegramBot(TELEGRAM_BOT_TOKEN);
  
  try {
    // Get your Repl URL - replace with your actual URL
    const webhookUrl = process.env.REPL_SLUG ? 
      `https://${process.env.REPL_SLUG}.${process.env.REPL_OWNER}.repl.co/webhook` :
      'https://your-actual-repl-url.repl.co/webhook';
    
    console.log(`Setting webhook to: ${webhookUrl}`);
    
    await bot.setWebHook(webhookUrl);
    console.log('✅ Webhook set successfully!');
    
    // Check webhook info
    const webhookInfo = await bot.getWebHookInfo();
    console.log('Webhook info:', webhookInfo);
    
  } catch (error) {
    console.error('❌ Error setting webhook:', error);
  }
}

setupWebhook();
