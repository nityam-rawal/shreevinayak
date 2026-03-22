import csv
import html
import json
import os
import re
import secrets
import hashlib
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from wsgiref.simple_server import make_server


BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "shop_manager.db"
EXPORT_DIR = BASE_DIR / "exports"
BACKUP_DIR = BASE_DIR / "backups"
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8000"))
SHOP_NAME = "Apni Dukaan"
SESSIONS = {}

TEXT = {
    "en": {
        "tagline": "Phone-Friendly Indian Shop Manager",
        "quick_entry": "Quick Entry",
        "quick_help": "Type or speak: sold 2 sugar to Ramesh 120 credit | bought 10 rice from Gupta 45 paid 300 | expense electricity 800",
        "inventory": "Inventory",
        "add_item": "Add Item",
        "purchase": "Purchase / Restock",
        "sale": "Sales Invoice",
        "expense": "Expense",
        "dashboard": "Daily Dashboard",
        "ledger": "Ledgers",
        "recent_sales": "Recent Sales",
        "low_stock": "Low Stock",
        "open_phone": "Open on phone",
        "voice": "Voice Input",
        "language": "Hindi / English",
        "save": "Save",
    },
    "hi": {
        "tagline": "Phone se chalne wala Dukaan Manager",
        "quick_entry": "Tez Entry",
        "quick_help": "Likho ya bolo: sold 2 sugar to Ramesh 120 credit | bought 10 rice from Gupta 45 paid 300 | expense bijli 800",
        "inventory": "Inventory",
        "add_item": "Naya Item",
        "purchase": "Kharid / Restock",
        "sale": "Sale Invoice",
        "expense": "Kharcha",
        "dashboard": "Aaj ka Hisaab",
        "ledger": "Udhaar Ledger",
        "recent_sales": "Haal ki Sales",
        "low_stock": "Kam Stock",
        "open_phone": "Phone par kholo",
        "voice": "Voice Input",
        "language": "Hindi / English",
        "save": "Save",
    },
}


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_string():
    return datetime.now().strftime("%Y-%m-%d")


def safe_float(value, default=0.0):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def safe_text(value, default=""):
    return (value or default).strip()


def hash_pin(pin):
    return hashlib.sha256(safe_text(pin).encode("utf-8")).hexdigest()


def h(value):
    return html.escape(str(value), quote=True)


def local_ip():
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class ShopManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.setup_db()

    def setup_db(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                stock_qty REAL NOT NULL DEFAULT 0,
                buy_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                low_stock_limit REAL NOT NULL DEFAULT 5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                phone TEXT DEFAULT '',
                balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                phone TEXT DEFAULT '',
                balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_no TEXT NOT NULL UNIQUE,
                vendor_id INTEGER,
                item_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                rate REAL NOT NULL,
                total REAL NOT NULL,
                paid REAL NOT NULL,
                due REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY(vendor_id) REFERENCES vendors(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL UNIQUE,
                customer_id INTEGER,
                sale_date TEXT NOT NULL,
                subtotal REAL NOT NULL,
                discount REAL NOT NULL,
                grand_total REAL NOT NULL,
                paid REAL NOT NULL,
                due REAL NOT NULL,
                payment_mode TEXT NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                qty REAL NOT NULL,
                rate REAL NOT NULL,
                buy_price REAL NOT NULL,
                line_total REAL NOT NULL,
                profit REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY(item_id) REFERENCES items(id)
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT DEFAULT ''
            );
            """
        )
        self.set_setting("shop_name", SHOP_NAME, if_missing=True)
        self.set_setting("telegram_enabled", "0", if_missing=True)
        self.set_setting("app_pin", hash_pin("1234"), if_missing=True)
        self.set_setting("telegram_chat_id", "", if_missing=True)
        self.set_setting("telegram_last_update_id", "0", if_missing=True)
        self.conn.commit()

    def set_setting(self, key, value, if_missing=False):
        if if_missing:
            self.conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))
        else:
            self.conn.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        self.conn.commit()

    def get_setting(self, key, default=""):
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def shop_name(self):
        return self.get_setting("shop_name", SHOP_NAME)

    def verify_pin(self, pin):
        stored = self.get_setting("app_pin", hash_pin("1234"))
        candidate = safe_text(pin)
        if stored == candidate:
            self.set_setting("app_pin", hash_pin(candidate))
            return True
        return hash_pin(candidate) == stored

    def update_settings(self, form):
        shop_name = safe_text(form.get("shop_name"))
        app_pin = safe_text(form.get("app_pin"))
        telegram_enabled = "1" if safe_text(form.get("telegram_enabled")).lower() in {"1", "y", "yes", "on", "true"} else "0"
        telegram_chat_id = safe_text(form.get("telegram_chat_id"))
        if shop_name:
            self.set_setting("shop_name", shop_name)
        if app_pin:
            self.set_setting("app_pin", hash_pin(app_pin))
        self.set_setting("telegram_enabled", telegram_enabled)
        self.set_setting("telegram_chat_id", telegram_chat_id)
        return True, "Settings updated."

    def next_invoice_no(self):
        count = self.conn.execute("SELECT COUNT(*) AS c FROM sales").fetchone()["c"] + 1
        return f"INV-{datetime.now().strftime('%Y%m%d')}-{count:03d}"

    def next_purchase_bill_no(self):
        count = self.conn.execute("SELECT COUNT(*) AS c FROM purchases").fetchone()["c"] + 1
        return f"PUR-{datetime.now().strftime('%Y%m%d')}-{count:03d}"

    def find_item(self, name):
        return self.conn.execute("SELECT * FROM items WHERE lower(name)=lower(?)", (safe_text(name),)).fetchone()

    def get_or_create_vendor(self, name, phone=""):
        name = safe_text(name)
        row = self.conn.execute("SELECT * FROM vendors WHERE lower(name)=lower(?)", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO vendors(name, phone, balance, created_at) VALUES(?, ?, 0, ?)",
            (name, safe_text(phone), now_string()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_or_create_customer(self, name, phone=""):
        name = safe_text(name)
        row = self.conn.execute("SELECT * FROM customers WHERE lower(name)=lower(?)", (name,)).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO customers(name, phone, balance, created_at) VALUES(?, ?, 0, ?)",
            (name, safe_text(phone), now_string()),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_item_record(self, form):
        name = safe_text(form.get("name"))
        if not name:
            return False, "Item name required."
        if self.find_item(name):
            return False, "Item already exists."
        category = safe_text(form.get("category"), "general")
        unit = safe_text(form.get("unit"), "pcs")
        qty = safe_float(form.get("qty"), 0)
        buy_price = safe_float(form.get("buy_price"), 0)
        sell_price = safe_float(form.get("sell_price"), 0)
        low_stock = safe_float(form.get("low_stock_limit"), 5)
        self.conn.execute(
            """
            INSERT INTO items(name, category, unit, stock_qty, buy_price, sell_price, low_stock_limit, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, category, unit, qty, buy_price, sell_price, low_stock, now_string(), now_string()),
        )
        self.conn.commit()
        return True, f"{name} added."

    def update_item_record(self, item_id, form):
        self.conn.execute(
            """
            UPDATE items
            SET category=?, unit=?, buy_price=?, sell_price=?, low_stock_limit=?, updated_at=?
            WHERE id=?
            """,
            (
                safe_text(form.get("category"), "general"),
                safe_text(form.get("unit"), "pcs"),
                safe_float(form.get("buy_price"), 0),
                safe_float(form.get("sell_price"), 0),
                safe_float(form.get("low_stock_limit"), 5),
                now_string(),
                item_id,
            ),
        )
        self.conn.commit()
        return True, "Item updated."

    def delete_item_record(self, item_id):
        sales_count = self.conn.execute("SELECT COUNT(*) c FROM sale_items WHERE item_id = ?", (item_id,)).fetchone()["c"]
        purchase_count = self.conn.execute("SELECT COUNT(*) c FROM purchases WHERE item_id = ?", (item_id,)).fetchone()["c"]
        if sales_count or purchase_count:
            return False, "Used item delete nahi kar sakte. Stock adjust ya rename use kijiye."
        self.conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.conn.commit()
        return True, "Item deleted."

    def adjust_stock_record(self, form):
        item = self.find_item(form.get("item_name"))
        if not item:
            return False, "Item not found."
        qty = safe_float(form.get("qty"), 0)
        adjustment_type = safe_text(form.get("adjustment_type"), "set")
        if adjustment_type == "add":
            new_qty = item["stock_qty"] + qty
        elif adjustment_type == "remove":
            new_qty = item["stock_qty"] - qty
        else:
            new_qty = qty
        if new_qty < 0:
            return False, "Stock negative nahi ho sakta."
        self.conn.execute(
            "UPDATE items SET stock_qty = ?, updated_at = ? WHERE id = ?",
            (new_qty, now_string(), item["id"]),
        )
        self.conn.commit()
        return True, f"Stock updated for {item['name']}"

    def purchase_item_record(self, form):
        item = self.find_item(form.get("item_name"))
        if not item:
            return False, "Item not found."
        qty = safe_float(form.get("qty"), 0)
        rate = safe_float(form.get("rate"), 0)
        paid = safe_float(form.get("paid"), qty * rate)
        total = round(qty * rate, 2)
        if qty <= 0 or rate <= 0:
            return False, "Qty and rate must be positive."
        if paid > total:
            return False, "Paid cannot be greater than total."
        vendor_name = safe_text(form.get("vendor_name"))
        vendor_id = self.get_or_create_vendor(vendor_name) if vendor_name else None
        due = round(total - paid, 2)
        bill_no = self.next_purchase_bill_no()
        note = safe_text(form.get("note"))
        self.conn.execute(
            "UPDATE items SET stock_qty = stock_qty + ?, buy_price = ?, updated_at = ? WHERE id = ?",
            (qty, rate, now_string(), item["id"]),
        )
        self.conn.execute(
            """
            INSERT INTO purchases(bill_no, vendor_id, item_id, qty, rate, total, paid, due, purchase_date, note)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bill_no, vendor_id, item["id"], qty, rate, total, paid, due, today_string(), note),
        )
        if vendor_id and due > 0:
            self.conn.execute("UPDATE vendors SET balance = balance + ? WHERE id = ?", (due, vendor_id))
        self.conn.commit()
        return True, f"Purchase saved: {bill_no}"

    def create_sale_record(self, form):
        raw_items = safe_text(form.get("items"))
        sale_lines = []
        for part in raw_items.splitlines():
            bits = [piece.strip() for piece in part.split(",")]
            if len(bits) < 3 or not bits[0]:
                continue
            item = self.find_item(bits[0])
            if not item:
                return False, f"Item not found: {bits[0]}"
            qty = safe_float(bits[1], 0)
            rate = safe_float(bits[2], item["sell_price"])
            if qty <= 0:
                continue
            if qty > item["stock_qty"]:
                return False, f"Stock low for {item['name']}"
            line_total = round(qty * rate, 2)
            sale_lines.append(
                {
                    "item": item,
                    "qty": qty,
                    "rate": rate,
                    "line_total": line_total,
                    "profit": round((rate - item["buy_price"]) * qty, 2),
                }
            )
        if not sale_lines:
            return False, "At least one valid sale line is required."
        subtotal = round(sum(line["line_total"] for line in sale_lines), 2)
        discount = safe_float(form.get("discount"), 0)
        grand_total = round(max(subtotal - discount, 0), 2)
        payment_mode = safe_text(form.get("payment_mode"), "cash")
        paid = safe_float(form.get("paid"), 0 if payment_mode == "credit" else grand_total)
        if paid > grand_total:
            return False, "Paid cannot be greater than total."
        due = round(grand_total - paid, 2)
        customer_name = safe_text(form.get("customer_name"))
        customer_phone = safe_text(form.get("customer_phone"))
        customer_id = self.get_or_create_customer(customer_name, customer_phone) if customer_name else None
        invoice_no = self.next_invoice_no()
        cur = self.conn.execute(
            """
            INSERT INTO sales(invoice_no, customer_id, sale_date, subtotal, discount, grand_total, paid, due, payment_mode, note)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_no,
                customer_id,
                today_string(),
                subtotal,
                discount,
                grand_total,
                paid,
                due,
                payment_mode,
                safe_text(form.get("note")),
            ),
        )
        sale_id = cur.lastrowid
        for line in sale_lines:
            item = line["item"]
            self.conn.execute(
                """
                INSERT INTO sale_items(sale_id, item_id, item_name, qty, rate, buy_price, line_total, profit)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    item["id"],
                    item["name"],
                    line["qty"],
                    line["rate"],
                    item["buy_price"],
                    line["line_total"],
                    line["profit"],
                ),
            )
            self.conn.execute(
                "UPDATE items SET stock_qty = stock_qty - ?, updated_at = ? WHERE id = ?",
                (line["qty"], now_string(), item["id"]),
            )
        if customer_id and due > 0:
            self.conn.execute("UPDATE customers SET balance = balance + ? WHERE id = ?", (due, customer_id))
        self.conn.commit()
        self.maybe_send_telegram_alert(f"{self.shop_name()}\nSale {invoice_no}\nTotal Rs {grand_total:.2f}\nDue Rs {due:.2f}")
        return True, f"Invoice created: {invoice_no}"

    def add_expense_record(self, form):
        category = safe_text(form.get("category"))
        amount = safe_float(form.get("amount"), 0)
        if not category or amount <= 0:
            return False, "Expense category and amount required."
        self.conn.execute(
            "INSERT INTO expenses(expense_date, category, amount, note) VALUES(?, ?, ?, ?)",
            (today_string(), category, amount, safe_text(form.get("note"))),
        )
        self.conn.commit()
        return True, f"Expense added: {category}"

    def delete_expense_record(self, expense_id):
        self.conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self.conn.commit()
        return True, "Expense deleted."

    def receive_customer_payment(self, form):
        name = safe_text(form.get("customer_name"))
        amount = safe_float(form.get("amount"), 0)
        row = self.conn.execute("SELECT * FROM customers WHERE lower(name)=lower(?)", (name,)).fetchone()
        if not row:
            return False, "Customer not found."
        if amount <= 0 or amount > row["balance"]:
            return False, "Invalid customer payment amount."
        self.conn.execute("UPDATE customers SET balance = balance - ? WHERE id = ?", (amount, row["id"]))
        self.conn.commit()
        return True, f"Customer payment received from {name}"

    def pay_vendor_due(self, form):
        name = safe_text(form.get("vendor_name"))
        amount = safe_float(form.get("amount"), 0)
        row = self.conn.execute("SELECT * FROM vendors WHERE lower(name)=lower(?)", (name,)).fetchone()
        if not row:
            return False, "Vendor not found."
        if amount <= 0 or amount > row["balance"]:
            return False, "Invalid vendor payment amount."
        self.conn.execute("UPDATE vendors SET balance = balance - ? WHERE id = ?", (amount, row["id"]))
        self.conn.commit()
        return True, f"Vendor payment done for {name}"

    def quick_entry(self, text):
        line = safe_text(text).lower()
        replacements = {
            "becha": "sold",
            "bikri": "sold",
            "diya": "sold",
            "udhar": "credit",
            "udhaar": "credit",
            "kharida": "bought",
            "liya": "bought",
            "kharcha": "expense",
            "bijli bill": "expense bijli",
            "aaj": "",
            "rupaye": "",
            "rupees": "",
            "rs.": "",
            "rs": "",
        }
        for old, new in replacements.items():
            line = line.replace(old, new)
        line = " ".join(line.split())
        if not line:
            return False, "Quick entry text required."
        sale_match = re.search(
            r"(sold|sale)\s+(\d+(?:\.\d+)?)\s+([a-z0-9 ]+?)(?:\s+to\s+([a-z0-9 ]+?))?(?:\s+(\d+(?:\.\d+)?))?(?:\s+(cash|upi|card|credit))?$",
            line,
        )
        if sale_match:
            qty = sale_match.group(2)
            item_name = sale_match.group(3).strip()
            customer = safe_text(sale_match.group(4))
            rate = sale_match.group(5)
            mode = safe_text(sale_match.group(6), "credit" if "credit" in line or "udhaar" in line else "cash")
            item = self.find_item(item_name)
            if not item:
                return False, f"Item not found: {item_name}"
            rate_value = safe_float(rate, item["sell_price"])
            paid_value = 0 if mode == "credit" else round(safe_float(qty) * rate_value, 2)
            return self.create_sale_record(
                {
                    "customer_name": customer,
                    "items": f"{item['name']},{qty},{rate_value}",
                    "payment_mode": mode,
                    "paid": paid_value,
                    "discount": 0,
                }
            )

        purchase_match = re.search(
            r"(bought|buy|purchase)\s+(\d+(?:\.\d+)?)\s+([a-z0-9 ]+?)(?:\s+from\s+([a-z0-9 ]+?))?\s+(\d+(?:\.\d+)?)(?:\s+paid\s+(\d+(?:\.\d+)?))?$",
            line,
        )
        if purchase_match:
            qty = purchase_match.group(2)
            item_name = purchase_match.group(3).strip()
            vendor_name = safe_text(purchase_match.group(4))
            rate = purchase_match.group(5)
            paid = purchase_match.group(6)
            return self.purchase_item_record(
                {
                    "item_name": item_name,
                    "vendor_name": vendor_name,
                    "qty": qty,
                    "rate": rate,
                    "paid": paid if paid else round(safe_float(qty) * safe_float(rate), 2),
                }
            )

        expense_match = re.search(r"(expense)\s+([a-z0-9 ]+)\s+(\d+(?:\.\d+)?)$", line)
        if expense_match:
            return self.add_expense_record({"category": expense_match.group(2).strip(), "amount": expense_match.group(3)})

        return False, "Quick entry not understood. Use simple format shown on screen."

    def dashboard_data(self):
        today = today_string()
        sales = self.conn.execute(
            "SELECT COALESCE(SUM(grand_total), 0) total, COALESCE(SUM(paid), 0) paid, COALESCE(SUM(due), 0) due FROM sales WHERE sale_date = ?",
            (today,),
        ).fetchone()
        expenses = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) total FROM expenses WHERE expense_date = ?",
            (today,),
        ).fetchone()["total"]
        purchases = self.conn.execute(
            "SELECT COALESCE(SUM(total), 0) total FROM purchases WHERE purchase_date = ?",
            (today,),
        ).fetchone()["total"]
        profit = self.conn.execute(
            """
            SELECT COALESCE(SUM(si.profit), 0) total
            FROM sale_items si JOIN sales s ON s.id = si.sale_id
            WHERE s.sale_date = ?
            """,
            (today,),
        ).fetchone()["total"]
        stock_value = self.conn.execute(
            "SELECT COALESCE(SUM(stock_qty * buy_price), 0) total FROM items"
        ).fetchone()["total"]
        return {
            "sales": sales["total"],
            "cash": sales["paid"],
            "due": sales["due"],
            "expenses": expenses,
            "purchases": purchases,
            "profit": profit,
            "stock_value": stock_value,
        }

    def inventory_rows(self):
        return self.conn.execute("SELECT * FROM items ORDER BY name COLLATE NOCASE").fetchall()

    def low_stock_rows(self):
        return self.conn.execute(
            "SELECT * FROM items WHERE stock_qty <= low_stock_limit ORDER BY stock_qty ASC, name COLLATE NOCASE"
        ).fetchall()

    def customer_ledgers(self):
        return self.conn.execute(
            "SELECT name, phone, balance FROM customers WHERE balance > 0 ORDER BY balance DESC, name COLLATE NOCASE"
        ).fetchall()

    def vendor_ledgers(self):
        return self.conn.execute(
            "SELECT name, phone, balance FROM vendors WHERE balance > 0 ORDER BY balance DESC, name COLLATE NOCASE"
        ).fetchall()

    def recent_sales(self):
        return self.conn.execute(
            """
            SELECT s.invoice_no, s.sale_date, s.grand_total, s.due, COALESCE(c.name, 'Walk-in') AS customer_name
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            ORDER BY s.id DESC
            LIMIT 8
            """
        ).fetchall()

    def recent_expenses(self):
        return self.conn.execute(
            "SELECT id, expense_date, category, amount, note FROM expenses ORDER BY id DESC LIMIT 10"
        ).fetchall()

    def latest_invoice_no(self):
        row = self.conn.execute("SELECT invoice_no FROM sales ORDER BY id DESC LIMIT 1").fetchone()
        return row["invoice_no"] if row else ""

    def invoice_detail(self, invoice_no):
        sale = self.conn.execute(
            """
            SELECT s.*, COALESCE(c.name, 'Walk-in Customer') AS customer_name, COALESCE(c.phone, '') AS customer_phone
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE s.invoice_no = ?
            """,
            (invoice_no,),
        ).fetchone()
        if not sale:
            return None, []
        rows = self.conn.execute(
            "SELECT item_name, qty, rate, line_total, profit FROM sale_items WHERE sale_id = ? ORDER BY id",
            (sale["id"],),
        ).fetchall()
        return sale, rows

    def reverse_invoice(self, invoice_no):
        sale = self.conn.execute("SELECT * FROM sales WHERE invoice_no = ?", (invoice_no,)).fetchone()
        if not sale:
            return False, "Invoice not found."
        rows = self.conn.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale["id"],)).fetchall()
        for row in rows:
            self.conn.execute(
                "UPDATE items SET stock_qty = stock_qty + ?, updated_at = ? WHERE id = ?",
                (row["qty"], now_string(), row["item_id"]),
            )
        if sale["customer_id"] and sale["due"] > 0:
            self.conn.execute(
                "UPDATE customers SET balance = CASE WHEN balance >= ? THEN balance - ? ELSE 0 END WHERE id = ?",
                (sale["due"], sale["due"], sale["customer_id"]),
            )
        self.conn.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale["id"],))
        self.conn.execute("DELETE FROM sales WHERE id = ?", (sale["id"],))
        self.conn.commit()
        return True, f"Invoice reversed: {invoice_no}"

    def export_inventory_csv(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        path = EXPORT_DIR / f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow(["Item", "Category", "Qty", "Unit", "Buy", "Sell", "Low Stock"])
            for row in self.inventory_rows():
                writer.writerow([row["name"], row["category"], row["stock_qty"], row["unit"], row["buy_price"], row["sell_price"], row["low_stock_limit"]])
        return path

    def backup_database(self):
        BACKUP_DIR.mkdir(exist_ok=True)
        path = BACKUP_DIR / f"shop_manager_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_conn = sqlite3.connect(path)
        self.conn.backup(backup_conn)
        backup_conn.close()
        return path

    def maybe_send_telegram_alert(self, message):
        if self.get_setting("telegram_enabled", "0") != "1":
            return
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = self.get_setting("telegram_chat_id", "") or os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            return
        encoded = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=encoded, method="POST")
        try:
            urllib.request.urlopen(request, timeout=8).read()
        except Exception:
            pass

    def telegram_api(self, method, payload=None):
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            return {}
        payload = payload or {}
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=encoded, method="POST")
        try:
            return json.loads(urllib.request.urlopen(request, timeout=12).read().decode("utf-8"))
        except Exception:
            return {}

    def telegram_command_response(self, text):
        raw = safe_text(text)
        lower = raw.lower()
        if lower in {"/start", "/help"}:
            return (
                "Commands:\n"
                "/dashboard\n"
                "/lowstock\n"
                "/stock item_name\n"
                "/quick sold 2 sugar to ramesh 50 credit\n"
                "/quick bought 10 rice from gupta 45 paid 300"
            )
        if lower.startswith("/stock "):
            item = self.find_item(raw[7:])
            if not item:
                return "Item not found."
            return f"{item['name']}: {item['stock_qty']:.2f} {item['unit']} | Buy {item['buy_price']:.2f} | Sell {item['sell_price']:.2f}"
        if lower == "/lowstock":
            rows = self.low_stock_rows()
            if not rows:
                return "All stock levels are safe."
            return "\n".join(f"{row['name']}: {row['stock_qty']:.2f} {row['unit']}" for row in rows[:15])
        if lower == "/dashboard":
            data = self.dashboard_data()
            return (
                f"Sales Rs {data['sales']:.2f}\n"
                f"Cash Rs {data['cash']:.2f}\n"
                f"Due Rs {data['due']:.2f}\n"
                f"Purchase Rs {data['purchases']:.2f}\n"
                f"Expense Rs {data['expenses']:.2f}\n"
                f"Profit Rs {data['profit']:.2f}"
            )
        if lower.startswith("/quick "):
            ok, msg = self.quick_entry(raw[7:])
            return ("Success: " if ok else "Error: ") + msg
        return "Unknown command. Use /help"

    def telegram_poll_once(self):
        if self.get_setting("telegram_enabled", "0") != "1":
            return
        chat_id = self.get_setting("telegram_chat_id", "") or os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or not chat_id:
            return
        offset = int(self.get_setting("telegram_last_update_id", "0") or "0")
        result = self.telegram_api("getUpdates", {"offset": offset + 1, "timeout": 1})
        for update in result.get("result", []):
            update_id = update.get("update_id", offset)
            self.set_setting("telegram_last_update_id", str(update_id))
            message = update.get("message", {})
            incoming_chat = str(message.get("chat", {}).get("id", ""))
            if incoming_chat != str(chat_id):
                continue
            text = message.get("text", "")
            reply = self.telegram_command_response(text)
            self.telegram_api("sendMessage", {"chat_id": chat_id, "text": reply})

    def start_telegram_bot(self):
        def runner():
            while True:
                self.telegram_poll_once()
                time.sleep(3)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()


manager = ShopManager(DB_FILE)


def card(title, body):
    return f"<section class='card'><h2>{h(title)}</h2>{body}</section>"


def get_cookie(environ, key):
    raw = environ.get("HTTP_COOKIE", "")
    parts = [chunk.strip() for chunk in raw.split(";") if "=" in chunk]
    cookies = dict(part.split("=", 1) for part in parts)
    return cookies.get(key, "")


def create_session():
    token = secrets.token_hex(16)
    SESSIONS[token] = {"created_at": now_string()}
    return token


def render_login(message=""):
    message_html = f"<div class='flash'>{h(message)}</div>" if message else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(manager.shop_name())} Login</title>
<style>
body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(135deg,#115e59,#f59e0b);min-height:100vh;display:grid;place-items:center}}
.box{{background:#fff;border-radius:24px;padding:28px;max-width:420px;width:min(92vw,420px);box-shadow:0 20px 50px rgba(0,0,0,.18)}}
input,button{{width:100%;padding:12px 14px;border-radius:12px;border:1px solid #d4d4d8;font:inherit}}
button{{background:#115e59;color:#fff;border:none;margin-top:10px;font-weight:700}}
.flash{{margin-bottom:12px;padding:10px 12px;background:#fef3c7;border-radius:12px}}
</style></head><body>
<div class="box">
<h1>{h(manager.shop_name())}</h1>
<p>Secure local access. Default PIN: 1234</p>
{message_html}
<form method="post" action="/login">
<input type="password" name="pin" placeholder="Enter PIN">
<button type="submit">Login</button>
</form></div></body></html>"""


def render_index(lang="hi", flash=""):
    t = TEXT.get(lang, TEXT["hi"])
    metrics = manager.dashboard_data()
    inventory_rows = manager.inventory_rows()
    low_rows = manager.low_stock_rows()
    customer_rows = manager.customer_ledgers()
    vendor_rows = manager.vendor_ledgers()
    sale_rows = manager.recent_sales()
    expense_rows = manager.recent_expenses()
    latest_invoice = manager.latest_invoice_no()
    phone_link = f"http://{local_ip()}:{PORT}"
    flash_html = f"<div class='flash'>{h(flash)}</div>" if flash else ""
    inventory_html = "".join(
        f"<tr><td>{h(row['name'])}</td><td>{h(row['category'])}</td><td>{row['stock_qty']:.2f}</td><td>{h(row['unit'])}</td><td>{row['buy_price']:.2f}</td><td>{row['sell_price']:.2f}</td><td><form method='post' action='/delete-item' style='display:inline'><input type='hidden' name='lang' value='{lang}'><input type='hidden' name='item_id' value='{row['id']}'><button class='alt' type='submit'>Delete</button></form></td></tr>"
        for row in inventory_rows
    ) or "<tr><td colspan='7'>No items yet.</td></tr>"
    low_html = "".join(
        f"<li>{h(row['name'])}: {row['stock_qty']:.2f} {h(row['unit'])}</li>"
        for row in low_rows
    ) or "<li>All stock levels are safe.</li>"
    customer_html = "".join(
        f"<li>{h(row['name'])} - Rs {row['balance']:.2f}</li>"
        for row in customer_rows
    ) or "<li>No customer due.</li>"
    vendor_html = "".join(
        f"<li>{h(row['name'])} - Rs {row['balance']:.2f}</li>"
        for row in vendor_rows
    ) or "<li>No vendor due.</li>"
    sales_html = "".join(
        f"<li>{h(row['invoice_no'])} | {h(row['customer_name'])} | Rs {row['grand_total']:.2f} | Due Rs {row['due']:.2f}</li>"
        for row in sale_rows
    ) or "<li>No sales yet.</li>"
    expenses_html = "".join(
        f"<li>{h(row['expense_date'])} | {h(row['category'])} | Rs {row['amount']:.2f} "
        f"<form method='post' action='/delete-expense' style='display:inline'><input type='hidden' name='lang' value='{lang}'><input type='hidden' name='expense_id' value='{row['id']}'><button class='alt' type='submit'>Delete</button></form></li>"
        for row in expense_rows
    ) or "<li>No recent expenses.</li>"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(manager.shop_name())}</title>
<meta name="theme-color" content="#115e59">
<link rel="manifest" href="/manifest.json">
<style>
body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f5f1e8;color:#1f2937}}
.wrap{{max-width:1200px;margin:auto;padding:18px}}
.hero{{background:linear-gradient(135deg,#0f766e,#f59e0b);color:#fff;border-radius:24px;padding:22px;box-shadow:0 12px 36px rgba(0,0,0,.12)}}
.hero h1{{margin:0 0 8px;font-size:2rem}}
.hero p{{margin:6px 0}}
.phone-link{{display:inline-block;margin-top:8px;padding:10px 14px;border-radius:999px;background:#fff;color:#0f766e;text-decoration:none;font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:16px}}
.card{{background:#fff;border-radius:20px;padding:16px;box-shadow:0 10px 28px rgba(15,23,42,.08)}}
.metric{{font-size:1.8rem;font-weight:700;margin-top:8px}}
form{{display:grid;gap:8px}}
input,textarea,select,button{{font:inherit;padding:10px 12px;border-radius:12px;border:1px solid #d4d4d8}}
button{{background:#0f766e;color:#fff;border:none;font-weight:700}}
button.alt{{background:#f59e0b;color:#111827}}
table{{width:100%;border-collapse:collapse;font-size:.95rem}}
th,td{{padding:8px;border-bottom:1px solid #e5e7eb;text-align:left}}
ul{{margin:0;padding-left:18px}}
.flash{{margin:14px 0;padding:12px 14px;background:#dcfce7;color:#166534;border-radius:14px}}
.topbar{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-top:12px}}
.inline{{display:flex;gap:8px;flex-wrap:wrap}}
.note{{font-size:.9rem;color:#475569}}
@media (max-width:700px){{.hero h1{{font-size:1.5rem}} .wrap{{padding:12px}} }}
</style>
</head>
<body>
<div class="wrap">
<div class="hero">
<h1>{h(manager.shop_name())}</h1>
<p>{h(t["tagline"])}</p>
<p>{h(t["open_phone"])}: <strong>{h(phone_link)}</strong></p>
<a class="phone-link" href="{h(phone_link)}" target="_blank">{h(t["open_phone"])}</a>
</div>
<div class="topbar">
<form method="get" class="inline">
<input type="hidden" name="lang" value="{'en' if lang == 'hi' else 'hi'}">
<button class="alt" type="submit">{h(t["language"])}</button>
</form>
<form method="post" action="/export" class="inline">
<input type="hidden" name="lang" value="{lang}">
<button type="submit">Export CSV</button>
</form>
<form method="post" action="/backup" class="inline">
<input type="hidden" name="lang" value="{lang}">
<button type="submit">Backup DB</button>
</form>
<a class="phone-link" style="margin-top:0" href="/invoice?invoice_no={urllib.parse.quote(latest_invoice)}" target="_blank">{'Print Last Invoice' if latest_invoice else 'No Invoice Yet'}</a>
<form method="post" action="/logout" class="inline"><button class="alt" type="submit">Logout</button></form>
</div>
{flash_html}
<div class="grid">
{card(t["dashboard"], f"<div class='metric'>Rs {metrics['sales']:.2f}</div><div>Sales today</div><div class='note'>Cash Rs {metrics['cash']:.2f} | Due Rs {metrics['due']:.2f}<br>Purchase Rs {metrics['purchases']:.2f} | Expense Rs {metrics['expenses']:.2f}<br>Gross profit Rs {metrics['profit']:.2f} | Stock value Rs {metrics['stock_value']:.2f}</div>")}
{card(t["quick_entry"], f"<form method='post' action='/quick-entry'><input type='hidden' name='lang' value='{lang}'><textarea id='quickText' name='quick_text' rows='4' placeholder='{h(t['quick_help'])}'></textarea><div class='inline'><button type='submit'>{h(t['save'])}</button><button class='alt' type='button' onclick='startVoice()'>{h(t['voice'])}</button></div><div class='note'>{h(t['quick_help'])}</div></form>")}
{card(t["add_item"], f"<form method='post' action='/add-item'><input type='hidden' name='lang' value='{lang}'><input name='name' placeholder='Item name'><input name='category' placeholder='Category'><input name='unit' placeholder='Unit'><input name='qty' placeholder='Opening qty'><input name='buy_price' placeholder='Buy price'><input name='sell_price' placeholder='Sell price'><input name='low_stock_limit' placeholder='Low stock limit' value='5'><button type='submit'>{h(t['save'])}</button></form>")}
{card(t["purchase"], f"<form method='post' action='/purchase'><input type='hidden' name='lang' value='{lang}'><input name='item_name' placeholder='Item name'><input name='vendor_name' placeholder='Vendor name'><input name='qty' placeholder='Qty'><input name='rate' placeholder='Rate'><input name='paid' placeholder='Paid amount'><input name='note' placeholder='Note'><button type='submit'>{h(t['save'])}</button></form>")}
{card("Stock Adjust", f"<form method='post' action='/adjust-stock'><input type='hidden' name='lang' value='{lang}'><input name='item_name' placeholder='Item name'><select name='adjustment_type'><option value='set'>Set exact qty</option><option value='add'>Add qty</option><option value='remove'>Remove qty</option></select><input name='qty' placeholder='Qty'><button type='submit'>{h(t['save'])}</button></form>")}
{card(t["sale"], f"<form method='post' action='/sale'><input type='hidden' name='lang' value='{lang}'><input name='customer_name' placeholder='Customer name'><input name='customer_phone' placeholder='Phone'><textarea name='items' rows='4' placeholder='One line each: sugar,2,50'></textarea><input name='discount' placeholder='Discount' value='0'><select name='payment_mode'><option value='cash'>Cash</option><option value='upi'>UPI</option><option value='card'>Card</option><option value='credit'>Credit/Udhaar</option></select><input name='paid' placeholder='Paid amount'><input name='note' placeholder='Note'><button type='submit'>{h(t['save'])}</button></form>")}
{card(t["expense"], f"<form method='post' action='/expense'><input type='hidden' name='lang' value='{lang}'><input name='category' placeholder='Expense type'><input name='amount' placeholder='Amount'><input name='note' placeholder='Note'><button type='submit'>{h(t['save'])}</button></form>")}
{card("Reverse Invoice", f"<form method='post' action='/reverse-invoice'><input type='hidden' name='lang' value='{lang}'><input name='invoice_no' placeholder='Invoice no e.g. INV-20260322-001'><button class='alt' type='submit'>Reverse Invoice</button></form><div class='note'>Use only when full sale cancellation karni ho.</div>")}
{card("Customer Payment", f"<form method='post' action='/customer-payment'><input type='hidden' name='lang' value='{lang}'><input name='customer_name' placeholder='Customer name'><input name='amount' placeholder='Amount received'><button type='submit'>{h(t['save'])}</button></form>")}
{card("Vendor Payment", f"<form method='post' action='/vendor-payment'><input type='hidden' name='lang' value='{lang}'><input name='vendor_name' placeholder='Vendor name'><input name='amount' placeholder='Amount paid'><button type='submit'>{h(t['save'])}</button></form>")}
{card("Settings", f"<form method='post' action='/settings'><input type='hidden' name='lang' value='{lang}'><input name='shop_name' placeholder='Shop name' value='{h(manager.shop_name())}'><input name='app_pin' placeholder='New PIN'><input name='telegram_chat_id' placeholder='Telegram chat id' value='{h(manager.get_setting('telegram_chat_id',''))}'><label><input type='checkbox' name='telegram_enabled' value='1' {'checked' if manager.get_setting('telegram_enabled','0')=='1' else ''}> Telegram enabled</label><button type='submit'>{h(t['save'])}</button></form><div class='note'>Telegram token ko system environment variable `TELEGRAM_BOT_TOKEN` me set rakhiye.</div>")}
{card(t["low_stock"], f"<ul>{low_html}</ul>")}
{card(t["ledger"], f"<strong>Customer Due</strong><ul>{customer_html}</ul><strong>Vendor Due</strong><ul>{vendor_html}</ul>")}
{card(t["recent_sales"], f"<ul>{sales_html}</ul>")}
{card("Recent Expenses", f"<ul>{expenses_html}</ul>")}
{card(t["inventory"], f"<div style='overflow:auto'><table><thead><tr><th>Item</th><th>Category</th><th>Qty</th><th>Unit</th><th>Buy</th><th>Sell</th><th>Action</th></tr></thead><tbody>{inventory_html}</tbody></table></div>")}
</div>
</div>
<script>
if ('serviceWorker' in navigator) {{ window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js')); }}
function startVoice(){{
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!Speech){{ alert('Voice input browser me supported nahi hai. Chrome Android try kijiye.'); return; }}
  const recog = new Speech();
  recog.lang = 'hi-IN';
  recog.interimResults = false;
  recog.maxAlternatives = 1;
  recog.onresult = function(event){{ document.getElementById('quickText').value = event.results[0][0].transcript; }};
  recog.start();
}}
</script>
</body>
</html>"""


def render_invoice(invoice_no):
    sale, items = manager.invoice_detail(invoice_no)
    if not sale:
        return "<h1>Invoice not found</h1>"
    rows = "".join(
        f"<tr><td>{h(row['item_name'])}</td><td>{row['qty']:.2f}</td><td>{row['rate']:.2f}</td><td>{row['line_total']:.2f}</td></tr>"
        for row in items
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(invoice_no)}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;margin:0;padding:24px;color:#111827}}
.bill{{max-width:760px;margin:auto;background:#fff;padding:24px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,.08)}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}}
.actions{{margin-top:16px;display:flex;gap:10px;flex-wrap:wrap}} button,a{{padding:10px 14px;border:none;border-radius:12px;background:#115e59;color:#fff;text-decoration:none;font:inherit}}
@media print {{ .actions{{display:none}} body{{background:#fff;padding:0}} .bill{{box-shadow:none;border-radius:0}} }}
</style></head><body>
<div class="bill">
<h1>{h(manager.shop_name())}</h1>
<h2>Invoice {h(sale['invoice_no'])}</h2>
<p>Date: {h(sale['sale_date'])}<br>Customer: {h(sale['customer_name'])}<br>Phone: {h(sale['customer_phone'])}</p>
<table><thead><tr><th>Item</th><th>Qty</th><th>Rate</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
<p>Subtotal: Rs {sale['subtotal']:.2f}<br>Discount: Rs {sale['discount']:.2f}<br>Grand Total: Rs {sale['grand_total']:.2f}<br>Paid: Rs {sale['paid']:.2f}<br>Due: Rs {sale['due']:.2f}<br>Payment: {h(sale['payment_mode'])}</p>
<div class="actions"><button onclick="window.print()">Print / Save PDF</button><a href="/">Back</a></div>
</div></body></html>"""


def render_manifest():
    data = {
        "name": manager.shop_name(),
        "short_name": manager.shop_name(),
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f5f1e8",
        "theme_color": "#115e59",
        "icons": [],
    }
    return json.dumps(data)


def render_service_worker():
    return """self.addEventListener('install', event => self.skipWaiting());
self.addEventListener('activate', event => self.clients.claim());"""


def parse_post(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH", "0") or "0")
    except ValueError:
        size = 0
    raw = environ["wsgi.input"].read(size).decode("utf-8")
    parsed = urllib.parse.parse_qs(raw)
    return {key: values[0] for key, values in parsed.items()}


def redirect(start_response, location):
    start_response("302 Found", [("Location", location)])
    return [b""]


def app(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")
    query = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
    lang = query.get("lang", ["hi"])[0]
    session_id = get_cookie(environ, "shop_session")
    logged_in = session_id in SESSIONS

    if method == "GET" and path == "/manifest.json":
        start_response("200 OK", [("Content-Type", "application/manifest+json")])
        return [render_manifest().encode("utf-8")]

    if method == "GET" and path == "/sw.js":
        start_response("200 OK", [("Content-Type", "application/javascript; charset=utf-8")])
        return [render_service_worker().encode("utf-8")]

    if method == "GET" and path == "/login":
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [render_login().encode("utf-8")]

    if method == "POST" and path == "/login":
        form = parse_post(environ)
        if manager.verify_pin(form.get("pin")):
            token = create_session()
            start_response("302 Found", [("Location", "/"), ("Set-Cookie", f"shop_session={token}; HttpOnly; SameSite=Lax; Path=/")])
            return [b""]
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [render_login("Wrong PIN.").encode("utf-8")]

    if method == "POST" and path == "/logout":
        start_response("302 Found", [("Location", "/login"), ("Set-Cookie", "shop_session=; Max-Age=0; Path=/")])
        return [b""]

    if not logged_in:
        return redirect(start_response, "/login")

    if method == "GET" and path == "/":
        flash = query.get("flash", [""])[0]
        page = render_index(lang=lang, flash=flash)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [page.encode("utf-8")]

    if method == "GET" and path == "/invoice":
        invoice_no = query.get("invoice_no", [""])[0]
        page = render_invoice(invoice_no)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [page.encode("utf-8")]

    if method == "POST":
        form = parse_post(environ)
        lang = form.get("lang", lang)
        if path == "/add-item":
            ok, message = manager.add_item_record(form)
        elif path == "/delete-item":
            ok, message = manager.delete_item_record(int(form.get("item_id", "0") or "0"))
        elif path == "/purchase":
            ok, message = manager.purchase_item_record(form)
        elif path == "/adjust-stock":
            ok, message = manager.adjust_stock_record(form)
        elif path == "/sale":
            ok, message = manager.create_sale_record(form)
        elif path == "/reverse-invoice":
            ok, message = manager.reverse_invoice(form.get("invoice_no"))
        elif path == "/expense":
            ok, message = manager.add_expense_record(form)
        elif path == "/delete-expense":
            ok, message = manager.delete_expense_record(int(form.get("expense_id", "0") or "0"))
        elif path == "/customer-payment":
            ok, message = manager.receive_customer_payment(form)
        elif path == "/vendor-payment":
            ok, message = manager.pay_vendor_due(form)
        elif path == "/quick-entry":
            ok, message = manager.quick_entry(form.get("quick_text"))
        elif path == "/export":
            path_obj = manager.export_inventory_csv()
            ok, message = True, f"CSV export created: {path_obj.name}"
        elif path == "/backup":
            path_obj = manager.backup_database()
            ok, message = True, f"Backup created: {path_obj.name}"
        elif path == "/settings":
            ok, message = manager.update_settings(form)
        else:
            ok, message = False, "Unknown action."
        flash = urllib.parse.quote(("Success: " if ok else "Error: ") + message)
        return redirect(start_response, f"/?lang={lang}&flash={flash}")

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not found"]


def main():
    manager.start_telegram_bot()
    print(f"{manager.shop_name()} running on http://127.0.0.1:{PORT}")
    print(f"Phone access: http://{local_ip()}:{PORT}")
    print("Login PIN default: 1234")
    print("Stop with Ctrl+C")
    with make_server(HOST, PORT, app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
