KGFIPL INTERNAL PORTAL - RENDER FREE / LOCAL PACKAGE

RENDER WEB SERVICE SETTINGS
  Service type: Web Service
  Runtime: Python 3
  Plan: Free
  Build Command: echo "No dependencies to install"
  Start Command: python server.py
  Environment variable: TZ_HOURS=5.5
  Optional environment variable: INITIAL_STAFF_PASSWORD=KGFIPL@2026!
  If you use a different INITIAL_STAFF_PASSWORD, set the same value before first startup.
  Do NOT set DATA_DIR on Render Free. Do NOT add a Persistent Disk.

LOGIN (Employee ID + Password)
  The login page has one form: Employee ID, Name (as listed below) and Password.
  Demo employees (they can open all 12 segments and mark attendance in any of them):
    KGF001  Ravi Kumar    YFyqpx#17AY
    KGF002  Priya Sharma  8KR3Wj$26qE
    KGF003  Arjun Reddy   GThYXd#21At
    KGF004  Sneha Patil   B5Dkkq!609C
    KGF005  Imran Khan    k2RD84#28G2
  These are created on first startup from the DEMO list at the top of server.py. Change them before real use.

SEGMENTS
  12 segments: the original 11 plus 12. HR. Each segment page has its own attendance panel
  (employee ID check, live camera photo, GPS location, login = check-in time, logout = check-out
  time). Attendance is kept separately for each segment: a segment page shows only the records
  marked in that segment, and each segment allows one check-in and one check-out per day.

STAFF ACCOUNTS (not shown on the login page)
  HR1, HR2, MD, ACC01 through ACC11 still work from the same form with the temporary
  password KGFIPL@2026! (they must set a personal password at first login). They keep the
  reports, Excel export and Add employee tools. HR can now set a password for each new employee.

LOCAL RUN
  python3 server.py
  Open http://localhost:8000

IMPORTANT FREE-TIER DATA WARNING
  The app uses SQLite and local file storage. Render Free files are ephemeral and may be lost
  after restarts or redeploys. Use only sample/test data on Render Free. Do not store actual
  employee or attendance records until database and photo storage are moved to persistent
  services.
