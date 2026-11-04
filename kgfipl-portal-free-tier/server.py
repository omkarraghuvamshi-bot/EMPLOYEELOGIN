"""KGFIPL internal portal backend. Python 3.8+, no extra packages. Run: python3 server.py"""
import sqlite3,json,os,hmac,hashlib,secrets,io,zipfile,mimetypes,base64,time
from datetime import datetime,timedelta,timezone,date
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from xml.sax.saxutils import escape
B=os.path.dirname(os.path.abspath(__file__))
DATA=os.environ.get('DATA_DIR',B)  # Set to /var/data on Render when using a persistent disk
os.makedirs(DATA,exist_ok=True)
UP=os.path.join(DATA,'uploads');os.makedirs(UP,exist_ok=True)
TZ=timezone(timedelta(hours=float(os.environ.get('TZ_HOURS','5.5'))))  # default India time
now=lambda:datetime.now(TZ)
SEGS=[(1,'Construction, Mining & Wood Work','construction','HR-1'),(2,'KGFIPL Renewable Energy','solar','HR-1'),(3,'KGFIPL Manufacturing','manufacturing','HR-1'),(4,'KGFIPL Agriculture & Farming','agri','HR-1'),(5,'KGFIPL Electrical & Electronic Equipment Manufacturing','electrical','HR-1'),(6,'KGFIPL Import & Export','trade','HR-1'),(7,'KGFIPL Financial & Educational Services','finance','HR-1'),(8,'KGFIPL Security Services & Manpower Supply','manpower','HR-1'),(9,'Hospitality','hospitality','HR-2'),(10,'Adventures','adventure','HR-2'),(11,'Courier','courier','HR-2'),(12,'HR','hr','HR-1')]
# Demo employees: sign in with Employee ID + password. Change these before real use.
DEMO=[('KGF001','Ravi Kumar','YFyqpx#17AY'),('KGF002','Priya Sharma','8KR3Wj$26qE'),('KGF003','Arjun Reddy','GThYXd#21At'),('KGF004','Sneha Patil','B5Dkkq!609C'),('KGF005','Imran Khan','k2RD84#28G2')]
SN={s[0]:s[1] for s in SEGS};SG={s[0]:s[3] for s in SEGS}
def db():
    c=sqlite3.connect(os.path.join(DATA,'kgfipl.db'));c.row_factory=sqlite3.Row;return c
def ph(p,s=None):
    s=s or secrets.token_hex(8);return s+'$'+hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),120000).hex()
def chk(p,h):return hmac.compare_digest(ph(p,h.split('$')[0]),h)
def init():
    c=db();c.executescript('''create table if not exists users(username text primary key,name,role,grp,seg,pw);
create table if not exists employees(ecode text primary key,name,phone text unique,seg int,dept,added,active int default 1);
create table if not exists attendance(id integer primary key autoincrement,date,ecode,kind,time,lat,lng,acc,seg int,unique(date,ecode,seg,kind));
create table if not exists sessions(date,ecode,login,logout,primary key(date,ecode));
create table if not exists reports(id integer primary key autoincrement,by,at,dfrom,dto,seg,note);
create table if not exists app_meta(key text primary key,value text not null);''')
    # Safe migration for databases created by an older portal version.
    try:c.execute('alter table users add column force_reset integer not null default 0')
    except sqlite3.OperationalError:pass
    for tbl,col in (('employees','pw text'),('attendance','seg int')):
        try:c.execute('alter table %s add column %s'%(tbl,col))
        except sqlite3.OperationalError:pass
    sql=c.execute("select sql from sqlite_master where name='attendance'").fetchone()[0]
    if 'unique(date,ecode,kind)' in sql:  # older DB: allow one check-in/out per day per segment
        c.executescript('''create table attendance_new(id integer primary key autoincrement,date,ecode,kind,time,lat,lng,acc,seg int,unique(date,ecode,seg,kind));
insert into attendance_new(id,date,ecode,kind,time,lat,lng,acc,seg) select id,date,ecode,kind,time,lat,lng,acc,coalesce(seg,(select seg from employees e where e.ecode=attendance.ecode)) from attendance;
drop table attendance;alter table attendance_new rename to attendance;''')
    for ec,nm,pw in DEMO:
        if not c.execute('select 1 from employees where ecode=?',(ec,)).fetchone():
            c.execute('insert into employees(ecode,name,phone,seg,dept,added,active,pw) values(?,?,?,?,?,?,1,?)',(ec,nm,None,12,'Operations',now().date().isoformat(),ph(pw)))
    common=os.environ.get('INITIAL_STAFF_PASSWORD','KGFIPL@2026!')
    if len(common)<10:raise ValueError('INITIAL_STAFF_PASSWORD must be at least 10 characters')
    marker=c.execute("select value from app_meta where key='common_staff_password_v1'").fetchone()
    if not c.execute('select 1 from users').fetchone():
        L=[('HR1','HR - Segments 1 to 8 and 12','hr','HR-1',None),('HR2','HR - Segments 9 to 11','hr','HR-2',None),('MD','Managing Director','md',None,None)]+[('ACC%02d'%n,'Accounts - '+SN[n],'accounts',None,n) for n in SN if n<12]
        for u,n,r,g,sg in L:
            c.execute('insert into users(username,name,role,grp,seg,pw,force_reset) values(?,?,?,?,?,?,1)',(u,n,r,g,sg,ph(common)))
        c.execute("insert or replace into app_meta(key,value) values('common_staff_password_v1','done')")
        print('Created initial staff accounts. All staff accounts use the temporary common password.',flush=True)
    elif not marker:
        # One-time reset of existing staff accounts so the common password works
        # for users whose database was created by the previous random-password version.
        c.execute('update users set pw=?, force_reset=1',(ph(common),))
        c.execute("insert into app_meta(key,value) values('common_staff_password_v1','done')")
        print('Existing staff accounts have been reset to the temporary common password.',flush=True)
    # Make each Accounts staff account a reportable attendance identity as well.
    # Keep pw NULL so authentication continues to use the staff account in users.
    for a in c.execute("select username,name,seg from users where role='accounts' and seg is not null").fetchall():
        c.execute("insert or ignore into employees(ecode,name,phone,seg,dept,added,active,pw) values(?,?,NULL,?,'Accounts',?,1,NULL)",
                  (a['username'],a['name'],int(a['seg']),now().date().isoformat()))
        c.execute("update employees set name=?,seg=?,dept='Accounts',active=1,pw=NULL where ecode=?",
                  (a['name'],int(a['seg']),a['username']))
    pending=c.execute('select username from users where force_reset=1 order by username').fetchall()
    if pending:
        print('\n========== TEMPORARY STAFF LOGIN ==========',flush=True)
        print('Usernames: '+', '.join(r['username'] for r in pending),flush=True)
        print('Common temporary password: '+common,flush=True)
        print('Each staff member must set a personal password at first login.',flush=True)
        print('===========================================\n',flush=True)
    c.commit();c.close()
TOK={};F={}
def blocked(k):
    F[k]=[t for t in F.get(k,[]) if t>time.time()-600];return len(F[k])>=8
def D(v):return ''.join(ch for ch in str(v) if ch.isdigit())[-10:]
def z(v):return str(v).lstrip('0')
def maplink(r):return 'https://www.google.com/maps?q=%s,%s'%(r['lat'],r['lng']) if r else ''
def rows(f,t,segs,ecode=None):
    d0,d1=date.fromisoformat(f),date.fromisoformat(t)
    if d1<d0 or (d1-d0).days>92:raise ValueError('Choose a date range of up to 92 days')
    c=db()
    emps=c.execute('select * from employees where active=1 order by seg,dept,ecode').fetchall()
    hs={e['ecode']:e['seg'] for e in emps};att={};day={}
    for r in c.execute('select * from attendance where date between ? and ?',(f,t)):
        sg=r['seg'] or hs.get(r['ecode']);att[(r['date'],r['ecode'],sg,r['kind'])]=r;day.setdefault((r['date'],r['ecode']),set()).add(sg)
    ses={(r['date'],r['ecode']):r for r in c.execute('select * from sessions where date between ? and ?',(f,t))}
    out=[];d=d0
    while d<=d1:
        ds=d.isoformat()
        for e in emps:
            if ds<e['added'] or (ecode and e['ecode']!=ecode):continue
            s=ses.get((ds,e['ecode']))
            for rs in sorted(day.get((ds,e['ecode'])) or {e['seg']}):
                if rs not in segs:continue
                i,o=att.get((ds,e['ecode'],rs,'in')),att.get((ds,e['ecode'],rs,'out'))
                out.append(dict(date=ds,seg=rs,segname=SN[rs],dept=e['dept'],ecode=e['ecode'],name=e['name'],phone=e['phone'] or '',login=s['login'] if s else '',logout=(s['logout'] or '') if s else '',tin=i['time'] if i else '',tout=o['time'] if o else '',mapin=maplink(i),mapout=maplink(o),pin=i['id'] if i else None,pout=o['id'] if o else None,status='Present' if i else 'Absent'))
        d+=timedelta(1)
    return out
def xlsx(sheets):
    b=io.BytesIO();Z=zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED);n=list(sheets);ns='http://schemas.openxmlformats.org/'
    Z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="%spackage/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>%s</Types>'%(ns,''.join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'%(i+1) for i in range(len(n)))))
    Z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="%spackage/2006/relationships"><Relationship Id="rId1" Type="%sofficeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'%(ns,ns))
    Z.writestr('xl/workbook.xml','<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="%sspreadsheetml/2006/main" xmlns:r="%sofficeDocument/2006/relationships"><sheets>%s</sheets></workbook>'%(ns,ns,''.join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>'%(escape(k)[:31],i+1,i+1) for i,k in enumerate(n))))
    Z.writestr('xl/_rels/workbook.xml.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="%spackage/2006/relationships">%s</Relationships>'%(ns,''.join('<Relationship Id="rId%d" Type="%sofficeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'%(i+1,ns,i+1) for i in range(len(n)))))
    for i,k in enumerate(n):
        x=''
        for r,row in enumerate(sheets[k],1):
            x+='<row r="%d">'%r+''.join(('<c r="%s%d"><v>%s</v></c>'%(chr(65+j),r,v) if isinstance(v,(int,float)) else '<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>'%(chr(65+j),r,escape(str(v)))) for j,v in enumerate(row))+'</row>'
        Z.writestr('xl/worksheets/sheet%d.xml'%(i+1),'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="%sspreadsheetml/2006/main"><sheetData>%s</sheetData></worksheet>'%(ns,x))
    Z.close();return b.getvalue()
def book(f,t,segs):
    R=rows(f,t,segs);H=['Date','Segment','Department','Emp code','Name','Phone','Portal login','Portal logout','Attendance in','In location','Attendance out','Out location','Status']
    S={}
    for r in R:
        k=(r['seg'],r['dept']);a=S.setdefault(k,[0,0]);a[0 if r['status']=='Present' else 1]+=1
    return xlsx({'Summary':[['Report %s to %s'%(f,t)],['Segment','Department','Present days','Absent days']]+[[SN[k[0]],k[1],v[0],v[1]] for k,v in sorted(S.items())],
      'Details':[H]+[[r['date'],r['segname'],r['dept'],r['ecode'],r['name'],r['phone'],r['login'],r['logout'],r['tin'],r['mapin'],r['tout'],r['mapout'],r['status']] for r in R]})
def segs_of(u,q):
    s=[u['seg']] if u['role']=='accounts' else list(SN)
    if q.get('seg',[''])[0].isdigit():s=[x for x in s if x==int(q['seg'][0])]
    return s
class H(BaseHTTPRequestHandler):
    def log_message(s,*a):pass
    def out(s,code,body,ct='application/json',fn=None):
        if not isinstance(body,bytes):body=json.dumps(body).encode()
        s.send_response(code);s.send_header('Content-Type',ct);s.send_header('Content-Length',str(len(body)));s.send_header('X-Content-Type-Options','nosniff')
        if fn:s.send_header('Content-Disposition','attachment; filename="%s"'%fn)
        s.end_headers();s.wfile.write(body)
    def go(s,m):
        u=urlparse(s.path);p=u.path;q=parse_qs(u.query)
        try:
            n=int(s.headers.get('Content-Length') or 0);body=json.loads(s.rfile.read(n) or b'{}') if m=='POST' else {}
            if not p.startswith('/api') and not p.startswith('/photo'):return s.static(p)
            t=(s.headers.get('Authorization') or '')[7:] or q.get('t',[''])[0];U=TOK.get(t)
            if U and U['exp']<time.time():U=None
            c=db()
            if p=='/api/segments' and m=='GET':
                return s.out(200,SEGS)
            if p=='/api/login' and m=='POST':
                uid=str(body.get('username','')).strip().upper();pw=str(body.get('password',''));k='l'+s.client_address[0]+uid
                e=c.execute('select * from employees where upper(ecode)=? and active=1 and pw is not null',(uid,)).fetchone()
                r=None if e else c.execute('select * from users where username=?',(uid,)).fetchone()
                row=e or r
                nm=lambda v:' '.join(str(v).lower().split())
                requested_seg=body.get('segment')
                try: requested_seg=int(requested_seg) if requested_seg not in (None,'') else None
                except (TypeError,ValueError): requested_seg=None
                if blocked(k) or not row or not chk(pw,row['pw']) or (e and nm(e['name'])!=nm(body.get('name',''))) or (e and requested_seg!=int(e['seg'])):
                    F.setdefault(k,[]).append(time.time())
                    if e and requested_seg!=int(e['seg']):return s.out(401,{'error':'This employee account is not assigned to the selected segment'})
                    return s.out(401,{'error':'Wrong employee ID, name or password'})
                if e:
                    U=dict(role='emp',id=e['ecode'],name=e['name'],seg=e['seg'],ecode=e['ecode'])
                    c.execute('insert into sessions values(?,?,?,null) on conflict(date,ecode) do update set logout=null',(now().date().isoformat(),e['ecode'],now().strftime('%H:%M:%S')));c.commit()
                else:
                    U=dict(role=r['role'],id=r['username'],name=r['name'],grp=r['grp'],seg=r['seg'],
                           ecode=r['username'] if r['role']=='accounts' else None,
                           must_reset=bool(r['force_reset']))
                    if r['role']=='accounts':
                        c.execute('insert into sessions values(?,?,?,null) on conflict(date,ecode) do update set logout=null',
                                  (now().date().isoformat(),r['username'],now().strftime('%H:%M:%S')))
                        c.commit()
            if p=='/api/login':
                t=secrets.token_urlsafe(24);U['exp']=time.time()+43200;TOK[t]=U
                return s.out(200,{'token':t,'user':{k:v for k,v in U.items() if k!='exp'},'segments':SEGS})
            if not U:return s.out(401,{'error':'Please sign in'})
            R=U['role'];today=now().date().isoformat()
            if p=='/api/password/change' and m=='POST':
                if R not in ('hr','md','accounts'):return s.out(403,{'error':'Staff accounts only'})
                new_password=str(body.get('new_password',''))
                if len(new_password)<10:return s.out(400,{'error':'New password must be at least 10 characters'})
                row=c.execute('select pw,force_reset from users where username=?',(U['id'],)).fetchone()
                if not row:return s.out(404,{'error':'Staff account not found'})
                if not bool(row['force_reset']) and not chk(str(body.get('current_password','')),row['pw']):
                    return s.out(400,{'error':'Current password is incorrect'})
                c.execute('update users set pw=?,force_reset=0 where username=?',(ph(new_password),U['id']))
                c.commit();U['must_reset']=False
                return s.out(200,{'ok':True})
            if U.get('must_reset') and p!='/api/logout':
                return s.out(403,{'error':'Please set your personal password before continuing','must_reset':True})
            if p=='/api/logout':
                if R in ('emp','accounts'):c.execute('update sessions set logout=? where date=? and ecode=?',(now().strftime('%H:%M:%S'),today,U['ecode']));c.commit()
                TOK.pop(t,None);return s.out(200,{})
            if p=='/api/me/history' and R in ('emp','accounts'):
                return s.out(200,rows((now()-timedelta(14)).date().isoformat(),today,[int(U['seg'])],U['ecode']))
            if p=='/api/attendance' and m=='POST' and R in ('emp','accounts'):
                entered=str(body.get('ecode','')).strip().upper()
                expected=str(U['ecode']).upper()
                if (entered!=expected if R=='accounts' else z(entered)!=z(expected)):
                    return s.out(400,{'error':'Wrong employee ID'})
                try:sg=int(body.get('seg',0))
                except (TypeError,ValueError):sg=0
                if sg not in SN or sg!=int(U['seg']):return s.out(400,{'error':'You can only mark attendance in your assigned segment'})
                ph_=str(body.get('photo',''));lat,lng=body.get('lat'),body.get('lng')
                if not ph_.startswith('data:image/jpeg;base64,') or len(ph_)>600000 or not isinstance(lat,(int,float)) or not isinstance(lng,(int,float)):return s.out(400,{'error':'Location and photo are required'})
                have={r['kind'] for r in c.execute('select kind from attendance where date=? and ecode=? and seg=?',(today,U['ecode'],sg))}
                kind='in' if 'in' not in have else 'out' if 'out' not in have else None
                if not kind:return s.out(400,{'error':'Attendance for this segment is already complete today'})
                cur=c.execute('insert into attendance(date,ecode,kind,time,lat,lng,acc,seg) values(?,?,?,?,?,?,?,?)',(today,U['ecode'],kind,now().strftime('%H:%M:%S'),lat,lng,body.get('acc'),sg))
                open('%s/att_%d.jpg'%(UP,cur.lastrowid),'wb').write(base64.b64decode(ph_.split(',',1)[1]));c.commit();return s.out(200,{'kind':kind})
            if p.startswith('/photo/'):
                i=int(p[7:].split('.')[0]);r=c.execute('select * from attendance where id=?',(i,)).fetchone()
                e=c.execute('select seg from employees where ecode=?',(r['ecode'],)).fetchone() if r else None
                if not r or (R=='emp' and r['ecode']!=U['ecode']) or (R=='accounts' and (r['seg'] or (e['seg'] if e else None))!=U['seg']):return s.out(404,{})
                return s.out(200,open('%s/att_%d.jpg'%(UP,i),'rb').read(),'image/jpeg')
            if R=='emp':return s.out(403,{'error':'Not allowed'})
            if p=='/api/employees':
                if m=='POST':
                    sg=int(body.get('seg',0))
                    if R!='hr' or SG.get(sg)!=U['grp']:return s.out(403,{'error':'You can only add employees in your own segments'})
                    nm,phn,dp=str(body.get('name','')).strip(),D(body.get('phone')) or None,body.get('dept')
                    if not nm or (phn and len(phn)<10) or dp not in('Operations','Accounts'):return s.out(400,{'error':'Enter name and department (phone, if given, must be 10 digits)'})
                    npw=str(body.get('password','')).strip() or secrets.token_urlsafe(9)
                    if len(npw)<8:return s.out(400,{'error':'Password must be at least 8 characters'})
                    ec=str(body.get('ecode','')).strip()
                    if not ec:ec='%03d'%(max([int(r[0]) for r in c.execute('select ecode from employees') if r[0].isdigit()]+[0])+1)
                    try:c.execute('insert into employees(ecode,name,phone,seg,dept,added,active,pw) values(?,?,?,?,?,?,1,?)',(ec,nm,phn,sg,dp,today,ph(npw)));c.commit()
                    except sqlite3.IntegrityError:return s.out(400,{'error':'Phone number or employee code already registered'})
                    return s.out(200,{'ecode':ec,'password':npw})
                sg=segs_of(U,q);return s.out(200,[dict(r) for r in c.execute('select ecode,name,phone,seg,dept from employees where active=1 and seg in (%s) order by seg,ecode'%','.join('?'*len(sg)),sg)])
            f,tt=q.get('from',[today])[0],q.get('to',[today])[0]
            if p=='/api/report':return s.out(200,rows(f,tt,segs_of(U,q)))
            if p=='/api/export.xlsx':return s.out(200,book(f,tt,segs_of(U,q)),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','KGFIPL_attendance_%s_to_%s.xlsx'%(f,tt))
            if p=='/api/reports' and R in('hr','md'):
                if m=='POST':
                    if R!='hr':return s.out(403,{'error':'Only HR can send reports'})
                    sg=segs_of(U,{'seg':[str(body.get('seg',''))]});f,tt=body.get('from',today),body.get('to',today)
                    cur=c.execute('insert into reports(by,at,dfrom,dto,seg,note) values(?,?,?,?,?,?)',(U['name'],now().strftime('%Y-%m-%d %H:%M'),f,tt,body.get('seg') or 'All',str(body.get('note',''))[:500]))
                    open('%s/report_%d.xlsx'%(UP,cur.lastrowid),'wb').write(book(f,tt,sg));c.commit();return s.out(200,{'id':cur.lastrowid})
                return s.out(200,[dict(r) for r in c.execute('select * from reports order by id desc limit 50')])
            if p.startswith('/api/reports/') and R in('hr','md'):
                i=int(p[13:].split('.')[0]);return s.out(200,open('%s/report_%d.xlsx'%(UP,i),'rb').read(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','KGFIPL_report_%d.xlsx'%i)
            return s.out(404,{'error':'Not found'})
        except (ValueError,KeyError,TypeError) as e:return s.out(400,{'error':str(e)})
    def static(s,p):
        f=os.path.normpath(os.path.join(B,'static','index.html' if p=='/' else p[8:] if p.startswith('/static/') else '__no__'))
        if not f.startswith(B+os.sep+'static') or not os.path.isfile(f):return s.out(404,{})
        s.out(200,open(f,'rb').read(),mimetypes.guess_type(f)[0] or 'application/octet-stream')
    do_GET=lambda s:s.go('GET');do_POST=lambda s:s.go('POST')
if __name__=='__main__':
    init();P=int(os.environ.get('PORT','8000'));print('KGFIPL portal running on http://0.0.0.0:%d'%P);ThreadingHTTPServer(('0.0.0.0',P),H).serve_forever()
