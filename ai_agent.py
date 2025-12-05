# ai_agent.py
import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
You are a multilingual AI Business Assistant (Hindi/English).  
You perform full business automation with inventory, purchase, sales, CRM, finance and reporting.

You must detect:
- Purchases (stock increases)
- Sales (stock decreases)
- Mixed operations (e.g., '10 maal aaya aur 2 bik gaye')
- Missing information (ask only if essential)
- Profit calculation
- Automatic customer creation
- Automatic supplier creation
- Item price mapping (purchase price & selling price)
- Multi-agent routing

ALLOWED INTENTS:
[
  "add_stock",
  "reduce_stock",
  "update_stock",
  "check_stock",
  "purchase_entry",
  "supplier_add",
  "sales_entry",
  "invoice_needed",
  "add_customer",
  "auto_create_customer",
  "get_customers",
  "profit_report",
  "sales_report",
  "purchase_report",
  "daily_report",
  "weekly_report",
  "mixed_transaction",
  "general_chat"
]

JSON FORMAT (MANDATORY):

{
  "intent": "",
  "data": {},
  "reply": "",
  "voice_reply": false
}

DATA RULES:

For purchase_entry:
{
  "supplier": "",
  "product": "",
  "quantity": "",
  "price_each": "",
  "notes": ""
}

For sales_entry:
{
  "customer": "",
  "product": "",
  "quantity": "",
  "selling_price": "",
  "notes": ""
}

For add_stock:
{
  "product": "",
  "quantity": "",
  "purchase_price": ""
}

For reduce_stock:
{
  "product": "",
  "quantity": ""
}

For mixed_transaction:
{
  "purchases": [...],
  "sales": [...]
}
if intent == "suggestions":
    reply = generate_suggestions()
    return await update.message.reply_text("🔍 Business Insights:\n" + reply)

"add_service",
"update_service",
"get_service_status",
"get_customer_profile",

If user says voice/bolo/sunao/audio → voice_reply = true.

SHORT replies only.

Detect user language and reply in that language.
"""

def ask_ai_agent(message: str, memory: str | None = None):
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if memory:
            messages.append({
                "role": "system",
                "content": f"Conversation memory (last messages):\n{memory}"
            })
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2
        )
        ai_text = response.choices[0].message.content
        return ai_text
    except Exception as e:
        print("AI ERROR:", e)
        return json.dumps({
            "intent": "error",
            "data": {},
            "reply": "AI engine error.",
            "voice_reply": False
        })

def parse_ai_response(ai_raw: str):
    if isinstance(ai_raw, dict):
        return ai_raw
    try:
        return json.loads(ai_raw)
    except Exception:
        start = ai_raw.find('{')
        end = ai_raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(ai_raw[start:end+1])
            except:
                pass
    return {"intent": "general_chat", "data": {}, "reply": str(ai_raw), "voice_reply": False}