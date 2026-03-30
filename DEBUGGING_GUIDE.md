# Voice Accounting System - Debugging & Testing Guide

**Purpose:** Complete guide for debugging, testing, and troubleshooting the Voice Accounting System  
**Last Updated:** 2025-03-15  
**Status:** All systems verified and operational

---

## Quick Troubleshooting Guide

### Problem: Server won't start
```powershell
# 1. Verify environment is activated
.\.venv\Scripts\Activate.ps1

# 2. Check Python version
python --version
# Expected: Python 3.11.0

# 3. Verify all packages installed
pip freeze | findstr -E "flask|sqlalchemy|login|cryptography|reportlab"

# 4. Clear Python cache
Remove-Item -Recurse -Force .\app\__pycache__
Remove-Item -Recurse -Force .\instance\

# 5. Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# 6. Start server with verbose output
python run.py
```

### Problem: Database errors
```powershell
# 1. Backup existing database
Copy-Item instance\accounting_system.db instance\accounting_system.db.bak

# 2. Delete corrupted database
Remove-Item instance\accounting_system.db

# 3. Delete database initialization flag
Remove-Item instance\.db_initialized

# 4. Restart server (will recreate database)
python run.py
```

### Problem: Login not working
```
1. Verify default users exist
   - Open database browser or SQLite viewer
   - Check 'users' table has 'admin' and 'staff' users
   
2. Check password hashing
   - User passwords are hashed with PBKDF2+SHA256
   - Default credentials: admin/Admin@1234, staff/Staff@1234
   
3. Clear session cookies in browser
   - Open DevTools (F12)
   - Application > Cookies > Delete all
   - Clear cache and reload
```

### Problem: Voice commands not working
```
1. Check browser compatibility
   - Chrome, Edge, Firefox, Safari supported
   - Private/Incognito mode sometimes blocks Microphone API
   
2. Grant microphone permission
   - Click allow when browser prompts
   - Check browser Settings > Privacy > Microphone
   
3. Check Voice Parser
   - Test voice parser offline: python tests/test_voice_parser.py
   - Verify regex patterns in app/utils/voice_parser.py
```

### Problem: PDF generation fails
```
1. Verify ReportLab installed
   python -c "import reportlab; print(reportlab.__version__)"
   
2. Check invoices directory exists
   mkdir invoices  # if needed
   
3. Test PDF generation
   python tests/test_invoice_generator.py
```

---

## Verification Tests

### 1. Module Import Test

```python
# Run this to verify all modules load correctly
python -c "
from app import create_app, db
from app.database.models import User, Party, Material, Vehicle, Transaction
from app.utils.voice_parser import VoiceParser
from app.utils.security import SecurityManager
from app.utils.invoice_generator import InvoiceGenerator
print('All modules imported successfully!')
"
```

### 2. Database Integrity Test

```python
# Test database structure and default data
python

from app import create_app, db
from app.database.models import User, Party

app = create_app()
with app.app_context():
    # Check user count
    users = User.query.all()
    print(f"Users: {len(users)}")
    
    # List users
    for user in users:
        print(f"  - {user.username} (active: {user.is_active})")
```

### 3. Application Startup Test

```powershell
# 1. Start server
python run.py

# 2. In another PowerShell window, test endpoints
$uri = "http://localhost:5000"

# Test home page
Invoke-WebRequest -Uri "$uri/" | Select StatusCode

# Test login page
Invoke-WebRequest -Uri "$uri/auth/login" | Select StatusCode

# Test dashboard (should redirect to login)
Invoke-WebRequest -Uri "$uri/dashboard/" -AllowRedirect | Select StatusCode
```

### 4. Voice Parser Test

```python
from app.utils.voice_parser import VoiceParser

parser = VoiceParser()

# Test voice string parsing
test_voice = "Ramesh ne reti truck se 6 trip liya 1200 rupaye ka udhar mein"
result = parser.parse(test_voice)

print("Parsed:")
print(f"  Party: {result.get('party')}")
print(f"  Material: {result.get('material')}")
print(f"  Vehicle: {result.get('vehicle')}")
print(f"  Quantity: {result.get('quantity')}")
print(f"  Amount: {result.get('amount')}")
print(f"  Payment Status: {result.get('payment_status')}")
```

### 5. Invoice Generation Test

```python
from app import create_app, db
from app.database.models import User, Transaction
from app.utils.invoice_generator import InvoiceGenerator
from datetime import datetime

app = create_app()
with app.app_context():
    # Create a test transaction first
    user = User.query.filter_by(username='admin').first()
    
    # Create invoice
    generator = InvoiceGenerator()
    pdf_path = generator.generate_invoice(
        party_name="Test Party",
        amount=1200,
        transaction_date=datetime.now(),
        description="Test transaction"
    )
    
    print(f"Invoice created: {pdf_path}")
```

### 6. Security Features Test

```python
from app.utils.security import SecurityManager
from app.database.models import User

security = SecurityManager()

# Test password hashing
password = "TestPassword123!"
hashed = security.hash_password(password)
print(f"Original: {password}")
print(f"Hashed: {hashed}")

# Test password verification
verified = security.verify_password(password, hashed)
print(f"Verification result: {verified}")

# Test input sanitization
test_sql = "'; DROP TABLE users; --"
sanitized = security.sanitize_input(test_sql)
print(f"Original: {test_sql}")
print(f"Sanitized: {sanitized}")
```

---

## API Testing

### Login Endpoint
```powershell
# POST /auth/login
$body = @{
    username = "admin"
    password = "Admin@1234"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### Get Dashboard Data
```powershell
# GET /dashboard/
Invoke-WebRequest -Uri "http://localhost:5000/dashboard/" `
    -AllowRedirect
```

### Create Transaction (API)
```powershell
$body = @{
    party_id = 1
    material_id = 1
    vehicle_id = 1
    quantity = 5
    unit_price = 1200
    payment_status = "paid"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:5000/api/transactions" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### Get All Parties (API)
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/api/parties" `
    -Method GET
```

---

## Logging & Debugging

### View Application Logs

```powershell
# Real-time log viewing
Get-Content instance/accounting_system.log -Tail 50 -Wait

# Filter logs by level
Select-String "ERROR|WARNING" instance/accounting_system.log

# Count log entries by level
(Get-Content instance/accounting_system.log) | `
    Select-String -Pattern "INFO|ERROR|WARNING|DEBUG" | `
    Select-Object { $_ -replace '.*\[(\w+)\].*', '$1' } | `
    Group-Object | `
    Select-Object Count, Name
```

### Enable Debug Mode

Edit `run.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    # Change: app.run(debug=True, ...)
```

### Database Query Debugging

```python
from flask_sqlalchemy import get_debug_queries
from app import create_app

app = create_app()
app.config['SQLALCHEMY_ECHO'] = True  # Enable SQL query logging

# Now all SQL queries will be printed to console
```

---

## Performance Testing

### Stress Test the Voice Parser

```python
import time
from app.utils.voice_parser import VoiceParser

parser = VoiceParser()

test_cases = [
    "Ramesh ne reti truck 6 trip 1200 paid",
    "Party A material B vehicle C 10 units 500 udhar",
    "Name X substance Y transport Z 3 qty 2000 cash",
    # Add more test cases...
]

start = time.time()
for test in test_cases:
    result = parser.parse(test)
duration = time.time() - start

print(f"Parsed {len(test_cases)} commands in {duration:.3f}s")
print(f"Average: {duration/len(test_cases)*1000:.2f}ms per command")
```

### Database Performance Test

```python
import time
from app import create_app, db
from app.database.models import Transaction

app = create_app()
with app.app_context():
    # Test query performance
    start = time.time()
    for i in range(1000):
        count = Transaction.query.count()
    duration = time.time() - start
    
    print(f"1000 queries in {duration:.3f}s")
    print(f"Average: {duration/1000*1000:.2f}ms per query")
```

---

## Security Testing

### Password Strength Validation

```python
from app.utils.security import SecurityManager

security = SecurityManager()

test_passwords = [
    "weak",                      # Too short
    "WeakPassword",              # No number
    "123456789",                 # No letter
    "Str0ng!Pass",              # Good
    "VeryStr0ng!Password123",   # Excellent
]

for pwd in test_passwords:
    result = security.validate_password(pwd)
    print(f"{pwd:25} - {result}")
```

### SQL Injection Test

```python
from app.utils.security import SecurityManager

security = SecurityManager()

bad_inputs = [
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "<script>alert('XSS')</script>",
    "../../etc/passwd",
    "%27 OR %271%27=%271",
]

for bad_input in bad_inputs:
    sanitized = security.sanitize_input(bad_input)
    print(f"Input:     {bad_input}")
    print(f"Sanitized: {sanitized}")
    print()
```

---

## File Structure Verification

```powershell
# Verify complete project structure
Get-ChildItem -Recurse -Path . -Include "*.py" | `
    Select-Object FullName | `
    ConvertTo-Csv -NoTypeInformation | `
    ForEach-Object {$_ -replace '.*\\', ''} | `
    Sort-Object

# Check file existence
@(
    "run.py",
    "app/__init__.py",
    "app/database/models.py",
    "app/utils/voice_parser.py",
    "app/utils/security.py",
    "app/utils/invoice_generator.py",
    "app/routes/auth.py",
    "app/routes/dashboard.py",
    "app/routes/transactions.py",
    "app/routes/api.py",
    "requirements.txt",
    ".env"
) | ForEach-Object {
    if (Test-Path $_) {
        Write-Host "[OK] $_"
    } else {
        Write-Host "[MISSING] $_"
    }
}
```

---

## Environment Verification

```powershell
# Check virtual environment
.\.venv\Scripts\Activate.ps1
python -m venv --help  # Should show venv is available

# Check Python paths
python -c "import sys; print('\\n'.join(sys.path))"

# Verify pip is from venv
$(where.exe python)[0]
# Should show: ..\.venv\Scripts\python.exe

# List all installed packages
pip list

# Generate requirements.txt
pip freeze > requirements.txt
```

---

## Common Error Messages & Solutions

### ImportError: Cannot import name 'create_app'
```
Cause: app/__init__.py not in correct location or has errors
Solution:
1. Verify app/__init__.py exists
2. Check for syntax errors: python -m py_compile app/__init__.py
3. Ensure create_app function is defined
```

### ModuleNotFoundError: No module named 'flask'
```
Cause: Flask not installed or wrong Python environment
Solution:
1. Activate venv: .\.venv\Scripts\Activate.ps1
2. Install: pip install flask
3. Verify: python -c "import flask"
```

### sqlite3.OperationalError: no such table
```
Cause: Database tables not created
Solution:
1. Delete instance/accounting_system.db
2. Restart server - tables are auto-created
3. Check app/__init__.py has create_tables code
```

### CSRF validation failed
```
Cause: Form CSRF token missing or invalid
Solution:
1. Clear browser cookies and cache
2. Hard refresh (Ctrl+Shift+R)
3. Check SECRET_KEY in .env is set
```

### Port 5000 already in use
```
Cause: Another application using port 5000
Solution:
# Find process using port 5000
netstat -ano | findstr :5000

# Kill process (replace PID)
taskkill /PID 1234 /F

# Or use different port
python run.py  # Edit run.py to change port
```

---

## Advanced Debugging

### Enable SQL Query Logging

Create `debug_queries.py`:
```python
from app import create_app, db
from flask_sqlalchemy import get_debug_queries

app = create_app()
app.config['SQLALCHEMY_ECHO'] = True

with app.app_context():
    from app.database.models import User
    users = User.query.all()
    
    for query in get_debug_queries():
        print(f"Query: {query.statement}")
        print(f"Time: {query.duration}ms")
```

### Memory Profiling

```python
from memory_profiler import profile
from app.utils.voice_parser import VoiceParser

@profile
def test_voice_parser():
    parser = VoiceParser()
    for i in range(100):
        result = parser.parse("Ramesh reti truck 6 trip 1200")
    return result

# Run with: python -m memory_profiler debug_memory.py
```

### Request/Response Logging

```python
from app import create_app

app = create_app()

@app.before_request
def log_request():
    print(f"[REQUEST] {request.method} {request.path}")

@app.after_request
def log_response(response):
    print(f"[RESPONSE] {response.status_code}")
    return response
```

---

## Success Indicators

When everything is working correctly, you should see:

1. **Server Start Output**
   ```
   [2025-03-15 ...] INFO in __init__: Application started
   WARNING: This is a development server. Do not use it in production.
   * Running on http://127.0.0.1:5000
   ```

2. **Login Successful**
   - Redirects to dashboard
   - Session cookie created
   - Audit log entry recorded

3. **Voice Command Parsed**
   - Browser shows "Listening..." status
   - Console shows parsed transaction details
   - New transaction created in database

4. **Invoice Generated**
   - PDF file created in invoices/
   - Entry added to transactions table
   - No errors in log file

5. **Database Operations**
   - Query executes without errors
   - Data persists across restarts
   - Relationships work correctly

---

## Support & Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org/
- **ReportLab Guide:** https://www.reportlab.com/docs/reportlab-userguide.pdf
- **Web Speech API:** https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API

---

## Final Notes

- Always keep a backup of the database file
- Review logs regularly for errors and warnings
- Test changes in a development branch first
- Keep dependencies updated periodically
- Monitor server performance and response times
- Keep audit logs for compliance and debugging

**System is now ready for full testing and deployment.**
