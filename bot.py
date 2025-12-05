# bot.py - final multilingual bot
import os
import logging
import subprocess
import tempfile
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
# Voice libs
import speech_recognition as sr
from gtts import gTTS

# Local modules
from ai_agent import ask_ai_agent, parse_ai_response
import google_sheets as gs
from weekly_report import generate_weekly_report

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# -----------------------------
# helper: detect language from text
# -----------------------------
def detect_language(text):
    if not text:
        return "en"
    hindi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    return "hi" if hindi_chars > 0 else "en"

#generate pdf
def generate_invoice_pdf(
    invoice_id, customer, items,
    subtotal, tax_rate, tax_amount,
    discount, grand_total, paid, due,
    pdf_path
):
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Invoice")
    c.setFont("Helvetica", 10)
    y -= 20
    c.drawString(40, y, f"Invoice ID: {invoice_id}")
    y -= 15
    c.drawString(40, y, f"Customer: {customer}")
    y -= 15
    c.drawString(40, y, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

    # Table headers
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Item")
    c.drawString(260, y, "Qty")
    c.drawString(310, y, "Price")
    c.drawString(380, y, "Total")
    y -= 15
    c.setFont("Helvetica", 10)

    for item in items:
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

        c.drawString(40, y, str(item["product"]))
        c.drawRightString(290, y, f"{item['quantity']}")
        c.drawRightString(360, y, f"{item['price']:.2f}")
        c.drawRightString(440, y, f"{item['total']:.2f}")
        y -= 15

    y -= 20
    c.drawRightString(440, y, f"Subtotal: {subtotal:.2f}"); y -= 15
    c.drawRightString(440, y, f"Tax ({tax_rate}%): {tax_amount:.2f}"); y -= 15
    c.drawRightString(440, y, f"Discount: {discount:.2f}"); y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(440, y, f"Grand Total: {grand_total:.2f}"); y -= 15
    c.setFont("Helvetica", 10)
    c.drawRightString(440, y, f"Paid: {paid:.2f}"); y -= 15
    c.drawRightString(440, y, f"Due: {due:.2f}")

    c.showPage()
    c.save()

# helper: save memory and send reply
from typing import Optional

async def reply_with_memory(update: Update, user_id: int, user_text: str, reply_text: str):
    # store both sides in Memory sheet
    gs.add_memory(user_id, "user", user_text)
    gs.add_memory(user_id, "assistant", reply_text)
    return await update.message.reply_text(reply_text)
# -----------------------------
# Menu (Bilingual single-line)
# -----------------------------
def get_main_menu():
    keyboard = [
        ["Customers (ग्राहक)"],
        ["Inventory (स्टॉक)"],
        ["Tasks (कार्य)"],
        ["Finance (वित्त)"],
        ["Reports (रिपोर्ट)"],
        ["🎙 Voice Assistant (वॉइस असिस्टेंट)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_menu():
    return ReplyKeyboardMarkup([["⬅️ Back to Menu (वापस जाएं)"]], resize_keyboard=True)

# -----------------------------
# Command handlers
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm your AI Business Assistant.\nUse /menu to view options.\nYou can also say or type commands like:\nAdd customer Rahul 9876543210\nAdd 10 Dell laptops at 30000\nSend voice message to use voice assistant."
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Main Menu:", reply_markup=get_main_menu())

# -----------------------------
# Menu button handler
# -----------------------------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    # normalize exact left part (English) for matching
    if text.startswith("Customers"):
        keyboard = [["Add Customer (ग्राहक जोड़ें)"], ["View Customers (ग्राहकों को देखें)"], ["⬅️ Back to Menu (वापस जाएं)"]]
        return await update.message.reply_text("Customer options:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    if text.startswith("Inventory"):
        keyboard = [["Add Inventory (स्टॉक जोड़ें)"], ["View Inventory (स्टॉक देखें)"], ["Low Stock (कम स्टॉक)"], ["⬅️ Back to Menu (वापस जाएं)"]]
        return await update.message.reply_text("Inventory options:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    if text.startswith("Tasks"):
        keyboard = [["Add Task (कार्य जोड़ें)"], ["View Tasks (कार्य सूची)"], ["⬅️ Back to Menu (वापस जाएं)"]]
        return await update.message.reply_text("Task options:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    if text.startswith("Finance"):
        keyboard = [["Add Finance (वित्त जोड़ें)"], ["View Finance (वित्त देखें)"], ["⬅️ Back to Menu (वापस जाएं)"]]
        return await update.message.reply_text("Finance options:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    if text.startswith("Reports"):
        report_text = generate_weekly_report()
        return await update.message.reply_text(report_text, reply_markup=get_back_menu())

    if text.startswith("🎙 Voice Assistant"):
        # prompt user to send voice
        return await update.message.reply_text("Send a voice message and I'll respond (Hindi/English supported).", reply_markup=get_back_menu())

    if text.startswith("⬅️ Back to Menu"):
        return await update.message.reply_text("📌 Main Menu", reply_markup=get_main_menu())

    # If none of the above, route to AI handler (text)
    return await handle_message(update, context)

def generate_suggestions():
    suggestions = []

    # Low stock
    low = gs.get_low_stock()
    if low:
        s = "⚠️ Low Stock Items:\n"
        for p, q in low:
            s += f"• {p} — {q} pcs left\n"
        suggestions.append(s)

    # Best selling products
    top = gs.get_top_selling()
    if top:
        s = "🔥 Best Selling Items:\n"
        for p, q in top:
            s += f"• {p}: {q} sold\n"
        suggestions.append(s)

    # Total profit
    profit = gs.get_total_profit()
    if profit > 0:
        suggestions.append(f"💰 Total Profit So Far: ₹{profit:.2f}")

    # Today’s summary
    today = gs.get_today_summary()
    if today["sales"] > 0 or today["purchases"] > 0:
        suggestions.append(
            f"📅 Today’s Summary:\n"
            f"• Purchases: ₹{today['purchases']:.2f}\n"
            f"• Sales: ₹{today['sales']:.2f}\n"
            f"• Profit Today: ₹{today['profit']:.2f}"
        )

    if not suggestions:
        return "Everything looks smooth 👍"

    return "\n\n".join(suggestions)

# -----------------------------
# AI routing (text messages)
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text or ""
    user_id = update.effective_user.id

    # ---- load last few messages from Memory sheet ----
    mem_records = gs.get_memory(user_id, limit=6)
    memory_text = ""
    if mem_records:
        memory_text = "\n".join(f"{m.get('Role')}: {m.get('Text')}" for m in mem_records)

    # ---- call AI with memory ----
    ai_raw = ask_ai_agent(user_text, memory_text)
    ai = parse_ai_response(ai_raw)

    logging.info("AI RAW: %s", ai_raw)
    logging.info("AI PARSED: %s", ai)

    intent = ai.get("intent")
    data = ai.get("data", {})
    reply_message = ai.get("reply", "")

    # ---------- CUSTOMER ----------
    if intent == "add_customer":
        gs.add_customer(
            data.get("Name") or data.get("name"),
            data.get("Email") or data.get("email", ""),
            data.get("Phone") or data.get("phone", ""),
            data.get("Company") or data.get("company", "")
        )
        reply_message = reply_message or "Customer added."
        return await reply_with_memory(update, user_id, user_text, reply_message)

    if intent == "get_customers":
        customers = gs.get_customers()
        if not customers:
            reply_message = "No customers found."
            return await reply_with_memory(update, user_id, user_text, reply_message)

        result = ""
        for c in customers:
            name = c.get("Name") or c.get("name") or ""
            email = c.get("Email") or c.get("email") or ""
            phone = c.get("Phone") or c.get("phone") or ""
            company = c.get("Company") or c.get("company") or ""
            result += f"{name} - {phone} - {email} - {company}\n"

        return await reply_with_memory(update, user_id, user_text, result)

    # ---------- TASK ----------
    if intent == "add_task":
        gs.add_task(
            data.get("Task Name") or data.get("task_name") or data.get("task"),
            data.get("Assigned To") or data.get("assigned_to") or "self",
            data.get("Status") or data.get("status") or "pending"
        )
        reply_message = reply_message or "Task added."
        return await reply_with_memory(update, user_id, user_text, reply_message)

    if intent == "get_tasks":
        tasks = gs.get_tasks()
        if not tasks:
            reply_message = "No tasks found."
            return await reply_with_memory(update, user_id, user_text, reply_message)

        result = ""
        for t in tasks:
            task_name = t.get("Task Name") or t.get("task_name") or t.get("Task") or ""
            assigned = t.get("Assigned To") or t.get("assigned_to") or ""
            status = t.get("Status") or t.get("status") or ""
            result += f"{task_name} | {assigned} | {status}\n"

        return await reply_with_memory(update, user_id, user_text, result)

    # ---------- INVENTORY ----------
    if intent == "add_inventory":
        product = (
            data.get("Product") or data.get("product") or
            data.get("product_name") or data.get("item") or
            data.get("name")
        )
        quantity = (
            data.get("Quantity") or data.get("quantity") or
            data.get("qty") or data.get("count") or
            data.get("amount")
        )
        price = (
            data.get("Price") or data.get("price") or
            data.get("rate") or data.get("cost")
        )

        gs.add_inventory(product, quantity, price)
        reply_message = reply_message or "Inventory added."
        return await reply_with_memory(update, user_id, user_text, reply_message)

    if intent == "update_inventory":
        product = (
            data.get("Product") or data.get("product") or
            data.get("product_name") or data.get("item") or
            data.get("name")
        )
        quantity = (
            data.get("Quantity") or data.get("quantity") or
            data.get("qty") or data.get("count") or
            data.get("amount")
        )
        price = (
            data.get("Price") or data.get("price") or
            data.get("rate") or data.get("cost")
        )

        gs.update_inventory(product, quantity, price)
        reply_message = reply_message or "Inventory updated."
        return await reply_with_memory(update, user_id, user_text, reply_message)

    if intent == "get_inventory":
        items = gs.get_inventory()
        if not items:
            reply_message = "Inventory is empty."
            return await reply_with_memory(update, user_id, user_text, reply_message)

        result = ""
        for i in items:
            product = i.get("Product") or ""
            qty = i.get("Quantity") or ""
            price = i.get("Price") or ""
            result += f"{product} — {qty} pcs — ₹{price}\n"

        return await reply_with_memory(update, user_id, user_text, result)

    if intent == "low_stock_check":
        low = gs.low_stock_items()
        if not low:
            reply_message = "All stock levels are OK 👍"
            return await reply_with_memory(update, user_id, user_text, reply_message)

        result = "⚠️ Low Stock:\n"
        for i in low:
            product = i.get("Product") or ""
            qty = i.get("Quantity") or ""
            result += f"{product}: {qty} pcs left\n"

        return await reply_with_memory(update, user_id, user_text, result)
    

    # ---------- PURCHASE ENTRY ----------
    if intent == "purchase_entry":
        supplier = data.get("supplier") or "Unknown Supplier"
        product = data.get("product")
        qty = data.get("quantity")
        price = data.get("price_each")

        # Increase stock
        gs.increase_stock(product, qty, price)

        # Add purchase record
        pid, total = gs.add_purchase(supplier, product, qty, price)

        reply = reply_message or f"✔ Purchased {qty} {product} from {supplier}. Total ₹{total}."

        gs.add_memory(user_id, "user", user_text)
        gs.add_memory(user_id, "assistant", reply)
        return await update.message.reply_text(reply)
    
    suggest = generate_suggestions()
    await update.message.reply_text("🔎 Suggestions:\n" + suggest)
    
    # ---------- SALES ENTRY ----------
    if intent == "sales_entry":
        customer = data.get("customer") or "Walk-in Customer"
        product = data.get("product")
        qty = data.get("quantity")
        selling_price = data.get("selling_price")

        purchase_price = gs.get_purchase_price(product)

        # Decrease stock
        gs.decrease_stock(product, qty)

        # Add sale record
        sid, total, profit = gs.add_sale(customer, product, qty, selling_price, purchase_price)

        reply = reply_message or f"✔ Sold {qty} {product} to {customer}. Profit ₹{profit}."

        gs.add_memory(user_id, "user", user_text)
        gs.add_memory(user_id, "assistant", reply)
        return await update.message.reply_text(reply)
    suggest = generate_suggestions()
    await update.message.reply_text("🔎 Suggestions:\n" + suggest)
    
    # ---------- MIXED TRANSACTION ----------
    if intent == "mixed_transaction":
        purchases = data.get("purchases", [])
        sales = data.get("sales", [])
        reply_lines = []

        # Purchases
        for p in purchases:
            supplier = p.get("supplier") or "Unknown Supplier"
            product = p.get("product")
            qty = p.get("quantity")
            price = p.get("price_each")

            gs.increase_stock(product, qty, price)
            pid, total = gs.add_purchase(supplier, product, qty, price)
            reply_lines.append(f"✔ Purchased {qty} {product} (₹{total}).")

        # Sales
        for s in sales:
            customer = s.get("customer") or "Walk-in Customer"
            product = s.get("product")
            qty = s.get("quantity")
            selling_price = s.get("selling_price")

            purchase_price = gs.get_purchase_price(product)

            gs.decrease_stock(product, qty)
            sid, total, profit = gs.add_sale(customer, product, qty, selling_price, purchase_price)
            reply_lines.append(f"✔ Sold {qty} {product}. Profit ₹{profit}.")

        final_reply = "\n".join(reply_lines)

        gs.add_memory(user_id, "user", user_text)
        gs.add_memory(user_id, "assistant", final_reply)
        return await update.message.reply_text(final_reply)
    suggest = generate_suggestions()
    await update.message.reply_text("🔎 Suggestions:\n" + suggest)

    # ---------- FINANCE ----------
    if intent == "add_finance":
        gs.add_finance(
            data.get("Customer") or data.get("customer"),
            data.get("Amount") or data.get("amount"),
            data.get("Type") or data.get("type"),
            data.get("Date") or data.get("date"),
            data.get("Notes") or data.get("notes", "")
        )
        reply_message = reply_message or "Finance record added."
        return await reply_with_memory(update, user_id, user_text, reply_message)

    if intent == "get_finance":
        finance = gs.get_finance()
        if not finance:
            reply_message = "No finance records found."
            return await reply_with_memory(update, user_id, user_text, reply_message)

        result = ""
        for f in finance:
            customer = f.get("Customer") or ""
            amount = f.get("Amount") or ""
            ftype = f.get("Type") or ""
            date = f.get("Date") or ""
            result += f"{customer} - ₹{amount} - {ftype} - {date}\n"

        return await reply_with_memory(update, user_id, user_text, result)
    
    # ---------- BILLING / INVOICE ----------
    if intent == "create_invoice":
        customer = data.get("Customer") or data.get("customer") or "Walk-in Customer"
        items = data.get("items") or []
        discount = float(data.get("discount") or 0)
        tax_rate = float(data.get("tax_rate") or 0)
        paid = float(data.get("paid") or 0)

        normalized_items = []
        subtotal = 0.0

        for item in items:
            product = (
                item.get("product") or item.get("Product") or
                item.get("name") or "Item"
            )
            try:
                qty = float(item.get("quantity") or item.get("Quantity") or 1)
            except:
                qty = 1
            try:
                price = float(item.get("price") or item.get("Price") or 0)
            except:
                price = 0

            line_total = qty * price
            subtotal += line_total

            normalized_items.append({
                "product": product,
                "quantity": qty,
                "price": price,
                "total": line_total,
            })

        tax_amount = subtotal * tax_rate / 100
        grand_total = subtotal + tax_amount - discount
        due = grand_total - paid

        invoice_id = gs.add_invoice(
            customer=customer,
            items=normalized_items,
            subtotal=subtotal,
            tax_rate=tax_rate,
            discount=discount,
            grand_total=grand_total,
            paid=paid,
            due=due,
        )

        pdf_path = f"invoice_{invoice_id}.pdf"
        generate_invoice_pdf(
            invoice_id, customer, normalized_items,
            subtotal, tax_rate, tax_amount,
            discount, grand_total, paid, due,
            pdf_path
        )

        summary = reply_message or f"Invoice {invoice_id} created for {customer} (₹{grand_total:.2f})."

        # save memory
        gs.add_memory(user_id, "user", user_text)
        gs.add_memory(user_id, "assistant", summary)

        # send text + PDF
        await update.message.reply_text(summary)
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(f, filename=os.path.basename(pdf_path))
        return
    

    if intent == "get_customer_profile":
        customer = data.get("customer")
        ws = gs._crm_ws()
        records = ws.get_all_records()

        for r in records:
            if r["Customer"].lower() == customer.lower():
                reply = (
                    f"📇 Customer Profile\n"
                    f"Name: {r['Customer']}\n"
                    f"Phone: {r['Phone']}\n"
                    f"Email: {r['Email']}\n"
                    f"Last Visit: {r['LastVisit']}\n"
                    f"Total Purchases: {r['TotalPurchases']}\n"
                    f"Total Spent: ₹{r['TotalSpent']}\n"
                    f"Total Profit: ₹{r['TotalProfit']}\n"
                    f"Notes: {r['Notes']}\n"
                    f"Tags: {r['Tags']}\n"
                )
                return await update.message.reply_text(reply)

        return await update.message.reply_text("Customer not found.")
    
    if intent == "add_service":
        customer = data.get("customer")
        device = data.get("device")
        problem = data.get("problem")
        tech = data.get("technician") or ""

        sid = gs.add_service(customer, device, problem, "Pending", 0, tech, "")

        reply = f"🛠 Service Job Created\nID: {sid}\nCustomer: {customer}\nDevice: {device}\nProblem: {problem}"

        return await update.message.reply_text(reply)    


    if intent == "get_service_status":
        job_id = data.get("service_id")
        ws = gs._service_ws()
        records = ws.get_all_records()

        for r in records:
            if r["ServiceID"] == job_id:
                reply = (
                    f"📝 Service Status\n"
                    f"ID: {job_id}\n"
                    f"Customer: {r['Customer']}\n"
                    f"Device: {r['Device']}\n"
                    f"Problem: {r['Problem']}\n"
                    f"Status: {r['Status']}\n"
                    f"Technician: {r['Technician']}\n"
                    f"Cost: ₹{r['Cost']}\n"
                )
                return await update.message.reply_text(reply)

        return await update.message.reply_text("No such job found.")
    # ---------- REPORT ----------
    if intent == "weekly_report":
        report = generate_weekly_report()
        return await reply_with_memory(update, user_id, user_text, report)

    # ---------- GENERAL CHAT / FALLBACK ----------
    if ai.get("voice_reply", False):
        lang = detect_language(reply_message)
        mp3 = "reply_text.mp3"
        tts = gTTS(text=reply_message, lang=lang)
        tts.save(mp3)
        with open(mp3, "rb") as f:
            await update.message.reply_audio(f)
            

    if intent == "suggestions":
       reply = generate_suggestions()
    return await update.message.reply_text("🔍 Business Insights:\n" + reply)

    # store memory even for general chat
    return await reply_with_memory(update, user_id, user_text, reply_message or "Okay.")

# -----------------------------
# VOICE HANDLER (final)
# -----------------------------
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if not voice:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        wav_path = os.path.join(tmpdir, "voice.wav")
        mp3_path = os.path.join(tmpdir, "reply.mp3")

        file = await voice.get_file()
        await file.download_to_drive(ogg_path)

        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"  # adjust if different

        try:
            subprocess.run([ffmpeg_path, "-y", "-i", ogg_path, wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logging.error("FFmpeg conversion error: %s", e)
            return await update.message.reply_text("⚠️ Audio conversion failed.")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        # multi-language recognition
        def recognize_multilang():
            results = []
            for lang in ["hi-IN", "en-IN"]:
                try:
                    txt = recognizer.recognize_google(audio_data, language=lang)
                    results.append((txt, len(txt), lang))
                except:
                    pass
            if not results:
                return "", "en-IN"
            best = max(results, key=lambda x: x[1])
            return best[0], best[2]

        text, detected_lang = recognize_multilang()
        if not text:
            return await update.message.reply_text("⚠️ I couldn't understand your voice. Please try again.")

        await update.message.reply_text(f"🗣 You said: {text}")

        user_id = update.effective_user.id

        ai_raw = ask_ai_agent(text, "")
        ai = parse_ai_response(ai_raw)
        reply_message = ai.get("reply", "ठीक है।")

# save memory for voice conversation
        gs.add_memory(user_id, "user", text)
        gs.add_memory(user_id, "assistant", reply_message)

        await update.message.reply_text(reply_message)

        # voice reply if requested
        if ai.get("voice_reply", False):
            lang_code = "hi" if detected_lang.startswith("hi") else "en"
            tts = gTTS(text=reply_message, lang=lang_code)
            tts.save(mp3_path)
            with open(mp3_path, "rb") as audio_file:
                await update.message.reply_audio(audio=audio_file)

# -----------------------------
# Run the bot
# -----------------------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))

    # voice must come before text handler
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("Bot Running with Multilingual Menu + Voice Enabled...")
    app.run_polling()

if __name__ == "__main__":
    main()