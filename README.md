# WorkVault - HR & Payroll Management System

**A comprehensive HR and Payroll management system with face recognition attendance tracking, built with Flask and Supabase.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3%2B-green)](https://flask.palletsprojects.com/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange)](https://supabase.com/)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Supabase account (free)
- Modern web browser with camera

### Installation (5 minutes)

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd WorkVault
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   copy .env.example .env  # Windows
   # Edit .env with your Supabase credentials
   ```

3. **Setup database:**
   - Run `database_schema.sql` in Supabase SQL Editor

4. **Create admin:**
   ```bash
   python create_admin.py
   ```

5. **Start app:**
   ```bash
   python run.py
   ```

6. **Open browser:** http://localhost:5000

**📖 Need detailed instructions?** See [GETTING_STARTED.md](GETTING_STARTED.md) for complete setup guide.

---

## ✨ Key Features

### 👥 Attendance Management
- ✅ **Face Recognition** clock in/out (prevents buddy punching)
- ✅ **Auto-detection** of late arrivals (10-min grace period)
- ✅ **Daily reset** at 6:00 AM
- ✅ **Correction requests** for missed clock ins/outs
- ✅ **Real-time tracking** with auto-refresh

### 💰 Payroll System
- ✅ **Automated calculation** with Philippine standards
- ✅ **Overtime pay** (1.5x time-and-a-half)
- ✅ **Deductions** (SSS, PhilHealth, Pag-IBIG, Tax)
- ✅ **Semi-monthly periods** (1-15, 16-end)
- ✅ **Payroll preview** for employees before finalization
- ✅ **Excel export** for reports

### 🏖️ Leave Management
- ✅ **Leave requests** by employees
- ✅ **HR approval workflow**
- ✅ **Leave balance tracking**
- ✅ **Multiple leave types** (sick, vacation, emergency, personal)

### 📊 Employee Directory
- ✅ **Real-time attendance status** (Present/Late/Absent)
- ✅ **Filter by department and position**
- ✅ **Search by name or email**
- ✅ **Complete employee information** at a glance

### 🔔 Notifications
- ✅ **Real-time alerts** with badge counter
- ✅ **Auto-refresh** every 30 seconds
- ✅ **Leave and correction** notifications
- ✅ **Direct links** to related items

### 🎯 Dashboard Insights
- ✅ **Present vs Absent** split card view
- ✅ **Total employees** count
- ✅ **Pending leaves** summary
- ✅ **Quick actions** for common tasks

### 🔐 Security
- ✅ **Role-based access** (Admin, HR, Employee)
- ✅ **Password hashing**
- ✅ **Face verification** for attendance
- ✅ **Admin-only** face enrollment

---

## 📸 Screenshots

### HR Dashboard
```
┌──────────┬──────────┬──────────┐
│  Total   │ Pre│Abs  │ Pending  │
│Employees │sent│ent  │  Leaves  │
│  (Blue)  │(Gn)│(Red)│ (Yellow) │
└──────────┴──────────┴──────────┘
```

### Employee Directory
- Real-time status badges (Present, Late, Absent, On Leave)
- Filter by department, position, or search name
- Complete employee info: department, position, salary, times

### Payroll Preview
- **Current Period**: Real-time estimate up to today
- **Last Period**: Draft payroll with correction request button
- Detailed breakdown of earnings, deductions, taxes

---

## 🗂️ Project Structure

```
WorkVault/
├── app/
│   ├── models/              # Database models (User, Attendance, Leave, Payroll)
│   ├── routes/              # Application routes (Admin, HR, Employee)
│   └── utils/               # Utilities (Face recognition, Payroll calculator)
├── templates/               # HTML templates
├── static/                  # CSS, JS, face encodings
├── database_schema.sql      # Database structure
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── run.py                  # Application entry point
└── create_admin.py         # Admin creation script
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 📖 Complete setup guide with troubleshooting |
| **[FEATURES.md](FEATURES.md)** | ✨ Detailed feature documentation |
| **[SYSTEM_FLOWCHART.md](SYSTEM_FLOWCHART.md)** | 🏗️ System architecture and workflows |
| **[FINAL_TESTING_CHECKLIST.md](FINAL_TESTING_CHECKLIST.md)** | ✅ Testing guide by role |

---

## 💻 Tech Stack

- **Backend:** Flask (Python)
- **Database:** Supabase (PostgreSQL)
- **Face Recognition:** OpenCV, face_recognition, dlib
- **Frontend:** Bootstrap 5, JavaScript
- **Reports:** openpyxl (Excel)
- **Authentication:** Flask-Login
- **Password Security:** Werkzeug

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```env
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_service_role_key

# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development
```

### Database Tables

The system uses 6 main tables:
- `users` - User accounts (Admin, HR, Employee)
- `attendance` - Clock in/out records
- `attendance_corrections` - Correction requests
- `leaves` - Leave requests and approvals
- `payroll` - Payroll records
- `notifications` - User notifications

Run `database_schema.sql` in Supabase to create all tables.

---

## 🎯 Usage

### For Employees

1. **Clock In/Out** - Face recognition required
2. **View Attendance** - See your attendance history
3. **Request Leave** - Submit leave for approval
4. **Preview Payroll** - Check current and last period estimates
5. **Request Corrections** - Fix attendance errors

### For HR

1. **Employee Directory** - View all employees with real-time status
2. **Manage Leaves** - Approve or reject requests
3. **Manage Corrections** - Review attendance corrections
4. **Generate Payroll** - Create semi-monthly payroll
5. **Export Reports** - Download Excel reports

### For Admin

1. **Manage Users** - Add employees and HR users
2. **Enroll Faces** - Setup face recognition for employees
3. **Full Access** - All HR and employee features
4. **System Management** - User roles and permissions

---

## 🐛 Troubleshooting

### Common Issues

**App won't start?**
- Check `.env` has correct Supabase credentials
- Ensure virtual environment is activated: `venv\Scripts\activate`
- Reinstall dependencies: `pip install -r requirements.txt`

**Face recognition not working?**
- Admin must enroll face first
- Good lighting required
- Camera permissions enabled

**Database connection error?**
- Verify Supabase URL and key in `.env`
- Check Supabase project is active
- Confirm `database_schema.sql` was run

**See [GETTING_STARTED.md](GETTING_STARTED.md#troubleshooting) for detailed troubleshooting.**

---

## 🔒 Security Best Practices

### For Production:

1. **Change SECRET_KEY** to a random 32-byte string
2. **Use strong passwords** (min 8 chars, mixed case, numbers, symbols)
3. **Set FLASK_ENV=production**
4. **Use HTTPS** (not HTTP)
5. **Keep .env secret** (add to .gitignore)
6. **Regular database backups**
7. **Monitor Supabase usage**

---

## 🌟 Highlights

### What Makes WorkVault Special?

✅ **Philippine Payroll Standards** - SSS, PhilHealth, Pag-IBIG, TRAIN Law  
✅ **Face Recognition** - Prevents time theft and buddy punching  
✅ **Real-time Updates** - Live attendance status and notifications  
✅ **Employee Transparency** - Preview payroll before finalization  
✅ **Comprehensive** - All-in-one HR, Attendance, Leave, Payroll  
✅ **Easy Setup** - 30-minute setup with cloud database  
✅ **No Server Needed** - Uses Supabase (free tier available)  
✅ **Excel Reports** - Export payroll and attendance  

---

## 📈 System Capabilities

- **Unlimited employees** (within Supabase limits)
- **Unlimited attendance records**
- **Automatic payroll calculation**
- **Semi-monthly payroll** (Philippine standard)
- **Multiple leave types**
- **Role-based permissions**
- **Real-time notifications**
- **Face recognition** for all employees
- **Excel export** for reports
- **Attendance corrections** workflow

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

[Your License Here]

---

## 👥 Credits

**Developed by:** [Your Name/Team]  
**Date:** June 2026  
**Version:** 1.0

---

## 📞 Support

**Need help?**
1. Check [GETTING_STARTED.md](GETTING_STARTED.md) for setup issues
2. Review [FEATURES.md](FEATURES.md) for feature details
3. See [FINAL_TESTING_CHECKLIST.md](FINAL_TESTING_CHECKLIST.md) for testing
4. Contact system administrator

---

**WorkVault** - Simplifying HR and Payroll Management 🚀

*Made with ❤️ for Philippine businesses*
