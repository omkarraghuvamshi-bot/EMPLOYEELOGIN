KGFIPL EMPLOYEE ATTENDANCE PORTAL - RENDER FREE / LOCAL PACKAGE

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

EMPLOYEE LOGIN FLOW
  The public landing page has an Employee login button.
  Clicking it opens the 12 business segments. Selecting a segment opens that segment's
  employee login form (Employee ID, registered full name and password).
  Employee accounts can only log in to the segment assigned to their employee record.
  Segment cards no longer display the internal HR-1 / HR-2 routing labels. HR staff
  permissions remain enforced internally.
  After login, employees see their attendance screen for their assigned segment only.
  Today's and historical attendance statuses are green for PRESENT and red for ABSENT.
  Attendance still requires a camera photo and device location.

DEMO EMPLOYEE CREDENTIALS
  The bundled demo employees are created in Segment 12 (HR) on first startup:
    KGF001  Ravi Kumar    YFyqpx#17AY
    KGF002  Priya Sharma  8KR3Wj$26qE
    KGF003  Arjun Reddy   GThYXd#21At
    KGF004  Sneha Patil   B5Dkkq!609C
    KGF005  Imran Khan    k2RD84#28G2
  These are sample accounts. Change them before real use.
  Segments 1-11 do not receive fake/demo employee records. HR must add each real employee
  from the Staff / Admin login and issue the employee ID, registered name and password.

STAFF / ADMIN ACCESS
  Staff / Admin login is intentionally hidden from the public landing page. To access it,
  open https://YOUR-RENDER-SERVICE.onrender.com/?staff=1 directly. Replace the domain with
  your actual Render service URL.

  All seeded staff accounts use the temporary password: KGFIPL@2026!
  Staff must set a personal password after their first login.

  Username  Registered name
  HR1       HR - Segments 1 to 8 and 12
  HR2       HR - Segments 9 to 11
  MD        Managing Director
  ACC01     Accounts - Construction, Mining & Wood Work
  ACC02     Accounts - KGFIPL Renewable Energy
  ACC03     Accounts - KGFIPL Manufacturing
  ACC04     Accounts - KGFIPL Agriculture & Farming
  ACC05     Accounts - KGFIPL Electrical & Electronic Equipment Manufacturing
  ACC06     Accounts - KGFIPL Import & Export
  ACC07     Accounts - KGFIPL Financial & Educational Services
  ACC08     Accounts - KGFIPL Security Services & Manpower Supply
  ACC09     Accounts - Hospitality
  ACC10     Accounts - Adventures
  ACC11     Accounts - Courier

  HR can add employees to the segments assigned to that HR account. Accounts users and MD
  retain their existing reports and Excel export functions.

ACCOUNTS STAFF ATTENDANCE
  ACC01 through ACC11 can now also record their own attendance in their assigned segment.
  After Accounts login, the My Attendance panel appears at the top of the assigned segment page.
  Accounts staff use their ACC username as the employee ID and must allow camera and location
  access to complete check-in and check-out. Their attendance is included in segment reports.

LOCAL RUN
  python3 server.py
  Open http://localhost:8000

IMPORTANT FREE-TIER DATA WARNING
  The app uses SQLite and local file storage. Render Free files are ephemeral and may be lost
  after restarts or redeploys. Use only sample/test data on Render Free. Do not store actual
  employee or attendance records until database and photo storage are moved to persistent
  services.
