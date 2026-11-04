"""KGFIPL internal portal backend. Python 3.8+, no extra packages. Run: python3 server.py

Employees: no login. They open a segment, type Employee ID + Name + Password and press
Present or Leave. The browser sends a live photo + GPS location with it.
Every segment has its OWN database file:  segments/segment_01.db ... segment_12.db
Add employees with:  python3 add_employee.py   (see README.txt)
"""
import sqlite3,json,os,hmac,hashlib,secrets,mimetypes,base64,time
from datetime import datetime,timedelta,timezone
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
B=os.path.dirname(os.path.abspath(__file__))
DATA=os.environ.get('DATA_DIR',B)  # Set to /var/data on Render when using a persistent disk
os.makedirs(DATA,exist_ok=True)
UP=os.path.join(DATA,'uploads');os.makedirs(UP,exist_ok=True)
SD=os.path.join(DATA,'segments');os.makedirs(SD,exist_ok=True)
TZ=timezone(timedelta(hours=float(os.environ.get('TZ_HOURS','5.5'))))  # default India time
now=lambda:datetime.now(TZ)
# (number, name, picture, HR group, one-line description)
SEGS=[(1,'Construction, Mining & Wood Work','construction','HR-1','Building, mining and timber work on site.'),
(2,'KGFIPL Renewable Energy','solar','HR-1','Solar and clean-energy projects.'),
(3,'KGFIPL Manufacturing','manufacturing','HR-1','Factory production and plant operations.'),
(4,'KGFIPL Agriculture & Farming','agri','HR-1','Farming, crops and agricultural produce.'),
(5,'KGFIPL Electrical & Electronic Equipment Manufacturing','electrical','HR-1','Making electrical and electronic equipment.'),
(6,'KGFIPL Import & Export','trade','HR-1','Trading goods to and from other countries.'),
(7,'KGFIPL Financial & Educational Services','finance','HR-1','Finance services and education programmes.'),
(8,'KGFIPL Security Services & Manpower Supply','manpower','HR-1','Security guards and staffing for clients.'),
(9,'Hospitality','hospitality','HR-2','Hotels, stays and guest services.'),
(10,'Adventures','adventure','HR-2','Treks, camps and outdoor experiences.'),
(11,'Courier','courier','HR-2','Parcel pickup and doorstep delivery.'),
(12,'HR','hr','HR-1','People, hiring and employee records.')]
# One demo employee per segment: (Employee ID, Name, Password). Change these before real use.
DEMO={1:('KGF001','Ravi Kumar','Demo@001'),2:('KGF002','Priya Sharma','Demo@002'),3:('KGF003','Arjun Reddy','Demo@003'),4:('KGF004','Sneha Patil','Demo@004'),
5:('KGF005','Imran Khan','Demo@005'),6:('KGF006','Anita Rao','Demo@006'),7:('KGF007','Vikram Singh','Demo@007'),8:('KGF008','Meena Iyer','Demo@008'),
9:('KGF009','Suresh Naik','Demo@009'),10:('KGF010','Kavya Menon','Demo@010'),11:('KGF011','Rahul Das','Demo@011'),12:('KGF012','Divya Nair','Demo@012')}
SN={s[0]:s[1] for s in SEGS}
def sdb(n):  # one separate database file per segment
    c=sqlite3.connect(os.path.join(SD,'segment_%02d.db'%n));c.row_factory=sqlite3.Row;return c
def ph(p,s=None):
    s=s or secrets.token_hex(8);return s+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),120000).hex()
def chk(p,h):return hmac.compare_digest(ph(p,h.split('$')[0]),h)
def init():
    for n in SN:  # create each segment database: employees (id, name, password) + attendance
        c=sdb(n);c.executescript('''create table if not exists employees(ecode text primary key,name text not null,pw text not null,added text,active int default 1);
create table if not exists attendance(id integer primary key autoincrement,date text,ecode text,status text,time text,lat real,lng real,acc real,unique(date,ecode));''')
        if not c.execute('select 1 from employees').fetchone():
            ec,nm_,pw=DEMO[n];c.execute('insert into employees(ecode,name,pw,added,active) values(?,?,?,?,1)',(ec,nm_,ph(pw),now().date().isoformat()))
        c.commit();c.close()
F={}
def blocked(k,lim=8):
    F[k]=[t for t in F.get(k,[]) if t>time.time()-600];return len(F[k])>=lim
nm=lambda v:' '.join(str(v).lower().split())
class H(BaseHTTPRequestHandler):
    def log_message(s,*a):pass
    def out(s,code,body,ct='application/json',fn=None):
        if not isinstance(body,bytes):body=json.dumps(body).encode()
        s.send_response(code);s.send_header('Content-Type',ct);s.send_header('Content-Length',str(len(body)));s.send_header('X-Content-Type-Options','nosniff')
        if fn:s.send_header('Content-Disposition','attachment; filename="%s"'%fn)
        s.end_headers();s.wfile.write(body)
    def who(s,b):
        """Check Employee ID + Name + Password inside one segment. Returns (db, employee, segment) or sends an error and returns None."""
        sg=b.get('seg')
        if sg not in SN:s.out(400,{'error':'Open a business segment first'});return None
        ec=str(b.get('ecode','')).strip().upper();ip=s.client_address[0];k1,k2='a'+ip,'a%s|%d|%s'%(ip,sg,ec)
        c=sdb(sg);e=c.execute('select * from employees where upper(ecode)=? and active=1',(ec,)).fetchone()
        if blocked(k1,40) or blocked(k2) or not e or not chk(str(b.get('password','')),e['pw']) or nm(e['name'])!=nm(b.get('name','')):
            F.setdefault(k1,[]).append(time.time());F.setdefault(k2,[]).append(time.time());c.close()
            s.out(401,{'error':'Wrong employee ID, name or password for this segment'});return None
        return c,e,sg
    def check(s,b):
        """Segment login: after this the page shows the Present / Leave buttons."""
        w=s.who(b)
        if not w:return
        c,e,sg=w;old=c.execute('select status,time from attendance where date=? and ecode=?',(now().date().isoformat(),e['ecode'])).fetchone();c.close()
        return s.out(200,{'name':e['name'],'ecode':e['ecode'],'marked':dict(old) if old else None})
    def mark(s,b):
        """Employee presses Present / Leave. Needs login details + photo + location."""
        st=str(b.get('status','')).lower()
        if st not in('present','leave'):return s.out(400,{'error':'Press Present or Leave'})
        w=s.who(b)
        if not w:return
        c,e,sg=w
        photo=str(b.get('photo',''));lat,lng=b.get('lat'),b.get('lng')
        ok=lambda v,m:isinstance(v,(int,float)) and not isinstance(v,bool) and -m<=v<=m
        if not photo.startswith('data:image/jpeg;base64,') or len(photo)>600000 or not ok(lat,90) or not ok(lng,180):
            c.close();return s.out(400,{'error':'Location and photo are required'})
        raw=base64.b64decode(photo.split(',',1)[1])
        if raw[:2]!=b'\xff\xd8':c.close();return s.out(400,{'error':'Photo is not valid'})
        today=now().date().isoformat();old=c.execute('select status,time from attendance where date=? and ecode=?',(today,e['ecode'])).fetchone()
        if old:c.close();return s.out(400,{'error':'Already marked %s today at %s'%(old['status'].upper(),old['time'])})
        tm=now().strftime('%H:%M:%S')
        try:cur=c.execute('insert into attendance(date,ecode,status,time,lat,lng,acc) values(?,?,?,?,?,?,?)',(today,e['ecode'],st,tm,lat,lng,b.get('acc')))
        except sqlite3.IntegrityError:c.close();return s.out(400,{'error':'Already marked today'})
        open('%s/seg%02d_%d.jpg'%(UP,sg,cur.lastrowid),'wb').write(raw);c.commit();c.close()
        return s.out(200,{'status':st,'time':tm,'date':today,'name':e['name'],'ecode':e['ecode']})
    def go(s,m):
        p=urlparse(s.path).path
        try:
            n=int(s.headers.get('Content-Length') or 0)
            if n>1000000:return s.out(413,{'error':'Too large'})
            body=json.loads(s.rfile.read(n) or b'{}') if m=='POST' else {}
            if p=='/api/segments':return s.out(200,SEGS)
            if p=='/api/check' and m=='POST':return s.check(body)
            if p=='/api/attendance' and m=='POST':return s.mark(body)
            if p.startswith('/api'):return s.out(404,{'error':'Not found'})
            return s.static(p)
        except (ValueError,KeyError,TypeError) as e:return s.out(400,{'error':str(e)})
    def static(s,p):
        f=os.path.normpath(os.path.join(B,'static','index.html' if p=='/' else p[8:] if p.startswith('/static/') else '__no__'))
        if not f.startswith(B+os.sep+'static') or not os.path.isfile(f):return s.out(404,{})
        s.out(200,open(f,'rb').read(),mimetypes.guess_type(f)[0] or 'application/octet-stream')
    do_GET=lambda s:s.go('GET');do_POST=lambda s:s.go('POST')
if __name__=='__main__':
    init();P=int(os.environ.get('PORT','8000'));print('KGFIPL portal running on http://0.0.0.0:%d'%P);ThreadingHTTPServer(('0.0.0.0',P),H).serve_forever()
