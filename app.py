import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from db import get_db, init_db
from services import add_ledger, create_email_code, send_email, choose_lucky_winner

app = Flask(__name__)
app.config.from_object(Config)

with app.app_context():
    init_db()


def current_user():
    uid = session.get('user_id')
    if not uid: return None
    db = get_db(); user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone(); db.close()
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('Please log in first.')
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def earning_access(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for('register'))
        if user['status'] != 'active' or not user['email_verified']:
            flash('Complete registration verification before earning.')
            return redirect(url_for('payment'))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_globals():
    return {'user': current_user(), 'payment_number': app.config['PAYMENT_NUMBER']}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        first = request.form.get('first_name','').strip(); last = request.form.get('last_name','').strip()
        email = request.form.get('email','').strip().lower(); password = request.form.get('password',''); confirm = request.form.get('confirm','')
        terms = request.form.get('terms')
        if not all([first,last,email,password,confirm,terms]): flash('Fill every field and accept the terms.'); return render_template('register.html')
        if password != confirm: flash('Passwords do not match.'); return render_template('register.html')
        db = get_db()
        if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone(): db.close(); flash('Email already registered.'); return render_template('register.html')
        username = (first + last).replace(' ','').lower() + str(uuid.uuid4().int)[:4]
        ref = request.args.get('ref') or request.form.get('referral')
        code = uuid.uuid4().hex[:10].upper()
        cur = db.execute('INSERT INTO users(first_name,last_name,email,password_hash,username,status,terms_accepted,referral_code,referred_by) VALUES(?,?,?,?,?,?,?,?,?)', (first,last,email,generate_password_hash(password),username,'pending_payment',1,code,ref))
        uid = cur.lastrowid; db.commit(); db.close(); session['user_id']=uid
        return redirect(url_for('payment'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        db=get_db(); user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); db.close()
        if user and check_password_hash(user['password_hash'],password): session['user_id']=user['id']; return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('home'))

@app.route('/payment', methods=['GET','POST'])
@login_required
def payment():
    user=current_user()
    if request.method=='POST':
        proof=request.files.get('proof')
        if not proof or not proof.filename: flash('Upload the payment screenshot.'); return render_template('payment.html')
        name=secure_filename(proof.filename); filename=f'{user["id"]}_{uuid.uuid4().hex}_{name}'
        proof.save(os.path.join(app.config['UPLOAD_DIR'],filename))
        db=get_db(); db.execute('INSERT INTO payment_proofs(user_id,amount,recipient,filename) VALUES(?,?,?,?)',(user['id'],30000,app.config['PAYMENT_NUMBER'],filename)); db.execute('UPDATE users SET status="payment_review" WHERE id=?',(user['id'],)); db.commit(); db.close()
        flash('Payment proof submitted. Awaiting confirmation.')
        return redirect(url_for('dashboard'))
    return render_template('payment.html')

@app.route('/verify', methods=['GET','POST'])
def verify():
    user=current_user()
    if not user: return redirect(url_for('login'))
    if request.method=='POST':
        code=request.form.get('code','').strip()
        db=get_db(); row=db.execute('SELECT * FROM email_codes WHERE user_id=? AND code=? AND used=0 ORDER BY id DESC LIMIT 1',(user['id'],code)).fetchone()
        if row and datetime.fromisoformat(row['expires_at']) > datetime.now(timezone.utc):
            db.execute('UPDATE email_codes SET used=1 WHERE id=?',(row['id'],)); db.execute('UPDATE users SET email_verified=1,status="active" WHERE id=?',(user['id'],)); db.commit(); db.close(); flash('Registration completed.'); return redirect(url_for('dashboard'))
        db.close(); flash('Code is wrong or expired.')
    return render_template('verify.html')

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html', user=current_user())

@app.route('/earn')
@earning_access
def earn():
    db=get_db(); tasks=db.execute('SELECT * FROM tasks WHERE active=1').fetchall(); db.close(); return render_template('earn.html',tasks=tasks)

@app.route('/task/<int:task_id>/submit', methods=['POST'])
@earning_access
def submit_task(task_id):
    user=current_user(); proof=request.files.get('proof'); filename=''
    if proof and proof.filename:
        filename=f'task_{user["id"]}_{uuid.uuid4().hex}_{secure_filename(proof.filename)}'; proof.save(os.path.join(app.config['UPLOAD_DIR'],filename))
    db=get_db(); task=db.execute('SELECT * FROM tasks WHERE id=? AND active=1',(task_id,)).fetchone()
    if not task: db.close(); flash('Task not found.'); return redirect(url_for('earn'))
    db.execute('INSERT INTO task_submissions(user_id,task_id,proof_filename) VALUES(?,?,?)',(user['id'],task_id,filename)); db.commit(); db.close(); flash('Task submitted for review.'); return redirect(url_for('earn'))

@app.route('/refer')
@earning_access
def refer():
    u=current_user(); return render_template('refer.html', referral=url_for('register',ref=u['referral_code'],_external=True))

@app.route('/spin')
@earning_access
def spin():
    # Notebook wheel values are represented as a server-side random result.
    outcomes=[10,10,5,10,5,10]
    reward=outcomes[uuid.uuid4().int % len(outcomes)]
    add_ledger(current_user()['id'],'spin_reward',reward,'Daily spin')
    return jsonify({'reward':reward,'message':f'You won {reward} TCs'})

@app.route('/lucky-draw')
@earning_access
def lucky_draw():
    db=get_db(); draw=db.execute('SELECT * FROM lucky_draws WHERE status="collecting" ORDER BY id DESC LIMIT 1').fetchone(); db.close(); return render_template('lucky_draw.html',draw=draw)

@app.route('/lucky-draw/buy', methods=['POST'])
@earning_access
def lucky_buy():
    # Keeps the notebook's paid-entry concept as a disabled-by-default server setting.
    return jsonify({'ok':False,'message':'Paid lucky-draw entry is a launch-time compliance/payment integration feature. Configure and review it before enabling real-money entry.'}), 403

@app.route('/withdraw', methods=['GET','POST'])
@earning_access
def withdraw():
    u=current_user()
    if request.method=='POST':
        amount=float(request.form.get('amount') or 0); destination=request.form.get('destination','').strip()
        if amount < 50000: flash('Minimum withdrawal is 50,000 UGX.'); return render_template('withdraw.html')
        if amount > u['balance']: flash('Insufficient balance.'); return render_template('withdraw.html')
        db=get_db(); db.execute('UPDATE users SET balance=balance-? WHERE id=?',(amount,u['id'])); db.execute('INSERT INTO withdrawals(user_id,amount,destination) VALUES(?,?,?)',(u['id'],amount,destination)); db.execute('INSERT INTO ledger(user_id,kind,amount,note) VALUES(?,?,?,?)',(u['id'],'withdrawal',-amount,'Withdrawal requested')); db.commit(); db.close(); flash('Withdrawal request submitted.'); return redirect(url_for('dashboard'))
    return render_template('withdraw.html')

@app.route('/game/<slug>')
@earning_access
def game(slug):
    game_list = {**WAR_GAMES, **BOARD_GAMES}
    item=game_list.get(slug)
    if not item: return 'Game not found',404
    return render_template('game.html', game=item)

WAR_GAMES={
 'buildbattle': {'name':'Buildbattle','tier':2,'category':'War Games','rules':'Players have 30 minutes to build anything. When the timer runs out, builds receive life and HP; players battle on a floating, falling-off-is-elimination map. Last player standing wins. Physics, velocity, size and special build effects are part of the design.','voice':True},
 'colour-wars-2': {'name':'Colour Wars 2','tier':2,'category':'War Games','rules':'Players receive random colours and paint rollers. Spread your colour across the map for 5 minutes. Ability orbs can grant speed or a larger roller. Highest coverage wins.','voice':True},
 'hot-potato': {'name':'Hot Potato','tier':2,'category':'War Games','rules':'Players are arranged in a shape according to the amount. A random player gets the potato and automatically spins. Click to throw in the direction faced. Missed catches eliminate the thrower. The last player remaining wins.','voice':True},
 'jigsaw-puzzle-tournaments-2': {'name':'Jigsaw Puzzle Tournaments 2','tier':2,'category':'War Games','rules':'Players complete a very large and complicated puzzle. The player with the most points after the puzzle is done wins and takes the prize.','voice':True},
 'colour-arches': {'name':'Colour Arches','tier':2,'category':'War Games','rules':'Players use upgradeable arches with colour boards. Crossing an opponent colour starts shooting. Upgrades increase boundaries and shooting speed; ads can unlock speed or refill HP.','voice':True},
 'chrono-shatter': {'name':'Chrono Shatter','tier':2,'category':'War Games','rules':'60-second ticking time-bomb / life-theft concept from the notebook.','voice':True},
}
BOARD_GAMES={
 'unoverse': {'name':'Unoverse','tier':3,'category':'Board Games','rules':'Tier 3 board game concept.','voice':True},
 'hide-die': {'name':'Hide & Die','tier':3,'category':'Board Games','rules':'Tier 3 board game concept.','voice':True},
 'iceflow': {'name':'Iceflow','tier':3,'category':'Board Games','rules':'Players are on breaking ice. A player falls and is out; last player standing wins. Stepping on the same place twice breaks it.','voice':True},
 'ludo-2': {'name':'Ludo 2','tier':3,'category':'Board Games','rules':'Four players are randomly assigned to teams: defender/striker. Each team has one defender and one striker. Strikers must take all four pawns home. Stacking, blocking and the two-dice movement rules follow the notebook.','voice':True},
 'spinsters': {'name':'Spinsters','tier':3,'category':'Board Games','rules':'Players have a spinning disc and push other players off the platform. Last player standing wins.','voice':True},
 'the-last-slice': {'name':'The Last Slice','tier':3,'category':'Board Games','rules':'Players sit around a diner. A covered plate opens and players pull a pizza slice. The server can close/open it; rotten-slice events can remove points. First player to 10 points wins.','voice':True},
 'spelling-battle': {'name':'Spelling Battle','tier':3,'category':'Board Games','rules':'The server gives an audio prompt. Players have a few seconds to write it. First player to reach 10 points wins.','voice':True},
 'slapmouse': {'name':'Slapmouse','tier':3,'category':'Board Games','rules':'Tier 3 board game concept from the notebook.','voice':True},
}

@app.route('/games')
@earning_access
def games(): return render_template('games.html', war_games=WAR_GAMES, board_games=BOARD_GAMES)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if not session.get('admin'):
        if request.method=='POST' and request.form.get('passcode') == app.config['ADMIN_PASSCODE']:
            session['admin']=True; return redirect(url_for('admin'))
        return render_template('admin_login.html')
    db=get_db(); users=db.execute('SELECT * FROM users ORDER BY id DESC').fetchall(); payments=db.execute('SELECT p.*,u.email,u.first_name,u.last_name FROM payment_proofs p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC').fetchall(); withdrawals=db.execute('SELECT w.*,u.email FROM withdrawals w JOIN users u ON u.id=w.user_id ORDER BY w.id DESC').fetchall(); db.close()
    return render_template('admin.html',users=users,payments=payments,withdrawals=withdrawals)

@app.route('/admin/payment/<int:payment_id>/approve', methods=['POST'])
def approve_payment(payment_id):
    if not session.get('admin'): return 'Unauthorized',401
    db=get_db(); p=db.execute('SELECT * FROM payment_proofs WHERE id=?',(payment_id,)).fetchone()
    if not p: db.close(); return 'Not found',404
    db.execute('UPDATE payment_proofs SET status="approved" WHERE id=?',(payment_id,)); db.execute('UPDATE users SET status="email_verification" WHERE id=?',(p['user_id'],)); db.commit(); db.close()
    code=create_email_code(p['user_id']); db=get_db(); u=db.execute('SELECT * FROM users WHERE id=?',(p['user_id'],)).fetchone(); db.close()
    send_email(u['email'],'TimeCash verification code',f'Your TimeCash verification code is {code}. It expires in 60 seconds.')
    return redirect(url_for('admin'))

@app.route('/admin/logout')
def admin_logout(): session.pop('admin',None); return redirect(url_for('home'))

if __name__=='__main__':
    app.run(debug=True)
