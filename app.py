from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from database import Database
import os, secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
db = Database()

# إنشاء مستخدم افتراضي أول مرة
db.create_user('admin', 'admin123')

# ═══════ حماية الصفحات ═══════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ═══════ تسجيل الدخول ═══════
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.verify_user(request.form['username'], request.form['password'])
        if user:
            session['user'] = user
            return redirect(url_for('dashboard'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ═══════ لوحة التحكم ═══════
@app.route('/')
@login_required
def dashboard():
    stats = db.get_stats()
    recent_clients = db.get_all_clients()[:5]
    return render_template('dashboard.html', stats=stats, recent_clients=recent_clients)

# ═══════ العملاء ═══════
@app.route('/clients')
@login_required
def clients():
    search = request.args.get('q', '')
    all_clients = db.get_all_clients(search)
    return render_template('clients.html', clients=all_clients, search=search)

@app.route('/client/<int:cid>')
@login_required
def client_detail(cid):
    client = db.get_client(cid)
    if not client:
        flash('العميل غير موجود', 'error')
        return redirect(url_for('clients'))
    websites = db.get_websites_by_client(cid)
    # فك تشفير كلمات المرور للعرض
    for w in websites:
        w['decrypted_password'] = db.decrypt_password(w.get('password', ''))
    return render_template('client_detail.html', client=client, websites=websites)

@app.route('/client/add', methods=['GET', 'POST'])
@app.route('/client/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def add_edit_client(cid=None):
    client = None
    websites = []
    if cid:
        client = db.get_client(cid)
        websites = db.get_websites_by_client(cid)
        for w in websites:
            w['decrypted_password'] = db.decrypt_password(w.get('password', ''))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('الاسم مطلوب', 'error')
            return render_template('add_client.html', client=client, websites=websites)

        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        notes = request.form.get('notes', '').strip()
        is_vip = 1 if request.form.get('is_vip') else 0

        if cid:
            db.update_client(cid, name, phone, email, notes, is_vip)
            db.delete_websites_by_client(cid)
            client_id = cid
        else:
            client_id = db.add_client(name, phone, email, notes, is_vip)

        # حفظ المواقع
        site_names = request.form.getlist('site_name[]')
        site_urls = request.form.getlist('site_url[]')
        site_emails = request.form.getlist('login_email[]')
        site_passwords = request.form.getlist('password[]')
        site_categories = request.form.getlist('category[]')
        site_notes_list = request.form.getlist('site_notes[]')

        for i in range(len(site_names)):
            if site_names[i].strip():
                db.add_website(
                    client_id,
                    site_names[i].strip(),
                    site_urls[i].strip() if i < len(site_urls) else '',
                    site_emails[i].strip() if i < len(site_emails) else '',
                    site_passwords[i].strip() if i < len(site_passwords) else '',
                    site_notes_list[i].strip() if i < len(site_notes_list) else '',
                    site_categories[i] if i < len(site_categories) else 'شخصي'
                )

        flash('تم الحفظ بنجاح ✅', 'success')
        return redirect(url_for('client_detail', cid=client_id))

    return render_template('add_client.html', client=client, websites=websites)

@app.route('/client/<int:cid>/delete', methods=['POST'])
@login_required
def delete_client(cid):
    db.delete_client(cid)
    flash('تم الحذف بنجاح', 'success')
    return redirect(url_for('clients'))

# ═══════ الاستعلام ═══════
@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
    results = db.get_all_clients(q) if q else []
    # إرفاق عدد المواقع لكل نتيجة
    for c in results:
        c['website_count'] = len(db.get_websites_by_client(c['id']))
    return render_template('search.html', results=results, query=q)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)