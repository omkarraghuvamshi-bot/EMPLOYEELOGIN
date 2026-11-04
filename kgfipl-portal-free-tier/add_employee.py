"""Add an employee to a segment.   python3 add_employee.py
Asks: segment number (1-12), Employee ID, Name, Password."""
import server
server.init()
for n,name,*_ in server.SEGS:print('%2d  %s'%(n,name))
sg=int(input('Segment number: '));ec=input('Employee ID: ').strip().upper();name=input('Name: ').strip();pw=input('Password (min 6 chars): ').strip()
if sg not in server.SN or not ec or not name or len(pw)<6:raise SystemExit('Invalid input - nothing added.')
c=server.sdb(sg)
try:
    c.execute('insert into employees(ecode,name,pw,added,active) values(?,?,?,?,1)',(ec,name,server.ph(pw),server.now().date().isoformat()));c.commit()
    print('Added %s (%s) to segment %d'%(ec,name,sg))
except server.sqlite3.IntegrityError:print('That Employee ID already exists in this segment.')
