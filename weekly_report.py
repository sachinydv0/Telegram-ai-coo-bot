# weekly_report.py
from google_sheets import get_finance, get_customers, get_tasks, get_inventory, add_report
from datetime import datetime, timedelta

def generate_weekly_report():
    # Simple example summary. Customize as needed.
    finance = get_finance()
    customers = get_customers()
    tasks = get_tasks()
    inventory = get_inventory()

    # Simple aggregates
    total_income = 0
    total_expense = 0
    for f in finance:
        try:
            amt = float(f.get("Amount") or 0)
        except:
            amt = 0
        if (f.get("Type") or "").lower() == "income":
            total_income += amt
        else:
            total_expense += amt

    new_customers = len(customers)
    pending_tasks = sum(1 for t in tasks if (t.get("Status") or "").lower() != "done")

    low_stock = [i for i in inventory if (float(i.get("Quantity") or 0) <= 5)]

    report = (
        f"Weekly report ({datetime.utcnow().date().isoformat()}):\n"
        f"Total Income: ₹{total_income}\n"
        f"Total Expense: ₹{total_expense}\n"
        f"Customers (count): {new_customers}\n"
        f"Pending tasks: {pending_tasks}\n"
        f"Low stock items: {len(low_stock)}\n"
    )

    # Save to Report sheet
    add_report(report)
    return report