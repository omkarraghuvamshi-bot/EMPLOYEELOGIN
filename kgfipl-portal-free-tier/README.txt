KGFIPL INTERNAL PORTAL - RENDER FREE / LOCAL PACKAGE

HOW EMPLOYEES USE IT
  1. First page: one button "Employee Login".
  2. Click it -> all 12 business segments.
  3. Open a segment -> Login with Employee ID, Name and Password (that segment's employees only).
  4. After login -> green "Present" and red "Leave" buttons.
     Press one -> allow location -> allow camera -> photo is taken automatically ->
     attendance saved (Present/Leave, time, GPS location, photo).
     One mark per employee per day in each segment.

DATABASE - ONE PER SEGMENT
  segments/segment_01.db ... segments/segment_12.db  (created automatically on first start)
  Each file has:  employees (Employee ID, Name, Password[hashed])  and  attendance (date, ID, status, time, lat, lng)
  Photos are saved in uploads/ as seg01_<n>.jpg, seg02_<n>.jpg ...
  An employee only works in the segment where he/she was added.

DEMO EMPLOYEES (one per segment - change in server.py, DEMO list, before real use)
  Seg  ID      Name          Password
   1   KGF001  Ravi Kumar    Demo@001
   2   KGF002  Priya Sharma  Demo@002
   3   KGF003  Arjun Reddy   Demo@003
   4   KGF004  Sneha Patil   Demo@004
   5   KGF005  Imran Khan    Demo@005
   6   KGF006  Anita Rao     Demo@006
   7   KGF007  Vikram Singh  Demo@007
   8   KGF008  Meena Iyer    Demo@008
   9   KGF009  Suresh Naik   Demo@009
  10   KGF010  Kavya Menon   Demo@010
  11   KGF011  Rahul Das     Demo@011
  12   KGF012  Divya Nair    Demo@012

ADD MORE EMPLOYEES
  python3 add_employee.py      (Windows: python add_employee.py)
  It asks: segment number, Employee ID, Name, Password.

SEE THE ATTENDANCE DATA
  Open segments/segment_01.db ... segment_12.db with "DB Browser for SQLite" (free),
  table "attendance". Photos are in the uploads/ folder (seg03_1.jpg = segment 3, record 1).

RENDER WEB SERVICE SETTINGS
  Service type: Web Service     Runtime: Python 3     Plan: Free
  Build Command: echo "No dependencies to install"
  Start Command: python server.py
  Environment variable: TZ_HOURS=5.5
  Do NOT set DATA_DIR on Render Free. Do NOT add a Persistent Disk.
  NOTE: camera and location only work on https:// (Render gives https) or localhost.

LOCAL RUN
  python3 server.py
  Open http://localhost:8000

IMPORTANT FREE-TIER DATA WARNING
  The app uses SQLite and local file storage. Render Free files are ephemeral and may be lost
  after restarts or redeploys. Use only sample/test data on Render Free. Do not store actual
  employee or attendance records until database and photo storage are moved to persistent
  services.
