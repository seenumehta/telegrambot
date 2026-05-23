"""
AppleFixit Telegram Bot
Conversation-based appointment booking and support
"""

import os
import sys
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from applefixit_agent.conversation import ConversationManager
from applefixit_agent.database import init_db, get_db
from applefixit_agent.models import Appointment, Customer

load_dotenv()

GREETING, BOOKING_DEVICE, BOOKING_ISSUE, BOOKING_CONTACT, BOOKING_TIME, BOOKING_CONFIRM = range(6)
TROUBLESHOOT_START, TROUBLESHOOT_SOLUTION = range(2)
STATUS_TICKET = 7

SPECIALISTS = {
    'iPhone': {
        'name': 'Raj Kumar',
        'phone': '+91-9876543210',
        'experience': '5 years'
    },
    'iPad': {
        'name': 'Priya Singh',
        'phone': '+91-9765432101',
        'experience': '4 years'
    },
    'Mac': {
        'name': 'Amit Patel',
        'phone': '+91-9654321012',
        'experience': '6 years'
    },
    'Apple Watch': {
        'name': 'Sarah Verma',
        'phone': '+91-9543210123',
        'experience': '3 years'
    },
    'AirPods': {
        'name': 'Vikram Singh',
        'phone': '+91-9432101234',
        'experience': '2 years'
    }
}

init_db()
conversation_manager = ConversationManager()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

user_sessions = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {
        'state': 'greeting',
        'data': {},
        'history': []
    }
    
    reply_keyboard = [
        ['📅 Book Appointment', '🔧 Troubleshoot'],
        ['📊 Check Status', '❓ Help']
    ]
    
    await update.message.reply_text(
        "🍎 Welcome to **AppleFixit**!\n\nHow can I help you today?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    
    return GREETING


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🍎 **AppleFixit Bot Help**

*Available Commands:*
/start - Start conversation
/help - Show this help
/cancel - Cancel current operation

*Services:*
📅 **Book Appointment** - Schedule device repair
🔧 **Troubleshoot** - Get diagnostic help
📊 **Check Status** - View repair progress
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "❌ Operation cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {'state': 'greeting', 'data': {}, 'history': []}
    
    session = user_sessions[user_id]
    
    bot_response, next_state, data = conversation_manager.get_response(
        user_input=user_text,
        current_state=session['state'],
        session_data=session['data'],
        conversation_history=session['history']
    )
    
    session['state'] = next_state
    session['data'].update(data)
    session['history'].append({'user': user_text, 'bot': bot_response})
    
    reply_keyboard = None
    
    if next_state == 'booking_device':
        reply_keyboard = [['iPhone', 'iPad'], ['Mac', 'Apple Watch'], ['AirPods']]
    
    elif next_state == 'booking_confirm':
        reply_keyboard = [['Morning (9 AM-12 PM)'], ['Afternoon (12-3 PM)'], ['Evening (3-6 PM)']]
    
    elif next_state == 'completed':
        specialist_number = None
        confirmation_number = None
        specialist = None
        
        if session['data'].get('type') == 'booking':
            try:
                confirmation_number = save_appointment_to_db(user_id, session['data'])
                device_type = session['data'].get('device_type', 'iPhone')
                specialist = SPECIALISTS.get(device_type, SPECIALISTS['iPhone'])
                specialist_number = specialist['phone']
            except Exception as e:
                print(f"Error saving appointment: {e}")
        
        if confirmation_number and specialist_number:
            bot_response = f"✅ *Booking Confirmed!*\n\n"
            bot_response += f"📋 Confirmation: `{confirmation_number}`\n\n"
            bot_response += f"👨‍💼 *Your Specialist*\n"
            bot_response += f"Name: {specialist['name']}\n"
            bot_response += f"Phone: `{specialist_number}`\n"
            bot_response += f"Experience: {specialist['experience']}\n\n"
            bot_response += f"📍 We'll contact you at {session['data'].get('customer_phone', 'your phone')}\n"
            bot_response += f"⏰ Time: {session['data'].get('time_slot', 'Preferred time')}"
        
        reply_keyboard = [['📅 New Booking', '📊 Check Status'], ['/help', '/start']]
        bot_response += "\n\n_What would you like to do next?_"
    
    await update.message.reply_text(
        bot_response,
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True) if reply_keyboard else ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    
    return next_state if next_state != 'completed' else GREETING


async def handle_status_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {
        'state': 'status_ticket',
        'data': {},
        'history': []
    }
    
    await update.message.reply_text(
        "📊 **Repair Status Check**\n\nPlease provide your ticket number (e.g., AFX-00001)",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    
    return STATUS_TICKET


def save_appointment_to_db(user_id, data):
    try:
        db = get_db()
        
        phone = data.get('customer_phone', str(user_id))
        name = data.get('customer_name', 'Telegram User')
        
        customer = db.query(Customer).filter_by(phone=phone).first()
        
        if not customer:
            customer = Customer(
                phone=phone,
                name=name,
                created_at=datetime.now()
            )
            db.add(customer)
            db.commit()
        
        appointment = Appointment(
            customer_id=customer.id,
            device_type=data.get('device_type', ''),
            issue_description=data.get('issue', ''),
            preferred_date=datetime.now(),
            time_slot=data.get('time_slot', ''),
            status='scheduled',
            created_at=datetime.now()
        )
        db.add(appointment)
        db.commit()
        
        confirmation_number = f"AFX-{appointment.id:05d}"
        
        print(f"✅ Appointment saved: {confirmation_number}")
        
        return confirmation_number
    
    except Exception as e:
        db.rollback()
        print(f"Error saving appointment: {e}")
        return None


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_handler(MessageHandler(filters.Regex('^📊'), handle_status_check))
    
    application.add_error_handler(error_handler)
    
    print("🤖 AppleFixit Telegram Bot started!")
    print("Press Ctrl+C to stop")
    
    application.run_polling()


if __name__ == '__main__':
    main()