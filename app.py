from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','masar-altamayuz-2026')
DB = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'masar.db'))
ADMIN_CODE = os.environ.get('ADMIN_CODE','منصة إبداعية')

STAGES = [
    ('الانطلاقة','📖',5),('الاستكشاف','🔎',10),('المعرفة','💡',15),
    ('الإنجاز','🎯',20),('التميز','⭐',25),('الريادة','🏆',None)
]

def db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def init_db():
    con=db(); cur=con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,class_name TEXT NOT NULL,phone TEXT DEFAULT '',leadership INTEGER DEFAULT 0,created_at TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,title TEXT NOT NULL,author TEXT DEFAULT '',benefit TEXT DEFAULT '',rating INTEGER DEFAULT 5,status TEXT DEFAULT 'pending',created_at TEXT NOT NULL,FOREIGN KEY(student_id) REFERENCES students(id))''')
    con.commit(); con.close()

@app.context_processor
def inject(): return dict(stages=STAGES)

def student_stats(sid):
    con=db(); approved=con.execute("SELECT COUNT(*) c FROM books WHERE student_id=? AND status='approved'",(sid,)).fetchone()['c']; con.close()
    points=approved*10  # 10 عملات لكل كتاب معتمد
    if approved>=25: current='التميز'
    elif approved>=20: current='الإنجاز'
    elif approved>=15: current='المعرفة'
    elif approved>=10: current='الاستكشاف'
    else: current='الانطلاقة'
    within=approved%5 if approved<25 else 5
    return approved,points,current,within

@app.route('/')
def home():
    con=db(); students=con.execute('SELECT * FROM students ORDER BY name').fetchall(); con.close()
    selected=None; stats=(0,0,'الانطلاقة',0); recent=[]
    sid=request.args.get('student_id',type=int)
    if sid:
        con=db(); selected=con.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone(); recent=con.execute('SELECT * FROM books WHERE student_id=? ORDER BY id DESC LIMIT 5',(sid,)).fetchall(); con.close()
        if selected: stats=student_stats(sid)
    return render_template('index.html',students=students,selected=selected,stats=stats,recent=recent)

@app.post('/submit-book')
def submit_book():
    sid=request.form.get('student_id',type=int); title=request.form.get('title','').strip(); author=request.form.get('author','').strip(); benefit=request.form.get('benefit','').strip(); rating=request.form.get('rating',5,type=int)
    if not sid or not title: flash('اختاري الطالبة واكتبي عنوان الكتاب.','error'); return redirect(url_for('home',student_id=sid or ''))
    con=db(); con.execute('INSERT INTO books(student_id,title,author,benefit,rating,status,created_at) VALUES(?,?,?,?,?,?,?)',(sid,title,author,benefit,max(1,min(rating,5)),'pending',datetime.now().strftime('%Y-%m-%d %H:%M'))); con.commit(); con.close()
    flash('تم إرسال الكتاب بنجاح، وهو الآن بانتظار الاعتماد ✨','ok'); return redirect(url_for('home',student_id=sid))

@app.post('/admin-login')
def admin_login():
    if request.form.get('code','')==ADMIN_CODE: session['admin']=True; return redirect(url_for('admin'))
    flash('رمز الدخول غير صحيح.','error'); return redirect(url_for('home'))

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect(url_for('home'))
    con=db(); students=con.execute('SELECT * FROM students ORDER BY name').fetchall(); pending=con.execute('''SELECT books.*,students.name,students.class_name FROM books JOIN students ON students.id=books.student_id WHERE books.status='pending' ORDER BY books.id DESC''').fetchall(); con.close()
    return render_template('admin.html',students=students,pending=pending)

@app.post('/admin/student/add')
def add_student():
    if not session.get('admin'): return redirect(url_for('home'))
    name=request.form.get('name','').strip(); cls=request.form.get('class_name','').strip(); phone=request.form.get('phone','').strip()
    if name and cls:
        con=db(); con.execute('INSERT INTO students(name,class_name,phone,created_at) VALUES(?,?,?,?)',(name,cls,phone,datetime.now().strftime('%Y-%m-%d'))); con.commit(); con.close(); flash('تمت إضافة الطالبة.','ok')
    return redirect(url_for('admin'))

@app.post('/admin/student/<int:sid>/edit')
def edit_student(sid):
    if not session.get('admin'): return redirect(url_for('home'))
    con=db(); con.execute('UPDATE students SET name=?,class_name=?,phone=? WHERE id=?',(request.form.get('name','').strip(),request.form.get('class_name','').strip(),request.form.get('phone','').strip(),sid)); con.commit(); con.close(); return redirect(url_for('admin'))

@app.post('/admin/student/<int:sid>/delete')
def delete_student(sid):
    if not session.get('admin'): return redirect(url_for('home'))
    con=db(); con.execute('DELETE FROM books WHERE student_id=?',(sid,)); con.execute('DELETE FROM students WHERE id=?',(sid,)); con.commit(); con.close(); return redirect(url_for('admin'))

@app.post('/admin/book/<int:bid>/<action>')
def book_action(bid,action):
    if not session.get('admin'): return redirect(url_for('home'))
    if action in ('approved','rejected'):
        con=db(); con.execute('UPDATE books SET status=? WHERE id=?',(action,bid)); con.commit(); con.close()
    return redirect(url_for('admin'))

@app.post('/admin/student/<int:sid>/leadership')
def leadership(sid):
    if not session.get('admin'): return redirect(url_for('home'))
    approved,_,_,_=student_stats(sid)
    if approved<25: flash('لا يمكن ترشيح الطالبة للريادة قبل إكمال 25 كتابًا معتمدًا.','error')
    else:
        con=db(); con.execute('UPDATE students SET leadership=1 WHERE id=?',(sid,)); con.commit(); con.close(); flash('تم اعتماد الطالبة في مرحلة الريادة 🏆','ok')
    return redirect(url_for('admin'))

@app.get('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

if __name__=='__main__':
    init_db(); app.run(debug=True)
