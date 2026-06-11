# 📊 WorkVault System Flowchart

## Overview
This document provides visual flowcharts for all major workflows in the WorkVault HR & Payroll System.

---

## 1. 👤 Employee Daily Attendance Flow

```
START (Employee arrives at work)
    ↓
Go to "Clock In" page
📁 routes/employee.py: clock_in() [GET]
📁 templates/employee/clock_in.html
    ↓
[Face Recognition - Camera Capture]
📁 static/js/main.js: Camera API
    ↓
Submit Image to Server [POST]
📁 routes/employee.py: clock_in() [POST]
    ↓
Verify Face
📁 utils/face_recognition_utils.py: verify_face()
    ↓
┌─────────────────────────┐
│  Face Verified?         │
└─────────────────────────┘
    ↓ YES                    ↓ NO
    ↓                        ↓
Check 6 AM Reset        Return Error
📁 models/attendance.py     "Face verification failed"
Attendance.clock_in()       ↓
    ↓                      END
┌─────────────────────────┐
│  Is it after 6:00 AM    │
│  AND no clock in today? │
│  (lines 29-48)          │
└─────────────────────────┘
    ↓ YES                    ↓ NO
    ↓                        ↓
Check if Late           Return Error
(>8:10 AM grace)       "Already clocked in"
line 51                     ↓
    ↓                      END
Save to Database
supabase.table('attendance')
.insert(data)
lines 53-62
    ↓
✅ Clock In Success
Return time_in, status
    ↓
[Work throughout day]
    ↓
Go to "Clock Out" page
📁 routes/employee.py: clock_out() [POST]
    ↓
[Face Recognition]
📁 utils/face_recognition_utils.py: verify_face()
    ↓
Clock Out
📁 models/attendance.py: Attendance.clock_out()
    ↓
Save clock_out timestamp
supabase.table('attendance')
.update({'clock_out': now})
lines 80-90
    ↓
Calculate Overtime
(if clock_out > 5:00 PM)
Done in payroll calculation
    ↓
✅ Clock Out Success
    ↓
END
```

---

## 2. 📝 Attendance Correction Request Flow

```
START (Employee notices missing/wrong attendance)
    ↓
Go to "My Attendance Corrections"
📁 routes/attendance_corrections.py: my_requests() [GET]
📁 templates/attendance_corrections/my_requests.html
    ↓
Click "Request Correction"
📁 routes/attendance_corrections.py: request_correction() [GET]
📁 templates/attendance_corrections/request.html
    ↓
Select Correction Type:
├─→ Missing Day
├─→ Missing Clock Out
└─→ Wrong Time
    ↓
Fill in Details:
- Date
- Clock In Time
- Clock Out Time
- Reason
    ↓
Submit Request [POST]
📁 routes/attendance_corrections.py: request_correction() [POST]
    ↓
Create Correction Record
📁 models/attendance_correction.py: AttendanceCorrection.create()
supabase.table('attendance_corrections').insert(data)
lines 29-59
    ↓
Status = PENDING
    ↓
Notify HR (notification)
📁 models/notification.py: Notification.create()
    ↓
[HR Review Process]
📁 routes/attendance_corrections.py: manage() [GET]
📁 templates/attendance_corrections/manage.html
    ↓
HR Clicks Approve/Reject
📁 routes/attendance_corrections.py: approve_correction() [POST]
    ↓
┌──────────────────┐
│  HR Approves?    │
└──────────────────┘
    ↓ YES                           ↓ NO
    ↓                               ↓
Execute approve()              Execute reject()
📁 models/attendance_           📁 models/attendance_
correction.py: approve()        correction.py: reject()
lines 111-400                   lines 402-425
    ↓                               ↓
Status = APPROVED              Status = REJECTED
    ↓                               ↓
Update/Create Attendance       Update correction status
(add/fix clock in/out)         supabase.table(
supabase.table('attendance')   'attendance_corrections')
.insert() or .update()         .update({'status':'rejected'})
lines 126-254                       ↓
    ↓                          Notify Employee
Check correction type          📁 models/notification.py
lines 267-281                       ↓
    ↓                              END
should_create_payroll = True
    ↓
Create SEPARATE Payroll
📁 models/attendance_correction.py
lines 283-397
    ↓
Calculate 1-day payroll
📁 utils/ph_payroll_calculator.py
PHPayrollCalculator.calculate_semi_monthly_payroll(
    worked_days=1
)
    ↓
Insert NEW payroll record
supabase.table('payroll').insert({
    'period_start': attendance_date,
    'period_end': attendance_date,  # Same date!
    'days_present': 1,
    'status': 'draft'
})
lines 390-397
    ↓
✅ Separate Payroll Created
    ↓
Notify Employee
📁 models/notification.py
    ↓
END
```


---

## 3. 💰 Payroll Generation Flow (HR)

```
START (HR needs to generate payroll)
    ↓
Go to "Payroll Management"
    ↓
Click "Generate Payroll"
    ↓
Select Date Range:
- Period Start (e.g., May 16)
- Period End (e.g., May 31)
    ↓
Select Employees
(check boxes)
    ↓
Click "Generate Payroll"
    ↓
For Each Employee:
    ↓
Check if payroll exists
for this period
    ↓ EXISTS              ↓ NO
    ↓                     ↓
Show Error            Get Attendance Records
"Already exists"      (period start to end)
    ↓                     ↓
END                   Count Days:
                      - Present (completed: clock in + out)
                      - Absent
                      - On Leave
                          ↓
                      Calculate Tardiness
                      (late minutes × per-minute rate)
                          ↓
                      Calculate Overtime
                      (OT hours × 1.25 × hourly rate)
                          ↓
                      Calculate Deductions:
                      - SSS (5%, max ₱1,500)
                      - PhilHealth (2.5%, max ₱2,500)
                      - Pag-IBIG (1-2%, max ₱100)
                      - Withholding Tax (TRAIN Law)
                          ↓
                      Calculate Net Pay:
                      Gross - Total Deductions
                          ↓
                      Save Payroll Record
                      Status = DRAFT
                          ↓
                      END
```


---

## 4. 🔄 Payroll Status Lifecycle

```
┌──────────────┐
│    DRAFT     │ ← Payroll just generated
└──────────────┘
      ↓
HR reviews details
      ↓
HR clicks "Finalize"
      ↓
┌──────────────┐
│  FINALIZED   │ ← Locked, ready to pay
└──────────────┘
      ↓
HR reviews again
      ↓
HR clicks "Release to Employee"
      ↓
┌──────────────┐
│  PAID        │ ← Employee can see & download
└──────────────┘
      ↓
Employee gets notification
      ↓
Employee views payslip
      ↓
Employee downloads Excel
      ↓
END
```

---

## 5. 🗑️ Payroll Deletion & Regeneration Flow

```
START (Payroll has wrong data)
    ↓
HR goes to "Payroll Management"
    ↓
Finds incorrect payroll record
    ↓
Clicks red "Delete" button
    ↓
Confirms deletion
    ↓
Payroll deleted from database
    ↓
Click "Generate Payroll"
    ↓
Select same date range
    ↓
Select same employees
    ↓
Generate with updated attendance
    ↓
New payroll has correct data
    ↓
END
```


---

## 6. 🏖️ Leave Request Flow

```
START (Employee needs leave)
    ↓
Go to "Request Leave"
    ↓
Fill Leave Form:
- Leave Type (Sick/Vacation/etc.)
- Start Date
- End Date
- Days Count
- Reason
    ↓
Submit Request
    ↓
Status = PENDING
    ↓
Notify HR
    ↓
[HR Reviews Request]
    ↓
┌──────────────────┐
│  HR Approves?    │
└──────────────────┘
    ↓ YES                    ↓ NO
    ↓                        ↓
Status = APPROVED       Status = REJECTED
    ↓                        ↓
Mark dates as           Notify Employee
"On Leave" in               ↓
attendance                 END
    ↓
Notify Employee
(with notification)
    ↓
Employee sees
approved leave
    ↓
Days counted as
paid in payroll
    ↓
END
```

---

## 7. 🔔 Notification System Flow

```
Event Occurs:
├─→ Leave Approved
├─→ Leave Rejected
├─→ Payroll Released
└─→ Attendance Correction Approved
    ↓
Create Notification:
- User ID (recipient)
- Title
- Message
- Type (success/error/info)
- Link (to relevant page)
    ↓
Save to Database
    ↓
[User's Browser]
    ↓
Auto-refresh every 10 seconds
    ↓
Check unread notifications
    ↓
┌─────────────────────┐
│  Any unread?        │
└─────────────────────┘
    ↓ YES                    ↓ NO
    ↓                        ↓
Show badge count        Hide badge
(red number)                ↓
    ↓                      END
User clicks bell icon
    ↓
Show notification list
    ↓
User clicks notification
    ↓
Mark as read
    ↓
Navigate to link
    ↓
END
```

---

## 8. 📊 Complete Payroll Workflow (End-to-End)

```
┌─────────────────────────────────────────────────────────┐
│                    PAYROLL PERIOD                       │
│                  (May 16-31, 2026)                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              EMPLOYEES WORK & CLOCK IN/OUT              │
│  May 16: Clock in 8:00 AM, Clock out 5:00 PM          │
│  May 17: Clock in 8:15 AM (late), Clock out 6:00 PM   │
│  May 18: Forgot to clock in ❌                         │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               PERIOD ENDS (May 31)                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│           HR GENERATES PAYROLL (June 1)                │
│  - Counts completed days (9 days)                      │
│  - Calculates tardiness, OT                            │
│  - Calculates deductions (SSS, PhilHealth, etc.)       │
│  - Status: DRAFT                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              HR REVIEWS & FINALIZES                     │
│  Status: DRAFT → FINALIZED                             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│          HR RELEASES PAYROLL (June 5)                  │
│  Status: FINALIZED → PAID                              │
│  Employee gets notification                            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│        EMPLOYEE NOTICES MISSING DAY (May 18)           │
│  Requests attendance correction                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│           HR APPROVES CORRECTION (June 6)              │
│  - Attendance updated (May 18 marked present)          │
│  - SEPARATE payroll created:                           │
│    * Period: May 18 to May 18 (1 day)                 │
│    * Net Pay: ₱113.08                                  │
│    * Status: DRAFT                                     │
│  - Original payroll UNCHANGED                          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│       HR FINALIZES & RELEASES CORRECTION PAY           │
│  Status: DRAFT → FINALIZED → PAID                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│     EMPLOYEE RECEIVES SUPPLEMENTAL PAYMENT             │
│  Original: ₱3,581.61 (9 days)                         │
│  Correction: ₱113.08 (1 day)                          │
│  Total: ₱3,694.69                                      │
└─────────────────────────────────────────────────────────┘
                            ↓
                           END
```


---

## 9. 🔐 User Authentication & Role Flow

```
START (User opens app)
    ↓
Login Page
    ↓
Enter Credentials:
- Email
- Password
    ↓
Authenticate
    ↓
┌──────────────────┐
│  Valid Login?    │
└──────────────────┘
    ↓ NO                     ↓ YES
    ↓                        ↓
Show Error              Check Role
Back to Login               ↓
    ↓                  ┌────────────┐
   END                 │    Role?   │
                       └────────────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
    [ADMIN]            [HR]              [EMPLOYEE]
        ↓                   ↓                   ↓
Admin Dashboard     HR Dashboard      Employee Dashboard
        ↓                   ↓                   ↓
Can access:         Can access:       Can access:
- All employees     - Attendance      - Clock In/Out
- All HR users      - Leaves          - My Attendance
- Face enrollment   - Payroll         - My Leaves
- All attendance    - Corrections     - My Payroll
- All leaves        - Reports         - Corrections
- All payroll       - Notifications   - Notifications
        ↓                   ↓                   ↓
       END                 END                 END
```

---

## 10. 📈 System Data Relationships

```
┌──────────┐
│  USERS   │
└──────────┘
     │
     │ (1:many)
     ├──────────────────────────────────┐
     ↓                                  ↓
┌────────────┐                   ┌──────────┐
│ ATTENDANCE │                   │  LEAVES  │
└────────────┘                   └──────────┘
     │                                  │
     │ (1:many)                        │
     ↓                                  │
┌─────────────────────┐                │
│ ATTENDANCE          │                │
│ CORRECTIONS         │                │
└─────────────────────┘                │
     │                                  │
     └──────────────┬───────────────────┘
                    ↓
             ┌──────────┐
             │ PAYROLL  │
             └──────────┘
                    │
                    │ (1:many)
                    ↓
           ┌────────────────┐
           │ NOTIFICATIONS  │
           └────────────────┘
```

---

## Key Features Summary

### ✅ Implemented
- Face recognition clock in/out
- 6 AM daily clock in reset
- Tardiness calculation (10-min grace)
- Overtime calculation (1.25x rate)
- Philippine payroll (SSS, PhilHealth, Pag-IBIG, Tax)
- Semi-monthly payroll periods
- Attendance correction requests
- Separate correction payroll
- Leave management
- Notification system
- Excel payroll exports
- Payroll delete & regenerate
- Role-based access control

### 📝 Notes
- Payroll only counts completed days (with clock out)
- Corrections create separate 1-day payroll records
- Original payroll stays unchanged when corrections approved
- HR can delete and regenerate payroll anytime
- All payroll follows Philippine labor standards

