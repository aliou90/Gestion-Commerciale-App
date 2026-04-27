"""Gestion Commerciale v4.0 — Auth + Paiements QR"""
import os, sqlite3, io, uuid
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, send_file, g, send_from_directory, session)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from PIL import Image as PILImage
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "gc_secret_v4_2024_ultra"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

DB_PATH     = os.path.join(os.path.dirname(__file__), "database.db")
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "static", "uploads")
PRODUIT_DIR = os.path.join(UPLOAD_ROOT, "produits")
THUMB_DIR   = os.path.join(UPLOAD_ROOT, "thumbs")
LOGO_DIR    = os.path.join(UPLOAD_ROOT, "logo")
QR_DIR      = os.path.join(UPLOAD_ROOT, "qr_paiement")
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

for d in [PRODUIT_DIR, THUMB_DIR, LOGO_DIR, QR_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Auth ──────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

# ── DB ────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def row_to_dict(r): return dict(r) if r else None
def rows_to_list(rs): return [dict(r) for r in rs]

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS parametres(cle TEXT PRIMARY KEY, valeur TEXT);
    CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS produits(
        id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL, description TEXT, categorie_id INTEGER REFERENCES categories(id),
        prix_achat REAL DEFAULT 0, prix_vente REAL NOT NULL, tva REAL DEFAULT 18,
        stock INTEGER DEFAULT 0, stock_min INTEGER DEFAULT 5, unite TEXT DEFAULT 'unité',
        actif INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS produit_images(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
        filename TEXT NOT NULL, thumb_filename TEXT NOT NULL,
        principale INTEGER DEFAULT 0, ordre INTEGER DEFAULT 0,
        alt_text TEXT, created_at TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL, prenom TEXT, email TEXT, telephone TEXT,
        adresse TEXT, ville TEXT, pays TEXT DEFAULT 'Sénégal',
        type_client TEXT DEFAULT 'particulier', remise REAL DEFAULT 0,
        actif INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS moyens_paiement(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL UNIQUE,
        type_paiement TEXT DEFAULT 'mobile',
        description TEXT,
        telephone TEXT,
        qr_filename TEXT,
        couleur TEXT DEFAULT '#1B73E8',
        banque_nom TEXT,
        banque_iban TEXT,
        banque_swift TEXT,
        banque_titulaire TEXT,
        banque_agence TEXT,
        actif INTEGER DEFAULT 1,
        ordre INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')));
    -- Migration: add telephone if missing

    CREATE TABLE IF NOT EXISTS commandes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL REFERENCES clients(id),
        moyen_paiement_id INTEGER REFERENCES moyens_paiement(id),
        date_commande TEXT DEFAULT (datetime('now')), date_livraison TEXT,
        statut TEXT DEFAULT 'en_attente', remise_globale REAL DEFAULT 0,
        notes TEXT, created_at TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS lignes_commande(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
        produit_id INTEGER NOT NULL REFERENCES produits(id),
        quantite INTEGER NOT NULL DEFAULT 1, prix_unitaire REAL NOT NULL,
        remise REAL DEFAULT 0, tva REAL DEFAULT 18);
    CREATE TABLE IF NOT EXISTS factures(
        id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT NOT NULL UNIQUE,
        commande_id INTEGER REFERENCES commandes(id),
        client_id INTEGER NOT NULL REFERENCES clients(id),
        date_facture TEXT DEFAULT (datetime('now')), date_echeance TEXT,
        statut TEXT DEFAULT 'non_payee', notes TEXT,
        created_at TEXT DEFAULT (datetime('now')));
    """)
    # Migrations
    for col_def in [
        "ALTER TABLE moyens_paiement ADD COLUMN telephone TEXT",
        "ALTER TABLE moyens_paiement ADD COLUMN type_paiement TEXT DEFAULT 'mobile'",
        "ALTER TABLE moyens_paiement ADD COLUMN banque_nom TEXT",
        "ALTER TABLE moyens_paiement ADD COLUMN banque_iban TEXT",
        "ALTER TABLE moyens_paiement ADD COLUMN banque_swift TEXT",
        "ALTER TABLE moyens_paiement ADD COLUMN banque_titulaire TEXT",
        "ALTER TABLE moyens_paiement ADD COLUMN banque_agence TEXT",
    ]:
        try: db.execute(col_def)
        except: pass
    db.commit()

    defs = {
        'boutique_nom':'Ma Boutique','boutique_adresse':'123 Rue du Commerce',
        'boutique_ville':'Dakar','boutique_pays':'Sénégal',
        'boutique_telephone':'+221 77 000 00 00','boutique_email':'contact@maboutique.sn',
        'boutique_ninea':'NINEA: 000000000','boutique_rccm':'RCCM: DKR-2024-B-00000',
        'devise':'FCFA','tva_defaut':'18','couleur_primaire':'#1a56db',
        'logo_text':'MB','logo_filename':'',
        'admin_password': generate_password_hash('123456'),
    }
    for k,v in defs.items():
        db.execute("INSERT OR IGNORE INTO parametres VALUES(?,?)",(k,v))
    for cat in ['Électronique','Vêtements','Alimentation','Fournitures','Cosmétiques']:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES(?)",(cat,))
    for mp in [('Wave','mobile','Paiement Wave','#1B73E8',1),
               ('Orange Money','mobile','Paiement Orange Money','#FF6600',2),
               ('Free Money','mobile','Paiement Free Money','#CC0000',3)]:
        db.execute("INSERT OR IGNORE INTO moyens_paiement(nom,type_paiement,description,couleur,ordre) VALUES(?,?,?,?,?)",mp)
    db.commit(); db.close()

def get_param(k,d=''): r=get_db().execute("SELECT valeur FROM parametres WHERE cle=?",(k,)).fetchone(); return r['valeur'] if r else d
def get_all_params(): return {r['cle']:r['valeur'] for r in get_db().execute("SELECT cle,valeur FROM parametres").fetchall()}

def next_numero(prefix,table,col):
    today=date.today().strftime('%Y%m')
    r=get_db().execute(f"SELECT COUNT(*) as c FROM {table} WHERE {col} LIKE ?",(f"{prefix}-{today}-%",)).fetchone()
    return f"{prefix}-{today}-{r['c']+1:04d}"

def commande_totaux(cid):
    db=get_db()
    ls=db.execute("""SELECT l.*,p.nom as produit_nom,p.reference as produit_ref
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id
        WHERE l.commande_id=? ORDER BY l.id""",(cid,)).fetchall()
    cmd=db.execute("SELECT remise_globale FROM commandes WHERE id=?",(cid,)).fetchone()
    rg=float(cmd['remise_globale']) if cmd else 0.0
    ht=sum(l['quantite']*l['prix_unitaire']*(1-l['remise']/100) for l in ls)
    tv=sum(l['quantite']*l['prix_unitaire']*(1-l['remise']/100)*l['tva']/100 for l in ls)
    return {'ht':ht,'ht_net':ht*(1-rg/100),'tva':tv*(1-rg/100),
            'ttc':ht*(1-rg/100)+tv*(1-rg/100),'remise_globale':rg,
            'remise_montant':ht*rg/100,'lignes':ls}

# ── Image helpers ─────────────────────────────────────────────
def allowed(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXT

def save_img(fo, ddir=None, tdir=None, maxs=(1200,1200), ths=(320,320)):
    if ddir is None: ddir=PRODUIT_DIR
    if tdir is None: tdir=THUMB_DIR
    if not fo or not fo.filename or not allowed(fo.filename): return None
    ext=fo.filename.rsplit('.',1)[1].lower()
    if ext=='jpg': ext='jpeg'
    uid=uuid.uuid4().hex; fn=f"{uid}.{ext}"; tfn=f"th_{uid}.{ext}"
    fmt='PNG' if ext=='png' else 'JPEG'
    try:
        img=PILImage.open(fo.stream).convert('RGBA' if ext=='png' else 'RGB')
        img.thumbnail(maxs,PILImage.LANCZOS)
        img.save(os.path.join(ddir,fn),format=fmt,quality=88,optimize=True)
        th=img.copy(); th.thumbnail(ths,PILImage.LANCZOS)
        w,h=th.size; s=min(w,h)
        th=th.crop(((w-s)//2,(h-s)//2,(w-s)//2+s,(h-s)//2+s))
        th.save(os.path.join(tdir,tfn),format=fmt,quality=82,optimize=True)
        return fn,tfn
    except Exception as e: print(f"[img]{e}"); return None

def del_img(fn,tfn,ddir=None,tdir=None):
    if ddir is None: ddir=PRODUIT_DIR
    if tdir is None: tdir=THUMB_DIR
    for p in [os.path.join(ddir,fn),os.path.join(tdir,tfn)]:
        try:
            if os.path.exists(p): os.remove(p)
        except: pass

def save_qr(fo):
    if not fo or not fo.filename or not allowed(fo.filename): return None
    ext=fo.filename.rsplit('.',1)[1].lower()
    if ext=='jpg': ext='jpeg'
    uid=uuid.uuid4().hex; fn=f"qr_{uid}.{ext}"
    fmt='PNG' if ext=='png' else 'JPEG'
    try:
        img=PILImage.open(fo.stream).convert('RGBA' if ext=='png' else 'RGB')
        img.thumbnail((600,600),PILImage.LANCZOS)
        img.save(os.path.join(QR_DIR,fn),format=fmt,quality=90,optimize=True)
        return fn
    except Exception as e: print(f"[qr]{e}"); return None

def get_prod_imgs(pid): return rows_to_list(get_db().execute("SELECT * FROM produit_images WHERE produit_id=? ORDER BY principale DESC,ordre,id",(pid,)).fetchall())
def get_prod_main_img(pid):
    db=get_db()
    r=db.execute("SELECT * FROM produit_images WHERE produit_id=? AND principale=1 LIMIT 1",(pid,)).fetchone()
    if not r: r=db.execute("SELECT * FROM produit_images WHERE produit_id=? ORDER BY ordre,id LIMIT 1",(pid,)).fetchone()
    return row_to_dict(r)

def get_logo_url(params=None):
    if params is None: params=get_all_params()
    lf=params.get('logo_filename','')
    if lf and os.path.exists(os.path.join(LOGO_DIR,lf)): return f"/uploads/logo/{lf}"
    return None

def get_moyens(actif_only=True):
    q="SELECT * FROM moyens_paiement"
    if actif_only: q+=" WHERE actif=1"
    return rows_to_list(get_db().execute(q+" ORDER BY ordre,nom").fetchall())

# ── Context + filters ─────────────────────────────────────────
@app.context_processor
def inject_globals():
    p=get_all_params()
    return {'now':datetime.now().strftime('%d/%m/%Y %H:%M'),
            'now_date':date.today().isoformat(),'today':date.today().isoformat(),
            'logo_url':get_logo_url(p)}

@app.template_filter('fmt_currency')
def fmt_currency(val,devise='FCFA'):
    try: return f"{float(val):,.0f} {devise}".replace(',','\u202f')
    except: return f"0 {devise}"

@app.template_filter('fmt_date')
def fmt_date(val):
    if not val: return ''
    try: return datetime.fromisoformat(str(val)[:10]).strftime('%d/%m/%Y')
    except: return str(val)[:10]

@app.template_filter('statut_badge')
def statut_badge(s):
    m={'en_attente':('bg-y','⏳ En attente'),'confirmee':('bg-b','✓ Confirmée'),
       'expediee':('bg-v','🚚 Expédiée'),'livree':('bg-g','✅ Livrée'),
       'annulee':('bg-r','✗ Annulée'),'payee':('bg-g','✅ Payée'),
       'non_payee':('bg-r','⚠ Non payée'),'partiellement_payee':('bg-o','◑ Partielle')}
    cls,lbl=m.get(s,('bg-gr',s)); return f'<span class="badge {cls}">{lbl}</span>'

# ── Static uploads ────────────────────────────────────────────
@app.route('/uploads/produits/<f>') 
def uploaded_produit(f): return send_from_directory(PRODUIT_DIR,f)
@app.route('/uploads/thumbs/<f>')
def uploaded_thumb(f): return send_from_directory(THUMB_DIR,f)
@app.route('/uploads/logo/<f>')
def uploaded_logo(f): return send_from_directory(LOGO_DIR,f)
@app.route('/uploads/qr/<f>')
def uploaded_qr(f): return send_from_directory(QR_DIR,f)

# ── AUTH ──────────────────────────────────────────────────────
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('logged_in'): return redirect(url_for('dashboard'))
    params=get_all_params(); error=None
    if request.method=='POST':
        pwd=request.form.get('password','')
        h=get_param('admin_password','')
        if h and check_password_hash(h,pwd):
            session.permanent=True; session['logged_in']=True
            flash('Bienvenue !','success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        error='Mot de passe incorrect.'
    return render_template('login.html',params=params,error=error)

@app.route('/logout')
def logout():
    session.clear(); flash('Déconnecté.','info'); return redirect(url_for('login'))

# ── DASHBOARD ─────────────────────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    db=get_db(); mois=date.today().strftime('%Y-%m')
    stats={'nb_produits':db.execute("SELECT COUNT(*) FROM produits WHERE actif=1").fetchone()[0],
           'nb_clients':db.execute("SELECT COUNT(*) FROM clients WHERE actif=1").fetchone()[0],
           'nb_commandes':db.execute("SELECT COUNT(*) FROM commandes").fetchone()[0],
           'nb_factures':db.execute("SELECT COUNT(*) FROM factures").fetchone()[0],
           'stock_alerte':db.execute("SELECT COUNT(*) FROM produits WHERE stock<=stock_min AND actif=1").fetchone()[0],
           'cmd_attente':db.execute("SELECT COUNT(*) FROM commandes WHERE statut='en_attente'").fetchone()[0],
           'fact_impayees':db.execute("SELECT COUNT(*) FROM factures WHERE statut='non_payee'").fetchone()[0]}
    r=db.execute("""SELECT COALESCE(SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)),0) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id WHERE strftime('%Y-%m',c.date_commande)=?""",(mois,)).fetchone()
    stats['ca_mois']=r['ca'] if r else 0
    recent_cmds=db.execute("SELECT c.*,cl.nom as client_nom FROM commandes c JOIN clients cl ON cl.id=c.client_id ORDER BY c.created_at DESC LIMIT 6").fetchall()
    top_raw=db.execute("""SELECT p.id,p.nom,SUM(l.quantite) as qte,SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)) as ca
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id JOIN commandes c ON c.id=l.commande_id
        WHERE strftime('%Y-%m',c.date_commande)=? GROUP BY p.id ORDER BY ca DESC LIMIT 5""",(mois,)).fetchall()
    top_produits=[{'p':dict(p),'img':get_prod_main_img(p['id'])} for p in top_raw]
    return render_template('dashboard.html',stats=stats,recent_cmds=recent_cmds,top_produits=top_produits,params=get_all_params())

# ── PRODUITS ──────────────────────────────────────────────────
@app.route('/produits')
@login_required
def produits():
    db=get_db(); q=request.args.get('q',''); cat=request.args.get('cat','')
    query="SELECT p.*,c.nom as cat_nom FROM produits p LEFT JOIN categories c ON c.id=p.categorie_id WHERE p.actif=1"; args=[]
    if q: query+=" AND (p.nom LIKE ? OR p.reference LIKE ?)"; args+=[f'%{q}%',f'%{q}%']
    if cat: query+=" AND p.categorie_id=?"; args.append(cat)
    ps=db.execute(query+" ORDER BY p.nom",args).fetchall()
    return render_template('produits.html',produits_data=[{'p':dict(p),'img':get_prod_main_img(p['id'])} for p in ps],
        categories=db.execute("SELECT * FROM categories ORDER BY nom").fetchall(),q=q,cat=cat,params=get_all_params())

@app.route('/produits/nouveau',methods=['GET','POST'])
@login_required
def nouveau_produit():
    db=get_db(); cats=db.execute("SELECT * FROM categories ORDER BY nom").fetchall(); params=get_all_params()
    if request.method=='POST':
        f=request.form; ref=(f.get('reference') or '').strip() or f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            db.execute("INSERT INTO produits(reference,nom,description,categorie_id,prix_achat,prix_vente,tva,stock,stock_min,unite) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (ref,f['nom'],f.get('description') or None,f.get('categorie_id') or None,
                 float(f.get('prix_achat',0) or 0),float(f['prix_vente']),
                 float(f.get('tva',get_param('tva_defaut','18')) or 18),
                 int(f.get('stock',0) or 0),int(f.get('stock_min',5) or 5),f.get('unite','unité')))
            db.commit()
            pid=db.execute("SELECT id FROM produits WHERE reference=?",(ref,)).fetchone()['id']
            _proc_imgs(db,pid,request.files); db.commit()
            flash('Produit créé !','success'); return redirect(url_for('produits'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('produit_form.html',produit=None,images=[],categories=cats,params=params)

@app.route('/produits/<int:id>/modifier',methods=['GET','POST'])
@login_required
def modifier_produit(id):
    db=get_db(); p=db.execute("SELECT * FROM produits WHERE id=?",(id,)).fetchone()
    cats=db.execute("SELECT * FROM categories ORDER BY nom").fetchall(); params=get_all_params()
    if not p: flash('Introuvable.','danger'); return redirect(url_for('produits'))
    if request.method=='POST':
        f=request.form
        try:
            db.execute("UPDATE produits SET reference=?,nom=?,description=?,categorie_id=?,prix_achat=?,prix_vente=?,tva=?,stock=?,stock_min=?,unite=? WHERE id=?",
                (f['reference'],f['nom'],f.get('description') or None,f.get('categorie_id') or None,
                 float(f.get('prix_achat',0) or 0),float(f['prix_vente']),float(f.get('tva',18) or 18),
                 int(f.get('stock',0) or 0),int(f.get('stock_min',5) or 5),f.get('unite','unité'),id))
            _proc_imgs(db,id,request.files)
            pid=f.get('principale_id')
            if pid:
                db.execute("UPDATE produit_images SET principale=0 WHERE produit_id=?",(id,))
                db.execute("UPDATE produit_images SET principale=1 WHERE id=? AND produit_id=?",(pid,id))
            db.commit(); flash('Modifié !','success'); return redirect(url_for('produits'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('produit_form.html',produit=p,images=get_prod_imgs(id),categories=cats,params=params)

def _proc_imgs(db,pid,files):
    uploaded=files.getlist('images[]')
    ex=db.execute("SELECT COUNT(*) as c FROM produit_images WHERE produit_id=?",(pid,)).fetchone()['c']
    for i,fo in enumerate(uploaded):
        r=save_img(fo)
        if r:
            fn,tfn=r
            db.execute("INSERT INTO produit_images(produit_id,filename,thumb_filename,principale,ordre) VALUES(?,?,?,?,?)",
                       (pid,fn,tfn,1 if (ex==0 and i==0) else 0,ex+i))

@app.route('/produits/<int:id>/supprimer',methods=['POST'])
@login_required
def supprimer_produit(id):
    db=get_db(); db.execute("UPDATE produits SET actif=0 WHERE id=?",(id,)); db.commit()
    flash('Archivé.','info'); return redirect(url_for('produits'))

@app.route('/produits/image/<int:img_id>/supprimer',methods=['POST'])
@login_required
def supprimer_image_produit(img_id):
    db=get_db(); img=db.execute("SELECT * FROM produit_images WHERE id=?",(img_id,)).fetchone()
    if not img: return jsonify({'error':'Introuvable'}),404
    del_img(img['filename'],img['thumb_filename'])
    db.execute("DELETE FROM produit_images WHERE id=?",(img_id,))
    if img['principale']:
        nxt=db.execute("SELECT id FROM produit_images WHERE produit_id=? ORDER BY ordre,id LIMIT 1",(img['produit_id'],)).fetchone()
        if nxt: db.execute("UPDATE produit_images SET principale=1 WHERE id=?",(nxt['id'],))
    db.commit(); return jsonify({'ok':True})

@app.route('/produits/image/<int:img_id>/principale',methods=['POST'])
@login_required
def set_image_principale(img_id):
    db=get_db(); img=db.execute("SELECT * FROM produit_images WHERE id=?",(img_id,)).fetchone()
    if not img: return jsonify({'error':'Introuvable'}),404
    db.execute("UPDATE produit_images SET principale=0 WHERE produit_id=?",(img['produit_id'],))
    db.execute("UPDATE produit_images SET principale=1 WHERE id=?",(img_id,))
    db.commit(); return jsonify({'ok':True})

@app.route('/produits/<int:pid>/images/reorder',methods=['POST'])
@login_required
def reorder_images(pid):
    ids=(request.json or {}).get('ids',[]); db=get_db()
    for i,iid in enumerate(ids): db.execute("UPDATE produit_images SET ordre=? WHERE id=? AND produit_id=?",(i,iid,pid))
    db.commit(); return jsonify({'ok':True})

# ── MOYENS DE PAIEMENT ────────────────────────────────────────
@app.route('/paiements')
@login_required
def paiements():
    return render_template('paiements.html',moyens=get_moyens(actif_only=False),params=get_all_params())

@app.route('/paiements/nouveau',methods=['GET','POST'])
@login_required
def nouveau_paiement():
    params=get_all_params()
    if request.method=='POST':
        f=request.form; db=get_db(); nom=f.get('nom','').strip()
        type_p=f.get('type_paiement','mobile')
        if not nom: flash('Nom requis.','danger')
        else:
            try:
                qr_fn=save_qr(request.files.get('qr_file'))
                db.execute("""INSERT INTO moyens_paiement
                    (nom,type_paiement,description,telephone,qr_filename,couleur,ordre,
                     banque_nom,banque_iban,banque_swift,banque_titulaire,banque_agence)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (nom, type_p,
                     f.get('description') or None,
                     (f.get('telephone','').strip() if type_p!='bancaire' else f.get('banque_telephone','').strip()) or None,
                     qr_fn,
                     f.get('couleur','#1B73E8'),
                     int(f.get('ordre',0) or 0),
                     f.get('banque_nom','').strip() or None,
                     f.get('banque_iban','').strip() or None,
                     f.get('banque_swift','').strip() or None,
                     f.get('banque_titulaire','').strip() or None,
                     f.get('banque_agence','').strip() or None,
                    ))
                db.commit(); flash(f'"{nom}" créé !','success'); return redirect(url_for('paiements'))
            except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('paiement_form.html',moyen=None,params=params)

@app.route('/paiements/<int:id>/modifier',methods=['GET','POST'])
@login_required
def modifier_paiement(id):
    db=get_db()
    m=db.execute("SELECT * FROM moyens_paiement WHERE id=?",(id,)).fetchone()
    params=get_all_params()
    if not m: flash('Introuvable.','danger'); return redirect(url_for('paiements'))
    if request.method=='POST':
        f=request.form
        nom=f.get('nom','').strip()
        if not nom:
            flash('Le nom est requis.','danger')
            return render_template('paiement_form.html',moyen=row_to_dict(m),params=params)
        try:
            # IMPORTANT: keep existing QR, only replace if new file submitted
            qr_fn=m['qr_filename']
            new_qr=save_qr(request.files.get('qr_file'))
            if new_qr:
                if qr_fn:
                    op=os.path.join(QR_DIR,qr_fn)
                    if os.path.exists(op): os.remove(op)
                qr_fn=new_qr
            type_p=f.get('type_paiement', m.get('type_paiement','mobile') if hasattr(m,'get') else (m['type_paiement'] or 'mobile'))
            db.execute("""UPDATE moyens_paiement SET
                nom=?,type_paiement=?,description=?,telephone=?,qr_filename=?,couleur=?,ordre=?,actif=?,
                banque_nom=?,banque_iban=?,banque_swift=?,banque_titulaire=?,banque_agence=?
                WHERE id=?""",
                (nom, type_p,
                 f.get('description') or None,
                 (f.get('telephone','').strip() if type_p!='bancaire' else f.get('banque_telephone','').strip()) or None,
                 qr_fn,
                 f.get('couleur','#1B73E8'),
                 int(f.get('ordre',0) or 0),
                 1 if f.get('actif','1') not in ('0','') else 0,
                 f.get('banque_nom','').strip() or None,
                 f.get('banque_iban','').strip() or None,
                 f.get('banque_swift','').strip() or None,
                 f.get('banque_titulaire','').strip() or None,
                 f.get('banque_agence','').strip() or None,
                 id))
            db.commit()
            flash('Mis à jour !','success')
            return redirect(url_for('paiements'))
        except Exception as e:
            flash(f'Erreur : {e}','danger')
    return render_template('paiement_form.html',moyen=row_to_dict(m),params=params)

@app.route('/paiements/<int:id>/supprimer',methods=['POST'])
@login_required
def supprimer_paiement(id):
    db=get_db(); m=db.execute("SELECT * FROM moyens_paiement WHERE id=?",(id,)).fetchone()
    if m and m['qr_filename']:
        p=os.path.join(QR_DIR,m['qr_filename'])
        if os.path.exists(p): os.remove(p)
    db.execute("DELETE FROM moyens_paiement WHERE id=?",(id,)); db.commit()
    flash('Supprimé.','info'); return redirect(url_for('paiements'))

@app.route('/paiements/<int:id>/qr/supprimer',methods=['POST'])
@login_required
def supprimer_qr(id):
    db=get_db(); m=db.execute("SELECT * FROM moyens_paiement WHERE id=?",(id,)).fetchone()
    if not m: return jsonify({'error':'Introuvable'}),404
    if m['qr_filename']:
        p=os.path.join(QR_DIR,m['qr_filename'])
        try:
            if os.path.exists(p): os.remove(p)
        except: pass
        db.execute("UPDATE moyens_paiement SET qr_filename=NULL WHERE id=?",(id,)); db.commit()
    # JSON response for AJAX calls, redirect for form POST
    if request.headers.get('X-Requested-With')=='XMLHttpRequest' or request.is_json:
        return jsonify({'ok':True})
    flash('QR supprimé.','success'); return redirect(url_for('modifier_paiement',id=id))

# ── CLIENTS ───────────────────────────────────────────────────
@app.route('/clients')
@login_required
def clients():
    db=get_db(); q=request.args.get('q','')
    query="SELECT * FROM clients WHERE actif=1"; args=[]
    if q: query+=" AND (nom LIKE ? OR code LIKE ? OR email LIKE ? OR telephone LIKE ?)"; args+=[f'%{q}%']*4
    return render_template('clients.html',clients=db.execute(query+" ORDER BY nom",args).fetchall(),q=q,params=get_all_params())

@app.route('/clients/nouveau',methods=['GET','POST'])
@login_required
def nouveau_client():
    db=get_db(); params=get_all_params()
    if request.method=='POST':
        f=request.form; code=(f.get('code') or '').strip() or f"CLI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            db.execute("INSERT INTO clients(code,nom,prenom,email,telephone,adresse,ville,pays,type_client,remise) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (code,f['nom'],f.get('prenom') or None,f.get('email') or None,f.get('telephone') or None,
                 f.get('adresse') or None,f.get('ville') or None,f.get('pays','Sénégal'),
                 f.get('type_client','particulier'),float(f.get('remise',0) or 0)))
            db.commit(); flash('Client créé !','success'); return redirect(url_for('clients'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('client_form.html',client=None,params=params)

@app.route('/clients/<int:id>/modifier',methods=['GET','POST'])
@login_required
def modifier_client(id):
    db=get_db(); cl=db.execute("SELECT * FROM clients WHERE id=?",(id,)).fetchone(); params=get_all_params()
    if not cl: flash('Introuvable.','danger'); return redirect(url_for('clients'))
    if request.method=='POST':
        f=request.form
        try:
            db.execute("UPDATE clients SET code=?,nom=?,prenom=?,email=?,telephone=?,adresse=?,ville=?,pays=?,type_client=?,remise=? WHERE id=?",
                (f['code'],f['nom'],f.get('prenom') or None,f.get('email') or None,f.get('telephone') or None,
                 f.get('adresse') or None,f.get('ville') or None,f.get('pays','Sénégal'),
                 f.get('type_client','particulier'),float(f.get('remise',0) or 0),id))
            db.commit(); flash('Modifié !','success'); return redirect(url_for('clients'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('client_form.html',client=cl,params=params)

@app.route('/clients/<int:id>/supprimer',methods=['POST'])
@login_required
def supprimer_client(id):
    db=get_db(); db.execute("UPDATE clients SET actif=0 WHERE id=?",(id,)); db.commit()
    flash('Archivé.','info'); return redirect(url_for('clients'))

# ── COMMANDES ─────────────────────────────────────────────────
@app.route('/commandes')
@login_required
def commandes():
    db=get_db(); statut=request.args.get('statut',''); q=request.args.get('q','')
    query="SELECT c.*,cl.nom as client_nom FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE 1=1"; args=[]
    if statut: query+=" AND c.statut=?"; args.append(statut)
    if q: query+=" AND (c.numero LIKE ? OR cl.nom LIKE ?)"; args+=[f'%{q}%',f'%{q}%']
    cs=db.execute(query+" ORDER BY c.created_at DESC",args).fetchall()
    return render_template('commandes.html',commandes_data=[{'cmd':c,'ttc':commande_totaux(c['id'])['ttc']} for c in cs],
        statut=statut,q=q,params=get_all_params())

def _build_prods():
    raw=rows_to_list(get_db().execute("SELECT id,nom,reference,prix_vente,tva,stock,unite FROM produits WHERE actif=1 ORDER BY nom").fetchall())
    for p in raw:
        img=get_prod_main_img(p['id']); p['thumb']=f"/uploads/thumbs/{img['thumb_filename']}" if img else None
    return raw

@app.route('/commandes/nouvelle',methods=['GET','POST'])
@login_required
def nouvelle_commande():
    db=get_db()
    cls=db.execute("SELECT id,code,nom,prenom FROM clients WHERE actif=1 ORDER BY nom").fetchall()
    prods=_build_prods(); moyens=get_moyens(); params=get_all_params()
    if request.method=='POST':
        f=request.form; num=next_numero('CMD','commandes','numero'); mp=f.get('moyen_paiement_id') or None
        try:
            db.execute("INSERT INTO commandes(numero,client_id,moyen_paiement_id,date_commande,date_livraison,statut,remise_globale,notes) VALUES(?,?,?,?,?,?,?,?)",
                (num,int(f['client_id']),int(mp) if mp else None,
                 f.get('date_commande') or date.today().isoformat(),f.get('date_livraison') or None,
                 f.get('statut','en_attente'),float(f.get('remise_globale',0) or 0),f.get('notes') or None))
            db.commit()
            cid=db.execute("SELECT id FROM commandes WHERE numero=?",(num,)).fetchone()['id']
            _save_lignes(db,cid,request.form); db.commit()
            flash(f'Commande {num} créée !','success'); return redirect(url_for('voir_commande',id=cid))
        except Exception as e: db.rollback(); flash(f'Erreur : {e}','danger')
    return render_template('commande_form.html',commande=None,clients=cls,produits=prods,lignes=[],moyens=moyens,params=params,mode='new')

@app.route('/commandes/<int:id>')
@login_required
def voir_commande(id):
    db=get_db()
    c=db.execute("""SELECT c.*,cl.nom as client_nom,cl.email as client_email,cl.telephone as client_tel,
        cl.adresse as client_adresse,cl.ville as client_ville,cl.pays as client_pays,cl.code as client_code
        FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE c.id=?""",(id,)).fetchone()
    if not c: flash('Introuvable.','danger'); return redirect(url_for('commandes'))
    totaux=commande_totaux(id)
    fac=db.execute("SELECT * FROM factures WHERE commande_id=?",(id,)).fetchone()
    mp=None
    if c['moyen_paiement_id']:
        mp=db.execute("SELECT * FROM moyens_paiement WHERE id=?",(c['moyen_paiement_id'],)).fetchone()
    return render_template('commande_detail.html',commande=c,totaux=totaux,facture=fac,
        moyen_paiement=row_to_dict(mp),params=get_all_params())

@app.route('/commandes/<int:id>/modifier',methods=['GET','POST'])
@login_required
def modifier_commande(id):
    db=get_db()
    c=db.execute("SELECT c.*,cl.nom as client_nom FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE c.id=?",(id,)).fetchone()
    if not c: flash('Introuvable.','danger'); return redirect(url_for('commandes'))
    if c['statut'] in ('livree','annulee'):
        flash(f'Impossible de modifier une commande {c["statut"]}.','warning'); return redirect(url_for('voir_commande',id=id))
    cls=db.execute("SELECT id,code,nom,prenom FROM clients WHERE actif=1 ORDER BY nom").fetchall()
    prods=_build_prods(); moyens=get_moyens()
    ls=rows_to_list(db.execute("SELECT l.*,p.nom as produit_nom FROM lignes_commande l JOIN produits p ON p.id=l.produit_id WHERE l.commande_id=?",(id,)).fetchall())
    params=get_all_params()
    if request.method=='POST':
        f=request.form; mp=f.get('moyen_paiement_id') or None
        try:
            for l in db.execute("SELECT produit_id,quantite FROM lignes_commande WHERE commande_id=?",(id,)).fetchall():
                db.execute("UPDATE produits SET stock=stock+? WHERE id=?",(l['quantite'],l['produit_id']))
            db.execute("UPDATE commandes SET client_id=?,moyen_paiement_id=?,date_commande=?,date_livraison=?,statut=?,remise_globale=?,notes=? WHERE id=?",
                (int(f['client_id']),int(mp) if mp else None,
                 f.get('date_commande') or date.today().isoformat(),f.get('date_livraison') or None,
                 f.get('statut','en_attente'),float(f.get('remise_globale',0) or 0),f.get('notes') or None,id))
            db.execute("DELETE FROM lignes_commande WHERE commande_id=?",(id,))
            _save_lignes(db,id,request.form); db.commit()
            db.execute("DELETE FROM factures WHERE commande_id=? AND statut='non_payee'",(id,)); db.commit()
            flash('Mis à jour !','success'); return redirect(url_for('voir_commande',id=id))
        except Exception as e: db.rollback(); flash(f'Erreur : {e}','danger')
    return render_template('commande_form.html',commande=c,clients=cls,produits=prods,lignes=ls,moyens=moyens,params=params,mode='edit')

@app.route('/commandes/<int:id>/dupliquer',methods=['POST'])
@login_required
def dupliquer_commande(id):
    db=get_db(); o=db.execute("SELECT * FROM commandes WHERE id=?",(id,)).fetchone()
    if not o: flash('Introuvable.','danger'); return redirect(url_for('commandes'))
    ls=db.execute("SELECT * FROM lignes_commande WHERE commande_id=?",(id,)).fetchall()
    num=next_numero('CMD','commandes','numero')
    try:
        db.execute("INSERT INTO commandes(numero,client_id,moyen_paiement_id,date_commande,statut,remise_globale,notes) VALUES(?,?,?,?,?,?,?)",
            (num,o['client_id'],o['moyen_paiement_id'],date.today().isoformat(),'en_attente',o['remise_globale'],f"Copie de {o['numero']}"))
        db.commit()
        nid=db.execute("SELECT id FROM commandes WHERE numero=?",(num,)).fetchone()['id']
        for l in ls:
            db.execute("INSERT INTO lignes_commande(commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES(?,?,?,?,?,?)",
                (nid,l['produit_id'],l['quantite'],l['prix_unitaire'],l['remise'],l['tva']))
        db.commit(); flash(f'Dupliquée → {num}','success'); return redirect(url_for('voir_commande',id=nid))
    except Exception as e:
        db.rollback(); flash(f'Erreur : {e}','danger'); return redirect(url_for('voir_commande',id=id))

@app.route('/commandes/<int:id>/statut',methods=['POST'])
@login_required
def changer_statut_commande(id):
    db=get_db(); db.execute("UPDATE commandes SET statut=? WHERE id=?",(request.form.get('statut'),id)); db.commit()
    flash('Statut mis à jour.','success'); return redirect(url_for('voir_commande',id=id))

@app.route('/commandes/<int:id>/supprimer',methods=['POST'])
@login_required
def supprimer_commande(id):
    db=get_db()
    for l in db.execute("SELECT * FROM lignes_commande WHERE commande_id=?",(id,)).fetchall():
        db.execute("UPDATE produits SET stock=stock+? WHERE id=?",(l['quantite'],l['produit_id']))
    db.execute("DELETE FROM commandes WHERE id=?",(id,)); db.commit()
    flash('Supprimée.','info'); return redirect(url_for('commandes'))

@app.route('/commandes/<int:id>/ligne/ajouter',methods=['POST'])
@login_required
def ajouter_ligne_commande(id):
    db=get_db(); cmd=db.execute("SELECT statut FROM commandes WHERE id=?",(id,)).fetchone()
    if not cmd or cmd['statut'] in ('livree','annulee'): return jsonify({'error':'Impossible'}),400
    f=request.json or request.form
    try:
        pid=int(f.get('produit_id')); qte=int(f.get('quantite',1))
        db.execute("INSERT INTO lignes_commande(commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES(?,?,?,?,?,?)",
            (id,pid,qte,float(f.get('prix_unitaire',0)),float(f.get('remise',0)),float(f.get('tva',18))))
        db.execute("UPDATE produits SET stock=stock-? WHERE id=?",(qte,pid))
        db.commit(); return jsonify({'ok':True})
    except Exception as e: return jsonify({'error':str(e)}),400

@app.route('/commandes/ligne/<int:lid>/supprimer',methods=['POST'])
@login_required
def supprimer_ligne_commande(lid):
    db=get_db(); l=db.execute("SELECT * FROM lignes_commande WHERE id=?",(lid,)).fetchone()
    if not l: return jsonify({'error':'Introuvable'}),404
    db.execute("UPDATE produits SET stock=stock+? WHERE id=?",(l['quantite'],l['produit_id']))
    db.execute("DELETE FROM lignes_commande WHERE id=?",(lid,)); db.commit(); return jsonify({'ok':True})

@app.route('/commandes/ligne/<int:lid>/modifier',methods=['POST'])
@login_required
def modifier_ligne_commande(lid):
    db=get_db(); l=db.execute("SELECT * FROM lignes_commande WHERE id=?",(lid,)).fetchone()
    if not l: return jsonify({'error':'Introuvable'}),404
    f=request.json or request.form; oq=l['quantite']; nq=int(f.get('quantite',oq))
    try:
        db.execute("UPDATE lignes_commande SET quantite=?,prix_unitaire=?,remise=?,tva=? WHERE id=?",
            (nq,float(f.get('prix_unitaire',l['prix_unitaire'])),float(f.get('remise',l['remise'])),float(f.get('tva',l['tva'])),lid))
        db.execute("UPDATE produits SET stock=stock+? WHERE id=?",(oq-nq,l['produit_id']))
        db.commit(); return jsonify({'ok':True})
    except Exception as e: return jsonify({'error':str(e)}),400

def _save_lignes(db,cid,form,update_stock=True):
    pids=form.getlist('produit_id[]'); qtes=form.getlist('quantite[]')
    pus=form.getlist('prix_unitaire[]'); rems=form.getlist('remise_ligne[]'); tvas=form.getlist('tva_ligne[]')
    for i,pid in enumerate(pids):
        pid=(pid or '').strip()
        if not pid: continue
        qte=int(qtes[i] or 1); pu=float(pus[i] or 0)
        rem=float(rems[i] or 0) if i<len(rems) else 0.0
        tva=float(tvas[i] or 18) if i<len(tvas) else 18.0
        db.execute("INSERT INTO lignes_commande(commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES(?,?,?,?,?,?)",
            (cid,int(pid),qte,pu,rem,tva))
        if update_stock: db.execute("UPDATE produits SET stock=stock-? WHERE id=?",(qte,int(pid)))

# ── FACTURES ──────────────────────────────────────────────────
@app.route('/factures')
@login_required
def factures():
    db=get_db(); statut=request.args.get('statut',''); q=request.args.get('q','')
    query="SELECT f.*,c.nom as client_nom FROM factures f JOIN clients c ON c.id=f.client_id WHERE 1=1"; args=[]
    if statut: query+=" AND f.statut=?"; args.append(statut)
    if q: query+=" AND (f.numero LIKE ? OR c.nom LIKE ?)"; args+=[f'%{q}%',f'%{q}%']
    fs=db.execute(query+" ORDER BY f.created_at DESC",args).fetchall()
    return render_template('factures.html',factures_data=[{'fac':f,'ttc':commande_totaux(f['commande_id'])['ttc'] if f['commande_id'] else 0} for f in fs],
        statut=statut,q=q,params=get_all_params())

def _get_mp_for_commande(commande_id):
    if not commande_id: return None
    db=get_db()
    cmd=db.execute("SELECT moyen_paiement_id FROM commandes WHERE id=?",(commande_id,)).fetchone()
    if cmd and cmd['moyen_paiement_id']:
        return row_to_dict(db.execute("SELECT * FROM moyens_paiement WHERE id=?",(cmd['moyen_paiement_id'],)).fetchone())
    return None

@app.route('/factures/generer/<int:cid>',methods=['POST'])
@login_required
def generer_facture(cid):
    db=get_db()
    if db.execute("SELECT id FROM factures WHERE commande_id=?",(cid,)).fetchone():
        flash('Facture déjà existante.','warning'); return redirect(url_for('voir_commande',id=cid))
    cmd=db.execute("SELECT * FROM commandes WHERE id=?",(cid,)).fetchone()
    num=next_numero('FAC','factures','numero')
    db.execute("INSERT INTO factures(numero,commande_id,client_id,date_facture,date_echeance,statut) VALUES(?,?,?,?,?,?)",
        (num,cid,cmd['client_id'],date.today().isoformat(),(date.today()+timedelta(days=30)).isoformat(),'non_payee'))
    db.commit()
    fid=db.execute("SELECT id FROM factures WHERE numero=?",(num,)).fetchone()['id']
    flash(f'Facture {num} générée !','success'); return redirect(url_for('voir_facture',id=fid))

@app.route('/factures/<int:id>')
@login_required
def voir_facture(id):
    db=get_db()
    fac=db.execute("""SELECT f.*,c.nom as client_nom,c.email as client_email,c.telephone as client_tel,
        c.adresse as client_adresse,c.ville as client_ville,c.pays as client_pays,c.code as client_code
        FROM factures f JOIN clients c ON c.id=f.client_id WHERE f.id=?""",(id,)).fetchone()
    if not fac: flash('Introuvable.','danger'); return redirect(url_for('factures'))
    totaux=commande_totaux(fac['commande_id']) if fac['commande_id'] else {'ht':0,'ht_net':0,'tva':0,'ttc':0,'lignes':[],'remise_globale':0,'remise_montant':0}
    mp=_get_mp_for_commande(fac['commande_id'])
    return render_template('facture_detail.html',facture=fac,totaux=totaux,moyen_paiement=mp,params=get_all_params())

@app.route('/factures/<int:id>/payer',methods=['POST'])
@login_required
def marquer_payee(id):
    db=get_db(); db.execute("UPDATE factures SET statut='payee' WHERE id=?",(id,)); db.commit()
    flash('Payée.','success'); return redirect(url_for('voir_facture',id=id))

@app.route('/factures/<int:id>/annuler',methods=['POST'])
@login_required
def annuler_facture(id):
    db=get_db(); db.execute("UPDATE factures SET statut='annulee' WHERE id=?",(id,)); db.commit()
    flash('Annulée.','info'); return redirect(url_for('voir_facture',id=id))

@app.route('/factures/<int:id>/pdf')
@login_required
def telecharger_facture_pdf(id):
    db=get_db()
    fac=db.execute("""SELECT f.*,c.nom as client_nom,c.email as client_email,c.telephone as client_tel,
        c.adresse as client_adresse,c.ville as client_ville,c.pays as client_pays,c.code as client_code
        FROM factures f JOIN clients c ON c.id=f.client_id WHERE f.id=?""",(id,)).fetchone()
    if not fac: return "Introuvable",404
    totaux=commande_totaux(fac['commande_id']) if fac['commande_id'] else {'ht':0,'ht_net':0,'tva':0,'ttc':0,'lignes':[],'remise_globale':0,'remise_montant':0}
    mp=_get_mp_for_commande(fac['commande_id'])
    pdf=generer_pdf_facture(fac,totaux,get_all_params(),mp)
    return send_file(io.BytesIO(pdf),mimetype='application/pdf',as_attachment=False,download_name=f"Facture-{fac['numero']}.pdf")

# ── STATS ─────────────────────────────────────────────────────
@app.route('/statistiques')
@login_required
def statistiques():
    return render_template('statistiques.html',params=get_all_params(),annee=request.args.get('annee',date.today().year),
        annees=range(date.today().year-3,date.today().year+1))

@app.route('/api/stats/ca_mensuel')
@login_required
def api_ca_mensuel():
    db=get_db(); an=str(request.args.get('annee',date.today().year))
    rows=db.execute("""SELECT strftime('%m',c.date_commande) as m,
        SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY m ORDER BY m""",(an,)).fetchall()
    mois=['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    data={i:0 for i in range(1,13)}
    for r in rows: data[int(r['m'])]=round(float(r['ca'] or 0),2)
    return jsonify({'labels':mois,'values':list(data.values())})

@app.route('/api/stats/top_produits')
@login_required
def api_top_produits():
    db=get_db(); an=str(request.args.get('annee',date.today().year))
    rows=db.execute("""SELECT p.nom,SUM(l.quantite) as qte,SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)) as ca
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id JOIN commandes c ON c.id=l.commande_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY p.id ORDER BY ca DESC LIMIT 8""",(an,)).fetchall()
    return jsonify({'labels':[r['nom'] for r in rows],'qte':[r['qte'] for r in rows],'values':[round(float(r['ca'] or 0),2) for r in rows]})

@app.route('/api/stats/clients_top')
@login_required
def api_clients_top():
    db=get_db(); an=str(request.args.get('annee',date.today().year))
    rows=db.execute("""SELECT cl.nom,COUNT(DISTINCT c.id) as nc,
        SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id JOIN clients cl ON cl.id=c.client_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY cl.id ORDER BY ca DESC LIMIT 8""",(an,)).fetchall()
    return jsonify({'labels':[r['nom'] for r in rows],'ca':[round(float(r['ca'] or 0),2) for r in rows],'cmds':[r['nc'] for r in rows]})

@app.route('/api/stats/statuts_commandes')
@login_required
def api_statuts_commandes():
    db=get_db(); an=str(request.args.get('annee',date.today().year))
    rows=db.execute("SELECT statut,COUNT(*) as nb FROM commandes WHERE strftime('%Y',date_commande)=? GROUP BY statut",(an,)).fetchall()
    lm={'en_attente':'En attente','confirmee':'Confirmée','expediee':'Expédiée','livree':'Livrée','annulee':'Annulée'}
    return jsonify({'labels':[lm.get(r['statut'],r['statut']) for r in rows],'values':[r['nb'] for r in rows]})

@app.route('/api/stats/evolution_clients')
@login_required
def api_evolution_clients():
    db=get_db(); an=str(request.args.get('annee',date.today().year))
    rows=db.execute("SELECT strftime('%m',created_at) as m,COUNT(*) as nb FROM clients WHERE strftime('%Y',created_at)=? GROUP BY m ORDER BY m",(an,)).fetchall()
    mois=['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    data={i:0 for i in range(1,13)}
    for r in rows: data[int(r['m'])]=r['nb']
    return jsonify({'labels':mois,'values':list(data.values())})

@app.route('/api/produit_prix/<int:id>')
@login_required
def produit_prix(id):
    p=get_db().execute("SELECT prix_vente,tva,stock FROM produits WHERE id=?",(id,)).fetchone()
    return jsonify({'prix':p['prix_vente'],'tva':p['tva'],'stock':p['stock']}) if p else (jsonify({}),404)

# ── PARAMÈTRES ────────────────────────────────────────────────
@app.route('/parametres',methods=['GET','POST'])
@login_required
def parametres():
    db=get_db(); params=get_all_params()
    cats=db.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    if request.method=='POST':
        action=request.form.get('action')
        if action=='save_params':
            for key in ['boutique_nom','boutique_adresse','boutique_ville','boutique_pays',
                        'boutique_telephone','boutique_email','boutique_ninea','boutique_rccm',
                        'devise','tva_defaut','couleur_primaire','logo_text']:
                db.execute("INSERT OR REPLACE INTO parametres VALUES(?,?)",(key,request.form.get(key,'')))
            # Logo
            lf=request.files.get('logo_file')
            if lf and lf.filename and lf.filename.rsplit('.',1)[-1].lower() in ALLOWED_EXT:
                old=params.get('logo_filename','')
                if old:
                    op=os.path.join(LOGO_DIR,old)
                    if os.path.exists(op): os.remove(op)
                ext=lf.filename.rsplit('.',1)[1].lower()
                if ext=='jpg': ext='jpeg'
                uid=uuid.uuid4().hex; nfn=f"logo_{uid}.{ext}"; fmt='PNG' if ext=='png' else 'JPEG'
                try:
                    img=PILImage.open(lf.stream).convert('RGBA' if ext=='png' else 'RGB')
                    img.thumbnail((400,200),PILImage.LANCZOS)
                    img.save(os.path.join(LOGO_DIR,nfn),format=fmt,quality=90,optimize=True)
                    db.execute("INSERT OR REPLACE INTO parametres VALUES(?,?)",('logo_filename',nfn))
                except Exception as e: flash(f'Erreur logo : {e}','danger')
            # Mot de passe
            np=request.form.get('new_password','').strip()
            if np:
                cp=request.form.get('confirm_password','').strip()
                if np!=cp: flash('Mots de passe différents.','danger'); return redirect(url_for('parametres'))
                if len(np)<4: flash('Minimum 4 caractères.','danger'); return redirect(url_for('parametres'))
                db.execute("INSERT OR REPLACE INTO parametres VALUES(?,?)",('admin_password',generate_password_hash(np)))
                flash('Mot de passe mis à jour !','success')
            db.commit(); flash('Paramètres enregistrés !','success')
        elif action=='delete_logo':
            old=params.get('logo_filename','')
            if old:
                op=os.path.join(LOGO_DIR,old)
                if os.path.exists(op): os.remove(op)
            db.execute("INSERT OR REPLACE INTO parametres VALUES(?,?)",('logo_filename','')); db.commit(); flash('Logo supprimé.','info')
        elif action=='add_categorie':
            nom=(request.form.get('cat_nom') or '').strip()
            if nom:
                try: db.execute("INSERT INTO categories(nom) VALUES(?)",(nom,)); db.commit(); flash('Catégorie ajoutée !','success')
                except: flash('Existe déjà.','warning')
        elif action=='del_categorie':
            db.execute("DELETE FROM categories WHERE id=?",(request.form.get('cat_id'),)); db.commit(); flash('Supprimée.','info')
        return redirect(url_for('parametres'))
    return render_template('parametres.html',params=params,categories=cats)

# ── PDF ───────────────────────────────────────────────────────
def generer_pdf_facture(facture, totaux, params, moyen_paiement=None):
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=1.5*cm,rightMargin=1.5*cm,topMargin=1.5*cm,bottomMargin=1.5*cm)
    styles=getSampleStyleSheet(); story=[]; devise=params.get('devise','FCFA')
    try:
        hx=params.get('couleur_primaire','#1a56db').lstrip('#')
        primary=colors.Color(*[int(hx[i:i+2],16)/255 for i in (0,2,4)])
    except: primary=colors.HexColor('#1a56db')

    logo_text=params.get('logo_text','MB'); boutique=params.get('boutique_nom','Ma Boutique')
    lf=params.get('logo_filename',''); logo_path=os.path.join(LOGO_DIR,lf) if lf else None
    ninea=params.get('boutique_ninea',''); rccm=params.get('boutique_rccm','')

    # En-tête
    CW=[2.8*cm,9.7*cm,5.5*cm]
    if logo_path and os.path.exists(logo_path):
        with PILImage.open(logo_path) as pi: iw,ih=pi.size
        cw=CW[0]-0.3*cm; ch=1.8*cm; ratio=min(cw/iw,ch/ih)
        logo_cell=RLImage(logo_path,width=iw*ratio,height=ih*ratio)
    else:
        logo_cell=Paragraph(f'<font color="white" size="18"><b>{logo_text}</b></font>',ParagraphStyle('lg',alignment=TA_CENTER))
    hdr=[[logo_cell,
          Paragraph(f'<b><font size="16">{boutique}</font></b><br/>'
                    f'<font size="8.5" color="grey">{params.get("boutique_adresse","")}<br/>'
                    f'{params.get("boutique_ville","")} — {params.get("boutique_pays","")}<br/>'
                    f'Tél : {params.get("boutique_telephone","")}<br/>Email : {params.get("boutique_email","")}</font>',styles['Normal']),
          Paragraph(f'<font size="20" color="white"><b>FACTURE</b></font><br/>'
                    f'<font size="10" color="white"><b>N° {facture["numero"]}</b></font>',ParagraphStyle('fac',alignment=TA_RIGHT))]]
    ht=Table(hdr,colWidths=CW)
    ht.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,0),primary),('BACKGROUND',(2,0),(2,0),primary),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(0,0),'CENTER'),
        ('LEFTPADDING',(0,0),(0,0),4),('RIGHTPADDING',(0,0),(0,0),4),
        ('TOPPADDING',(0,0),(0,0),5),('BOTTOMPADDING',(0,0),(0,0),5),
        ('LEFTPADDING',(1,0),(1,0),10),('RIGHTPADDING',(2,0),(2,0),10),
        ('TOPPADDING',(1,0),(-1,-1),12),('BOTTOMPADDING',(1,0),(-1,-1),12),
    ]))
    story.append(ht); story.append(Spacer(1,0.4*cm))

    statut_txt='✓ PAYÉE' if facture['statut']=='payee' else 'NON PAYÉE'
    info=[[Paragraph(f'<font size="8" color="grey">{ninea}<br/>{rccm}</font>',styles['Normal']),
           Paragraph(f'<b>Facturé à :</b><br/><b>{facture["client_nom"]}</b><br/>'
                     f'{facture["client_adresse"] or ""}<br/>{facture["client_ville"] or ""}'
                     f'{" — "+facture["client_pays"] if facture["client_pays"] else ""}<br/>'
                     f'Code : {facture["client_code"] or ""}',ParagraphStyle('cl',leftIndent=8)),
           Paragraph(f'<b>Date :</b> {facture["date_facture"] or date.today().isoformat()}<br/>'
                     f'<b>Échéance :</b> {facture["date_echeance"] or ""}<br/>'
                     f'<b>Statut :</b> {statut_txt}',ParagraphStyle('dt',alignment=TA_RIGHT))]]
    it=Table(info,colWidths=[6*cm,7*cm,5.5*cm])
    it.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4)]))
    story.append(it); story.append(Spacer(1,0.5*cm))

    # Lignes
    th=ParagraphStyle('th',alignment=TA_CENTER,fontSize=9,textColor=colors.white,fontName='Helvetica-Bold')
    td=ParagraphStyle('td',fontSize=9); tr2=ParagraphStyle('tr2',fontSize=9,alignment=TA_RIGHT)
    tbl=[[Paragraph(h,th) for h in ['#','Désignation','Qté','P.U. HT','Rem.','TVA','Total HT']]]
    for i,l in enumerate(totaux['lignes'],1):
        pu=float(l['prix_unitaire']); q=int(l['quantite']); rem=float(l['remise']); tv=float(l['tva'])
        tbl.append([Paragraph(str(i),ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
                    Paragraph(str(l['produit_nom']),td),
                    Paragraph(str(q),ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
                    Paragraph(f"{pu:,.0f} {devise}",tr2),
                    Paragraph(f"{rem:.0f}%",ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
                    Paragraph(f"{tv:.0f}%",ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
                    Paragraph(f"{q*pu*(1-rem/100):,.0f} {devise}",tr2)])
    lt=Table(tbl,colWidths=[0.8*cm,6.8*cm,1.2*cm,3.1*cm,1.3*cm,1.3*cm,3.5*cm])
    lt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),primary),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f8faff'),colors.white]),
        ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#e5e7eb')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(lt); story.append(Spacer(1,0.4*cm))

    # Totaux + QR
    rg=totaux['remise_globale']; hn=totaux['ht_net']; tvn=totaux['tva']; ttc=totaux['ttc']
    tot_rows=[]
    if rg>0:
        tot_rows+=[['','Sous-total HT',f"{totaux['ht']:,.0f} {devise}"],
                   ['',f'Remise ({rg:.0f}%)',f"-{totaux['ht']*rg/100:,.0f} {devise}"]]
    tot_rows+=[['','Total HT',f"{hn:,.0f} {devise}"],['','TVA',f"{tvn:,.0f} {devise}"],
               ['',Paragraph('<b>TOTAL TTC</b>',ParagraphStyle('tt',fontName='Helvetica-Bold',fontSize=11)),
                Paragraph(f'<b>{ttc:,.0f} {devise}</b>',ParagraphStyle('ttv',fontName='Helvetica-Bold',fontSize=11,alignment=TA_RIGHT))]]

    qr_block=None
    if moyen_paiement:
        mp_nom=moyen_paiement.get('nom','')
        mp_type=moyen_paiement.get('type_paiement','mobile') or 'mobile'
        mp_tel=moyen_paiement.get('telephone','') or ''
        try:
            mhx=(moyen_paiement.get('couleur','#1B73E8') or '#1B73E8').lstrip('#')
            mp_col=colors.Color(*[int(mhx[i:i+2],16)/255 for i in (0,2,4)])
        except: mp_col=colors.HexColor('#1B73E8')

        qr_path=None
        if moyen_paiement.get('qr_filename'):
            p=os.path.join(QR_DIR,moyen_paiement['qr_filename'])
            if os.path.exists(p): qr_path=p

        QRS=3.8*cm
        rows_qr=[]

        if qr_path:
            rows_qr.append([RLImage(qr_path,width=QRS,height=QRS)])

        if mp_type=='bancaire':
            # Bank info block
            iban=moyen_paiement.get('banque_iban','') or ''
            swift=moyen_paiement.get('banque_swift','') or ''
            bnom=moyen_paiement.get('banque_nom','') or ''
            btit=moyen_paiement.get('banque_titulaire','') or ''
            bage=moyen_paiement.get('banque_agence','') or ''
            lines=[f'<b>🏦 Virement bancaire</b><br/><b>{mp_nom}</b>']
            if btit: lines.append(f'Titulaire: <b>{btit}</b>')
            if bnom: lines.append(f'Banque: {bnom}')
            if bage: lines.append(f'Agence: {bage}')
            if iban: lines.append(f'IBAN/Compte: <b>{iban}</b>')
            if swift: lines.append(f'SWIFT/BIC: <b>{swift}</b>')
            if mp_tel: lines.append(f'📞 {mp_tel}')
            txt='<br/>'.join(lines)
            lbl=Paragraph(f'<font size="7.5">{txt}</font>',
                ParagraphStyle('bklbl',alignment=TA_LEFT,leading=11,textColor=mp_col))
            rows_qr.append([lbl])
        else:
            # Mobile money
            qr_txt=f'<font size="8.5"><b>📱 Scannez et Payez<br/>par {mp_nom}</b></font>'
            if mp_tel: qr_txt+=f'<br/><font size="8" color="grey">📞 {mp_tel}</font>'
            rows_qr.append([Paragraph(qr_txt,
                ParagraphStyle('qrl',alignment=TA_CENTER,leading=13,textColor=mp_col,fontName='Helvetica-Bold'))])

        if rows_qr:
            qr_block=Table(rows_qr,colWidths=[4.4*cm])
            qr_block.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),4),
                ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
                ('BOX',(0,0),(-1,-1),1,mp_col),
                ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f8fbff')),
            ]))

    if qr_block:
        QC=4.6*cm; TC=18*cm-QC
        tt2=Table(tot_rows,colWidths=[TC-9*cm,5*cm,4*cm])
        tt2.setStyle(TableStyle([
            ('ALIGN',(1,0),(2,-1),'RIGHT'),('LINEABOVE',(1,-1),(2,-1),1,primary),
            ('BACKGROUND',(1,-1),(2,-1),colors.HexColor('#f0f4ff')),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('GRID',(1,0),(2,-1),0.3,colors.HexColor('#e5e7eb')),
        ]))
        combined=Table([[qr_block,tt2]],colWidths=[QC,TC])
        combined.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(0,0),(0,0),10),
            ('LEFTPADDING',(1,0),(1,0),0),
        ]))
        story.append(combined)
    else:
        tt2=Table(tot_rows,colWidths=[9.5*cm,5*cm,4*cm])
        tt2.setStyle(TableStyle([
            ('ALIGN',(1,0),(2,-1),'RIGHT'),('LINEABOVE',(1,-1),(2,-1),1,primary),
            ('BACKGROUND',(1,-1),(2,-1),colors.HexColor('#f0f4ff')),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('GRID',(1,0),(2,-1),0.3,colors.HexColor('#e5e7eb')),
        ]))
        story.append(tt2)

    notes=facture['notes'] if not isinstance(facture,dict) else facture.get('notes','')
    if notes: story.append(Spacer(1,0.4*cm)); story.append(Paragraph(f"<b>Notes :</b> {notes}",styles['Normal']))
    story.append(Spacer(1,1*cm))
    story.append(HRFlowable(width="100%",thickness=0.5,color=colors.lightgrey)); story.append(Spacer(1,0.2*cm))
    footer=f"{boutique} | {params.get('boutique_adresse','')} | Tél : {params.get('boutique_telephone','')} | {ninea} | {rccm}"
    story.append(Paragraph(f'<font size="7" color="grey">{footer}</font>',ParagraphStyle('ft',alignment=TA_CENTER)))
    doc.build(story); return buf.getvalue()

if __name__=='__main__':
    init_db()
    print("\n"+"═"*56+"\n  🏪  GESTION COMMERCIALE v4.0\n"+"═"*56)
    print("  ➜  http://127.0.0.1:5000\n  🔐  Mot de passe par défaut: 123456\n  💳  QR Paiement sur PDF\n"+"═"*56+"\n")
    app.run(debug=False,port=5000)
