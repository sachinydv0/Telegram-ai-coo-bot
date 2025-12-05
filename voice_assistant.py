import os
import requests
from dotenv import load_dotenv
from google_sheets import add_customer, add_task, add_inventory, add_transaction

load_dotenv()

# Using AssemblyAI for free transcription (free tier available)
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

async def download_voice_file(context, file_id):
    """Download voice file from Telegram"""
    try:
        file = await context.bot.get_file(file_id)
        voice_path = f"temp_voice_{file_id}.ogg"
        await file.download_to_drive(voice_path)
        return voice_path
    except Exception as e:
        print(f"Error downloading voice: {e}")
        return None

def transcribe_audio_free(audio_file_path):
    """Transcribe audio using free online service"""
    try:
        # Using a free transcription API
        with open(audio_file_path, 'rb') as audio_file:
            files = {'file': audio_file}
            # Using AssemblyAI free tier
            headers = {"Authorization": ASSEMBLYAI_API_KEY} if ASSEMBLYAI_API_KEY else {}
            
            # For free tier without API key, we'll use a simple approach
            # In production, use proper speech-to-text service
            
            # Using SpeechRecognition library as fallback
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            
            with sr.AudioFile(audio_file_path) as source:
                audio = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                return "Could not understand audio"
            except sr.RequestError:
                return "Error with speech recognition service"
    
    except Exception as e:
        print(f"Error transcribing: {e}")
        return f"Error: {str(e)}"

def parse_voice_command(transcribed_text, module_type):
    """Parse transcribed text to extract data"""
    text_lower = transcribed_text.lower()
    
    if module_type == 'crm':
        # Example: "Add customer John Doe john at example.com 9876543210 ABC Corp"
        if 'add customer' in text_lower or 'new customer' in text_lower:
            # Extract customer details from voice
            return parse_customer_voice(transcribed_text)
    
    elif module_type == 'task':
        # Example: "Add task Follow up with client assign to John"
        if 'add task' in text_lower or 'new task' in text_lower:
            return parse_task_voice(transcribed_text)
    
    elif module_type == 'inventory':
        # Example: "Add product laptop quantity 10 price 50000"
        if 'add product' in text_lower or 'new product' in text_lower:
            return parse_inventory_voice(transcribed_text)
    
    elif module_type == 'finance':
        # Example: "Add transaction customer John amount 5000"
        if 'add transaction' in text_lower or 'add sale' in text_lower:
            return parse_finance_voice(transcribed_text)
    
    return None

def parse_customer_voice(text):
    """Extract customer info from voice"""
    # Simple parsing - in production use NLP
    words = text.split()
    
    # Try to extract email and phone
    email = None
    phone = None
    
    for i, word in enumerate(words):
        if '@' in word:
            email = word
        if len(word) >= 10 and word.isdigit():
            phone = word
    
    # Reconstruct name (skip "add", "customer", email, phone)
    name_words = [w for w in words if w.lower() not in ['add', 'customer'] 
                  and '@' not in w and not w.isdigit()]
    name = ' '.join(name_words[:2]) if name_words else "Unknown"
    
    company = name_words[-1] if len(name_words) > 2 else "Unknown"
    
    return {
        'type': 'customer',
        'name': name,
        'email': email or 'not provided',
        'phone': phone or 'not provided',
        'company': company
    }

def parse_task_voice(text):
    """Extract task info from voice"""
    words = text.split()
    
    # Remove "add", "task" keywords
    task_words = [w for w in words if w.lower() not in ['add', 'task', 'assign', 'to', 'for']]
    
    # First part is task name, rest is assignee
    task_name = task_words[0] if task_words else "Unnamed Task"
    assigned_to = ' '.join(task_words[1:]) if len(task_words) > 1 else "Unassigned"
    
    return {
        'type': 'task',
        'task_name': task_name,
        'assigned_to': assigned_to,
        'status': 'Pending'
    }

def parse_inventory_voice(text):
    """Extract inventory info from voice"""
    words = text.split()
    
    # Extract numbers for quantity and price
    numbers = [w for w in words if w.replace('.', '', 1).isdigit()]
    
    product_words = [w for w in words if w.lower() not in 
                     ['add', 'product', 'quantity', 'price', 'qty'] and not w.isdigit()]
    
    product_name = ' '.join(product_words) if product_words else "Unknown Product"
    quantity = numbers[0] if len(numbers) > 0 else "1"
    price = numbers[1] if len(numbers) > 1 else "0"
    
    return {
        'type': 'inventory',
        'product_name': product_name,
        'quantity': quantity,
        'price': price
    }

def parse_finance_voice(text):
    """Extract finance info from voice"""
    words = text.split()
    
    # Extract numbers for amount
    numbers = [w for w in words if w.replace('.', '', 1).isdigit()]
    
    customer_words = [w for w in words if w.lower() not in 
                      ['add', 'transaction', 'amount', 'sale', 'customer'] and not w.isdigit()]
    
    customer = ' '.join(customer_words) if customer_words else "Unknown"
    amount = numbers[0] if numbers else "0"
    trans_type = "Sale"
    
    return {
        'type': 'finance',
        'customer': customer,
        'amount': amount,
        'trans_type': trans_type
    }

async def save_voice_data(transcribed_text, module_type, spreadsheet_id, update):
    """Save transcribed voice data to Google Sheets"""
    try:
        parsed_data = parse_voice_command(transcribed_text, module_type)
        
        if not parsed_data:
            await update.message.reply_text("❌ Could not parse voice command")
            return
        
        if parsed_data['type'] == 'customer':
            result = add_customer(
                spreadsheet_id,
                parsed_data['name'],
                parsed_data['email'],
                parsed_data['phone'],
                parsed_data['company']
            )
            await update.message.reply_text(f"✅ {result['message']}\n\n📝 Transcribed: {transcribed_text}")
        
        elif parsed_data['type'] == 'task':
            result = add_task(
                spreadsheet_id,
                parsed_data['task_name'],
                parsed_data['assigned_to']
            )
            await update.message.reply_text(f"✅ {result['message']}\n\n📝 Transcribed: {transcribed_text}")
        
        elif parsed_data['type'] == 'inventory':
            result = add_inventory(
                spreadsheet_id,
                parsed_data['product_name'],
                parsed_data['quantity'],
                parsed_data['price']
            )
            await update.message.reply_text(f"✅ {result['message']}\n\n📝 Transcribed: {transcribed_text}")
        
        elif parsed_data['type'] == 'finance':
            result = add_transaction(
                spreadsheet_id,
                parsed_data['customer'],
                parsed_data['amount'],
                parsed_data['trans_type']
            )
            await update.message.reply_text(f"✅ {result['message']}\n\n📝 Transcribed: {transcribed_text}")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error saving data: {str(e)}")