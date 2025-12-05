# google_sheets.py
import os
import json
from dotenv import load_dotenv
import gspread
from datetime import datetime

load_dotenv()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

gc = gspread.service_account(filename="service_account.json")

def _open_sheet():
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh

# ---------- CUSTOMER ----------
def add_customer(name, email, phone, company):
    sh = _open_sheet()
    ws = sh.worksheet("Customer")
    now = datetime.utcnow().isoformat()
    ws.append_row([name or "", email or "", phone or "", company or "", now])
    return True

def get_customers():
    sh = _open_sheet()
    ws = sh.worksheet("Customer")
    return ws.get_all_records()

# ---------- TASK ----------
def add_task(task_name, assigned_to="self", status="pending"):
    sh = _open_sheet()
    ws = sh.worksheet("Task")
    now = datetime.utcnow().isoformat()
    ws.append_row([task_name or "", assigned_to or "", status or "", now])
    return True

def get_tasks():
    sh = _open_sheet()
    ws = sh.worksheet("Task")
    return ws.get_all_records()

# ---------- INVENTORY ----------
def add_inventory(product, quantity, price):
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    now = datetime.utcnow().isoformat()
    ws.append_row([product or "", quantity or "", price or "", now])
    return True

def update_inventory(product, quantity, price):
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    records = ws.get_all_records()
    for idx, r in enumerate(records, start=2):  # data starts at row 2
        if str(r.get("Product", "")).strip().lower() == str(product).strip().lower():
            ws.update_cell(idx, 2, quantity)
            ws.update_cell(idx, 3, price)
            return True
    return add_inventory(product, quantity, price)

def get_inventory():
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    return ws.get_all_records()

def low_stock_items(threshold=5):
    items = get_inventory()
    low = []
    for it in items:
        try:
            qty = float(it.get("Quantity") or 0)
        except:
            qty = 0
        if qty <= threshold:
            low.append(it)
    return low

# ---------- FINANCE ----------
def add_finance(customer, amount, ftype, date=None, notes=""):
    sh = _open_sheet()
    ws = sh.worksheet("Finance")
    date = date or datetime.utcnow().date().isoformat()
    ws.append_row([customer or "", amount or "", ftype or "", date, notes])
    return True

def get_finance():
    sh = _open_sheet()
    ws = sh.worksheet("Finance")
    return ws.get_all_records()

# ---------- REPORT ----------
def add_report(text):
    sh = _open_sheet()
    ws = sh.worksheet("Report")
    now = datetime.utcnow().isoformat()
    ws.append_row([now, text])
    return True

# ---------- MEMORY (NEW) ----------
def _get_or_create_memory_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Memory")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Memory", rows=1000, cols=4)
        ws.update("A1:D1", [["UserID", "Timestamp", "Role", "Text"]])
    return ws

def add_memory(user_id, role, text):
    """Store short message history per user."""
    ws = _get_or_create_memory_ws()
    now = datetime.utcnow().isoformat()
    ws.append_row([str(user_id), now, role, text or ""])
    return True

def get_memory(user_id, limit=6):
    """Get last N messages (user+bot) for that user."""
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Memory")
    except gspread.WorksheetNotFound:
        return []
    records = ws.get_all_records()
    user_records = [r for r in records if str(r.get("UserID")) == str(user_id)]
    return user_records[-limit:]

# ---------- INVOICE / BILLING ----------
def _get_or_create_invoice_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Invoice")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Invoice", rows=1000, cols=10)
        ws.update("A1:J1", [[
            "InvoiceID", "Date", "Customer", "ItemsJSON",
            "Subtotal", "TaxRate", "Discount", "GrandTotal",
            "Paid", "Due"
        ]])
    return ws
# INVOICE
def add_invoice(customer, items, subtotal, tax_rate, discount, grand_total, paid, due):
    """
    items = list of dicts:
        [{"product": "...", "quantity": 2, "price": 45000, "total": 90000}, ...]
    """
    ws = _get_or_create_invoice_ws()
    now = datetime.utcnow().isoformat()
    # Simple unique id from timestamp
    invoice_id = f"INV-{now.replace('-', '').replace(':', '').split('.')[0]}"
    items_json = json.dumps(items, ensure_ascii=False)
    ws.append_row([
        invoice_id,
        now,
        customer or "Walk-in Customer",
        items_json,
        subtotal,
        tax_rate,
        discount,
        grand_total,
        paid,
        due,
    ])
    return invoice_id

# ---------- PURCHASE ----------
def _purchase_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Purchase")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Purchase", rows=1000, cols=8)
        ws.update("A1:H1", [[
            "PurchaseID", "Date", "Supplier", "Product",
            "Quantity", "PriceEach", "Total", "Notes"
        ]])
    return ws


def add_purchase(supplier, product, quantity, price_each, notes=""):
    ws = _purchase_ws()
    now = datetime.utcnow().isoformat()
    pid = f"P-{now.replace('-', '').replace(':', '').split('.')[0]}"

    quantity = float(quantity)
    price_each = float(price_each)
    total = quantity * price_each

    ws.append_row([
        pid,
        now,
        supplier or "",
        product,
        quantity,
        price_each,
        total,
        notes
    ])

    return pid, total

# ---------- SALES ----------
def _sales_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Sales")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Sales", rows=1000, cols=9)
        ws.update("A1:I1", [[
            "SaleID", "Date", "Customer", "Product",
            "Quantity", "PriceEach", "Total", "Profit", "Notes"
        ]])
    return ws


def add_sale(customer, product, quantity, selling_price, purchase_price, notes=""):
    ws = _sales_ws()
    now = datetime.utcnow().isoformat()
    sid = f"S-{now.replace('-', '').replace(':', '').split('.')[0]}"

    quantity = float(quantity)
    selling_price = float(selling_price)
    purchase_price = float(purchase_price)

    total = quantity * selling_price
    profit = (selling_price - purchase_price) * quantity

    ws.append_row([
        sid,
        now,
        customer or "",
        product,
        quantity,
        selling_price,
        total,
        profit,
        notes
    ])

    return sid, total, profit

# ---------- INVENTORY AUTO UPDATE ----------
def increase_stock(product, quantity, purchase_price=None):
    """Add stock; update purchase price if provided"""
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    records = ws.get_all_records()

    quantity = float(quantity)

    for i, row in enumerate(records, start=2):
        if row["Product"].strip().lower() == product.strip().lower():
            new_qty = float(row["Quantity"]) + quantity

            ws.update_cell(i, 2, new_qty)

            # update purchase price if given
            if purchase_price is not None:
                ws.update_cell(i, 3, float(purchase_price))

            return True

    # If product not found → add new row
    ws.append_row([product, quantity, purchase_price or 0, datetime.utcnow().isoformat()])
    return True


def decrease_stock(product, quantity):
    """Subtract stock when selling"""
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    records = ws.get_all_records()

    quantity = float(quantity)

    for i, row in enumerate(records, start=2):
        if row["Product"].strip().lower() == product.strip().lower():
            new_qty = float(row["Quantity"]) - quantity
            if new_qty < 0: new_qty = 0
            ws.update_cell(i, 2, new_qty)
            return True

    return False


def get_purchase_price(product):
    """Get last purchase price; needed for profit calc"""
    sh = _open_sheet()
    ws = sh.worksheet("Inventory")
    records = ws.get_all_records()

    for row in records:
        if row["Product"].strip().lower() == product.strip().lower():
            return float(row.get("Price") or 0)

    return 0

# ---------- SMART ANALYTICS ----------
def get_low_stock(threshold=5):
    items = get_inventory()
    low = []
    for it in items:
        try:
            qty = float(it.get("Quantity") or 0)
        except:
            qty = 0
        if qty <= threshold:
            low.append((it.get("Product"), qty))
    return low


def get_top_selling(limit=3):
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Sales")
    except:
        return []

    records = ws.get_all_records()
    sales_count = {}

    for r in records:
        p = r.get("Product")
        q = float(r.get("Quantity") or 0)
        sales_count[p] = sales_count.get(p, 0) + q

    sorted_items = sorted(sales_count.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:limit]


def get_total_profit():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("Sales")
    except:
        return 0

    records = ws.get_all_records()
    total = 0
    for r in records:
        try:
            total += float(r.get("Profit") or 0)
        except:
            pass
    return total


def get_today_summary():
    today = datetime.utcnow().date().isoformat()

    sh = _open_sheet()
    summary = {
        "purchases": 0,
        "sales": 0,
        "profit": 0
    }

    # Purchases
    try:
        ws_p = sh.worksheet("Purchase")
        records = ws_p.get_all_records()
        for r in records:
            if r.get("Date", "").startswith(today):
                summary["purchases"] += float(r.get("Total") or 0)
    except:
        pass

    # Sales
    try:
        ws_s = sh.worksheet("Sales")
        records = ws_s.get_all_records()
        for r in records:
            if r.get("Date", "").startswith(today):
                summary["sales"] += float(r.get("Total") or 0)
                summary["profit"] += float(r.get("Profit") or 0)
    except:
        pass

    return summary

# ---------- CRM ----------
def _crm_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("CRM")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="CRM", rows=2000, cols=9)
        ws.update("A1:I1", [[
            "Customer", "Phone", "Email", "LastVisit",
            "TotalPurchases", "TotalSpent", "TotalProfit",
            "Notes", "Tags"
        ]])
    return ws


def crm_add_or_update(customer, phone="", email="", notes="", tags=""):
    ws = _crm_ws()
    records = ws.get_all_records()

    # If customer exists → update
    for idx, row in enumerate(records, start=2):
        if row["Customer"].strip().lower() == customer.strip().lower():
            ws.update_cell(idx, 2, phone or row["Phone"])
            ws.update_cell(idx, 3, email or row["Email"])
            ws.update_cell(idx, 4, datetime.utcnow().date().isoformat())
            ws.update_cell(idx, 8, (row["Notes"] + " " + notes).strip())
            ws.update_cell(idx, 9, (row["Tags"] + "," + tags).strip())
            return

    # If new customer → add
    ws.append_row([
        customer, phone, email,
        datetime.utcnow().date().isoformat(),
        0, 0, 0, notes, tags
    ])


def crm_update_sales(customer, amount, profit):
    ws = _crm_ws()
    records = ws.get_all_records()

    for idx, row in enumerate(records, start=2):
        if row["Customer"].strip().lower() == customer.strip().lower():
            total_spent = float(row["TotalSpent"] or 0) + amount
            total_profit = float(row["TotalProfit"] or 0) + profit
            total_purchase = float(row["TotalPurchases"] or 0) + 1

            ws.update_cell(idx, 5, total_purchase)
            ws.update_cell(idx, 6, total_spent)
            ws.update_cell(idx, 7, total_profit)
            return True

    return False

# ---------- SERVICE HISTORY ----------
def _service_ws():
    sh = _open_sheet()
    try:
        ws = sh.worksheet("ServiceHistory")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="ServiceHistory", rows=2000, cols=9)
        ws.update("A1:I1", [[
            "ServiceID", "Date", "Customer", "Device",
            "Problem", "Status", "Cost", "Technician", "Notes"
        ]])
    return ws


def add_service(customer, device, problem, status="Pending", cost=0, tech="", notes=""):
    ws = _service_ws()
    now = datetime.utcnow().isoformat()
    sid = f"JOB-{now.replace('-', '').replace(':', '').split('.')[0]}"

    ws.append_row([
        sid, now, customer, device, problem, status,
        cost, tech, notes
    ])

    return sid