# 🎤 Voice Accounting System

A **secure, private, web-based voice accounting system** designed for tracking transactions, parties, materials, vehicles, and generating invoices with voice input support.

## ✨ Features

✅ **Voice Input** - Microphone button with browser Speech API for voice-to-text conversion
✅ **Smart Parser** - Extracts party, material, vehicle, quantity, rate, trips, and payment status from voice commands
✅ **Invoice Generation** - Auto-generates PDF invoices and ledger reports
✅ **Secure Authentication** - Login with strong password policy, admin/staff roles, optional 2FA
✅ **Database** - SQLite with Transactions, Parties, Materials, Vehicles, Payments, Expenses, Audit Logs
✅ **Security Features** - HTTPS encryption, input sanitization, rate limiting, audit logs, session timeout, IP whitelisting
✅ **Network Access** - Access from phone via Wi-Fi using local server
✅ **RESTful API** - Manage parties, materials, vehicles, and transactions programmatically

## 📋 Voice Command Examples

```
"Ramesh reti tractor 6 trip 1200 udhar"
"Amit balu truck 10 800 paid"
"Priya stone tractor 5 1500 advance"
```

Extracted:
- **Party**: Ramesh, Amit, Priya
- **Material**: reti (sand), balu (sand), stone
- **Vehicle**: tractor, truck
- **Quantity**: 6, 10, 5
- **Rate**: 1200, 800, 1500
- **Payment**: udhar (pending), paid, advance (partial)

## 🚀 Quick Start

### 1. Prerequisites
- Windows 10/11
- Python 3.8+
- pip (Python package manager)

### 2. Setup Python Environment

```powershell
# Navigate to project directory
cd "c:\Users\DELL\OneDrive\ledger\voice_accounting_system"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Dependencies

```powershell
# Install required packages
pip install -r requirements.txt
```

### 4. Run the Application

```powershell
# Start the development server
python run.py
```

You should see:
```
============================================================
🎤 VOICE ACCOUNTING SYSTEM
============================================================

✓ Database initialized
✓ Default users created:
  • Admin: admin / Admin@1234
  • Staff: staff / Staff@1234

⚠️  IMPORTANT: Change default passwords immediately!

📱 Starting development server...
🌐 Visit: http://localhost:5000
🔐 Use HTTPS in production!

Press Ctrl+C to stop the server
============================================================
```

### 5. Access in Browser

- **Local**: Navigate to `http://localhost:5000`
- **From Phone**: Open phone browser and go to `http://<YOUR_LAPTOP_IP>:5000`
  - Find your IP: Open Command Prompt and type `ipconfig` (look for "IPv4 Address" under your network)

### 6. Login

**Default Credentials:**
- Username: `admin` / Password: `Admin@1234`
- Username: `staff` / Password: `Staff@1234`

⚠️ **CHANGE THESE IMMEDIATELY IN PRODUCTION!**

## 📁 Project Structure

```
voice_accounting_system/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── database/
│   │   └── models.py         # SQLAlchemy models
│   ├── routes/
│   │   ├── auth.py           # Login, registration, password change
│   │   ├── dashboard.py      # Dashboard & statistics
│   │   ├── transactions.py   # Transaction CRUD & voice parsing
│   │   └── api.py            # RESTful API endpoints
│   ├── utils/
│   │   ├── voice_parser.py   # Voice text parser
│   │   ├── security.py       # Authentication & security
│   │   └── invoice_generator.py  # PDF invoice generation
│   ├── static/               # CSS, JS, images
│   └── templates/            # HTML templates
├── invoices/                 # Generated PDF invoices
├── logs/                     # Application logs
├── backups/                  # Database backups
├── run.py                    # Entry point
└── requirements.txt          # Python dependencies
```

## 🔐 Security Features

### Authentication
- ✅ Strong password requirements (8 chars, uppercase, lowercase, digit, special char)
- ✅ Secure password hashing (PBKDF2)
- ✅ Role-based access (admin/staff)
- ✅ Session timeout (30 minutes default)
- ✅ Audit logging of all actions
- ✅ Login attempt tracking

### Input & Data
- ✅ Input sanitization (SQL injection prevention)
- ✅ XSS protection
- ✅ CSRF protection
- ✅ Rate limiting
- ✅ Device/IP restrictions (optional)

### Network & Storage
- ✅ HTTPS ready (configure in production)
- ✅ Secure session cookies
- ✅ Database encryption (SQLite)
- ✅ Automatic backups
- ✅ Invoice file storage with access control

## 💻 Using Voice Commands

1. Click **🎤 Start Recording** button on Dashboard
2. Say your command (e.g., "Ramesh reti tractor 6 trip 1200 udhar")
3. Parsed data appears in text field
4. Click **Create Transaction from Voice** to save

Example commands:
```
"Ramesh reti tractor 6 trip 1200 udhar"
→ Party: Ramesh, Material: reti, Vehicle: tractor, Qty: 6, Rate: 1200, Status: pending

"Amit balu truck 10 800 paid"
→ Party: Amit, Material: balu, Vehicle: truck, Qty: 10, Rate: 800, Status: paid
```

## 📊 Dashboard Features

- **Statistics**: Total transactions, amount, pending, today's total
- **Recent Transactions**: Last 10 entries with quick view
- **Top Parties**: Parties by transaction count
- **Quick Actions**: New transaction, manage parties/materials

## 📄 Invoice Generation

- Auto-generated when transaction created
- PDF format with party details, amounts, and status
- Downloadable from transaction view
- Stored in `invoices/` folder

## 🔌 API Endpoints

### Parties
- `GET /api/parties` - List all parties
- `POST /api/parties` - Create party
- `PUT /api/parties/<id>` - Update party
- `DELETE /api/parties/<id>` - Delete party

### Materials
- `GET /api/materials` - List all materials
- `POST /api/materials` - Create material
- `PUT /api/materials/<id>` - Update material
- `DELETE /api/materials/<id>` - Delete material

### Vehicles
- `GET /api/vehicles` - List all vehicles
- `POST /api/vehicles` - Create vehicle
- `PUT /api/vehicles/<id>` - Update vehicle
- `DELETE /api/vehicles/<id>` - Delete vehicle

### Transactions
- `POST /api/parse-voice` - Parse voice text
- `POST /api/create-from-voice` - Create transaction from voice

## 📱 Access from Phone

### Windows:
1. Find your laptop IP: Open Command Prompt, type `ipconfig`
2. Look for "IPv4 Address" (usually 192.168.x.x)
3. On phone browser: `http://192.168.x.x:5000`

### Network Requirements:
- Phone and laptop on same Wi-Fi network
- Firewall allows port 5000 (or configure firewall)

## 🔧 Production Deployment

### Generate HTTPS Certificate
```powershell
pip install pyopenssl

# Create self-signed certificate
python -c "
from OpenSSL import crypto, SSL
import os

CERT_DIR = 'certs'
if not os.path.exists(CERT_DIR):
    os.makedirs(CERT_DIR)

# Create certificate (valid for 365 days)
os.system('openssl req -x509 -newkey rsa:4096 -nodes -out certs/cert.pem -keyout certs/key.pem -days 365 -subj \"/CN=localhost\"')
"
```

### Run with HTTPS
```powershell
python -c "
from app import create_app
app = create_app()
app.run(
    host='0.0.0.0',
    port=443,
    ssl_context=('certs/cert.pem', 'certs/key.pem'),
    debug=False
)
"
```

## 📝 Database

- **Type**: SQLite (file-based, no server needed)
- **Location**: `accounting_system.db` in project root
- **Auto-backup**: Yes (configure in `.env`)
- **Encryption**: Optional (install `sqlcipher`)

### Tables:
- `users` - System users (admin, staff)
- `parties` - Client/customer information
- `materials` - Goods/materials sold
- `vehicles` - Transport vehicles
- `transactions` - Voice/manual transaction entries
- `payments` - Payment records
- `expenses` - Additional expenses
- `audit_logs` - Security audit trail

## 🐛 Troubleshooting

### "Module not found" Error
```powershell
# Activate virtual environment again
.\venv\Scripts\Activate.ps1

# Reinstall packages
pip install -r requirements.txt
```

### Port 5000 Already in Use
```powershell
# Find process using port 5000
netstat -ano | findstr :5000

# Kill the process
taskkill /PID <PID> /F

# Or use different port (edit run.py)
```

### Speech Recognition Not Working
- ✅ Use Chrome, Edge, or Safari (not Firefox)
- ✅ Enable microphone permissions in browser
- ✅ Check browser console for errors (F12)

### Database Lock Error
```powershell
# Delete database and restart
Remove-Item accounting_system.db
python run.py
```

## 📚 Voice Parser Logic

The parser recognizes:
- **Party Names**: First word or proper nouns
- **Materials**: reti, balu, mitti, stone, cement, brick, sand, gravel
- **Vehicles**: tractor, truck, tempo, chhota (small), bada (big)
- **Numbers**: Quantity, rate, trips (in order)
- **Payment Status**: udhar (pending), paid, advance (partial)

Example: "Ramesh reti tractor 6 trip 1200 udhar"
- Party: Ramesh
- Material: reti
- Vehicle: tractor
- Quantity: 6
- Trips: 1 (or extracted from "6 trip")
- Rate: 1200
- Payment: pending (udhar)

## 🔄 Automatic Backups

Configure in `.env`:
```
AUTO_BACKUP=True
BACKUP_FREQUENCY=daily
```

Backups stored in `backups/` folder

## 📞 Support & Maintenance

### Regular Tasks:
- Change default passwords immediately
- Enable HTTPS in production
- Review audit logs regularly
- Backup database daily
- Update Python packages: `pip install -U -r requirements.txt`

### Security Checklist:
- [ ] Change admin/staff passwords
- [ ] Configure HTTPS/SSL
- [ ] Set strong SECRET_KEY in .env
- [ ] Enable session timeout
- [ ] Review audit logs
- [ ] Test voice input with various accents
- [ ] Test invoice generation
- [ ] Verify invoice storage security

## 📜 License

Private & Secure for Office Use

---

**Version**: 1.0  
**Created**: 2026  
**Last Updated**: March 15, 2026
