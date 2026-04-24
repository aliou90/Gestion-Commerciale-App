"""
Gestion Commerciale — Flask v3.0
Nouveautés : images produit (multi-upload, galerie, drag-reorder) + logo boutique
"""

import os, sqlite3, json, io, uuid
from datetime import datetime, date, timedelta
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, send_file, g, send_from_directory)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from PIL import Image as PILImage
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "gc_secret_v3_2024"
DB_PATH     = os.path.join(os.path.dirname(__file__), "database.db")
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "static", "uploads")
PRODUIT_DIR = os.path.join(UPLOAD_ROOT, "produits")
THUMB_DIR   = os.path.join(UPLOAD_ROOT, "thumbs")
LOGO_DIR    = os.path.join(UPLOAD_ROOT, "logo")
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
THUMB_SIZE  = (320, 320)
MAX_IMG_SIZE= (1200, 1200)

for d in [PRODUIT_DIR, THUMB_DIR, LOGO_DIR]:
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════
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

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS parametres (cle TEXT PRIMARY KEY, valeur TEXT);
    CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL UNIQUE);
    CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL,
        description TEXT,
        categorie_id INTEGER REFERENCES categories(id),
        prix_achat REAL DEFAULT 0,
        prix_vente REAL NOT NULL,
        tva REAL DEFAULT 18,
        stock INTEGER DEFAULT 0,
        stock_min INTEGER DEFAULT 5,
        unite TEXT DEFAULT 'unité',
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS produit_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        thumb_filename TEXT NOT NULL,
        principale INTEGER DEFAULT 0,
        ordre INTEGER DEFAULT 0,
        alt_text TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        nom TEXT NOT NULL,
        prenom TEXT,
        email TEXT,
        telephone TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT DEFAULT 'Sénégal',
        type_client TEXT DEFAULT 'particulier',
        remise REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL REFERENCES clients(id),
        date_commande TEXT DEFAULT (datetime('now')),
        date_livraison TEXT,
        statut TEXT DEFAULT 'en_attente',
        remise_globale REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS lignes_commande (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        commande_id INTEGER NOT NULL REFERENCES commandes(id) ON DELETE CASCADE,
        produit_id INTEGER NOT NULL REFERENCES produits(id),
        quantite INTEGER NOT NULL DEFAULT 1,
        prix_unitaire REAL NOT NULL,
        remise REAL DEFAULT 0,
        tva REAL DEFAULT 18
    );
    CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL UNIQUE,
        commande_id INTEGER REFERENCES commandes(id),
        client_id INTEGER NOT NULL REFERENCES clients(id),
        date_facture TEXT DEFAULT (datetime('now')),
        date_echeance TEXT,
        statut TEXT DEFAULT 'non_payee',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    defaults = {
        'boutique_nom': 'Ma Boutique', 'boutique_adresse': '123 Rue du Commerce',
        'boutique_ville': 'Dakar', 'boutique_pays': 'Sénégal',
        'boutique_telephone': '+221 77 000 00 00', 'boutique_email': 'contact@maboutique.sn',
        'boutique_ninea': 'NINEA: 000000000', 'boutique_rccm': 'RCCM: DKR-2024-B-00000',
        'devise': 'FCFA', 'tva_defaut': '18', 'couleur_primaire': '#1a56db',
        'logo_text': 'MB', 'logo_filename': '',
    }
    for k, v in defaults.items():
        db.execute("INSERT OR IGNORE INTO parametres VALUES (?,?)", (k, v))
    for cat in ['Électronique','Vêtements','Alimentation','Fournitures','Cosmétiques']:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (cat,))
    db.commit(); db.close()

def get_param(cle, defaut=''):
    r = get_db().execute("SELECT valeur FROM parametres WHERE cle=?", (cle,)).fetchone()
    return r['valeur'] if r else defaut

def get_all_params():
    rows = get_db().execute("SELECT cle, valeur FROM parametres").fetchall()
    return {r['cle']: r['valeur'] for r in rows}

def next_numero(prefix, table, col):
    today = date.today().strftime('%Y%m')
    r = get_db().execute(f"SELECT COUNT(*) as c FROM {table} WHERE {col} LIKE ?",
                         (f"{prefix}-{today}-%",)).fetchone()
    return f"{prefix}-{today}-{r['c']+1:04d}"

def commande_totaux(commande_id):
    db = get_db()
    lignes = db.execute("""
        SELECT l.*, p.nom as produit_nom, p.reference as produit_ref
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id
        WHERE l.commande_id=? ORDER BY l.id
    """, (commande_id,)).fetchall()
    cmd = db.execute("SELECT remise_globale FROM commandes WHERE id=?", (commande_id,)).fetchone()
    rg = float(cmd['remise_globale']) if cmd else 0.0
    ht = sum(l['quantite']*l['prix_unitaire']*(1-l['remise']/100) for l in lignes)
    tv = sum(l['quantite']*l['prix_unitaire']*(1-l['remise']/100)*l['tva']/100 for l in lignes)
    return {'ht': ht, 'ht_net': ht*(1-rg/100), 'tva': tv*(1-rg/100),
            'ttc': ht*(1-rg/100)+tv*(1-rg/100), 'remise_globale': rg,
            'remise_montant': ht*rg/100, 'lignes': lignes}

# ══════════════════════════════════════════════════════════════
#  IMAGE HELPERS
# ══════════════════════════════════════════════════════════════
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_image(file_obj, dest_dir=None, thumb_dir=None, max_size=None, thumb_size=None):
    """Sauvegarde image + miniature. Retourne (filename, thumb_filename) ou None."""
    if dest_dir is None:  dest_dir  = PRODUIT_DIR
    if thumb_dir is None: thumb_dir = THUMB_DIR
    if max_size is None:  max_size  = MAX_IMG_SIZE
    if thumb_size is None: thumb_size = THUMB_SIZE
    if not file_obj or not file_obj.filename or not allowed_file(file_obj.filename):
        return None
    ext = file_obj.filename.rsplit('.', 1)[1].lower()
    if ext == 'jpg': ext = 'jpeg'
    uid = uuid.uuid4().hex
    filename = f"{uid}.{ext}"; thumb_filename = f"th_{uid}.{ext}"
    save_fmt = 'PNG' if ext == 'png' else 'JPEG'
    try:
        img = PILImage.open(file_obj.stream).convert('RGBA' if ext == 'png' else 'RGB')
        img.thumbnail(max_size, PILImage.LANCZOS)
        img.save(os.path.join(dest_dir, filename), format=save_fmt, quality=88, optimize=True)
        # Thumb carré centré
        th = img.copy(); th.thumbnail(thumb_size, PILImage.LANCZOS)
        w, h = th.size; s = min(w, h)
        th = th.crop(((w-s)//2, (h-s)//2, (w-s)//2+s, (h-s)//2+s))
        th.save(os.path.join(thumb_dir, thumb_filename), format=save_fmt, quality=82, optimize=True)
        return filename, thumb_filename
    except Exception as e:
        print(f"[img] {e}"); return None

def delete_image_files(filename, thumb_filename, dest_dir=None, thumb_dir=None):
    if dest_dir is None:  dest_dir  = PRODUIT_DIR
    if thumb_dir is None: thumb_dir = THUMB_DIR
    for p in [os.path.join(dest_dir, filename), os.path.join(thumb_dir, thumb_filename)]:
        try:
            if os.path.exists(p): os.remove(p)
        except: pass

def get_produit_images(produit_id):
    return rows_to_list(get_db().execute(
        "SELECT * FROM produit_images WHERE produit_id=? ORDER BY principale DESC, ordre ASC, id ASC",
        (produit_id,)).fetchall())

def get_produit_image_principale(produit_id):
    db = get_db()
    row = db.execute("SELECT * FROM produit_images WHERE produit_id=? AND principale=1 LIMIT 1", (produit_id,)).fetchone()
    if not row:
        row = db.execute("SELECT * FROM produit_images WHERE produit_id=? ORDER BY ordre,id LIMIT 1", (produit_id,)).fetchone()
    return row_to_dict(row)

def get_logo_url(params=None):
    """Retourne l'URL du logo ou None. Priorité : logo uploadé > initiales."""
    if params is None: params = get_all_params()
    lf = params.get('logo_filename', '')
    if lf and os.path.exists(os.path.join(LOGO_DIR, lf)):
        return f"/uploads/logo/{lf}"
    return None

# ══════════════════════════════════════════════════════════════
#  CONTEXT PROCESSOR
# ══════════════════════════════════════════════════════════════
@app.context_processor
def inject_globals():
    params   = get_all_params()
    logo_url = get_logo_url(params)
    return {
        'now': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'now_date': date.today().isoformat(),
        'today': date.today().isoformat(),
        'logo_url': logo_url,
    }

# ══════════════════════════════════════════════════════════════
#  FILTRES JINJA
# ══════════════════════════════════════════════════════════════
@app.template_filter('fmt_currency')
def fmt_currency(val, devise='FCFA'):
    try: return f"{float(val):,.0f} {devise}".replace(',', '\u202f')
    except: return f"0 {devise}"

@app.template_filter('fmt_date')
def fmt_date(val):
    if not val: return ''
    try: return datetime.fromisoformat(str(val)[:10]).strftime('%d/%m/%Y')
    except: return str(val)[:10]

@app.template_filter('statut_badge')
def statut_badge(statut):
    m = {'en_attente':('bg-y','⏳ En attente'),'confirmee':('bg-b','✓ Confirmée'),
         'expediee':('bg-v','🚚 Expédiée'),'livree':('bg-g','✅ Livrée'),
         'annulee':('bg-r','✗ Annulée'),'payee':('bg-g','✅ Payée'),
         'non_payee':('bg-r','⚠ Non payée'),'partiellement_payee':('bg-o','◑ Partielle')}
    cls, label = m.get(statut, ('bg-gr', statut))
    return f'<span class="badge {cls}">{label}</span>'

# ══════════════════════════════════════════════════════════════
#  STATIC ROUTES
# ══════════════════════════════════════════════════════════════
@app.route('/uploads/produits/<filename>')
def uploaded_produit(filename):
    return send_from_directory(PRODUIT_DIR, filename)

@app.route('/uploads/thumbs/<filename>')
def uploaded_thumb(filename):
    return send_from_directory(THUMB_DIR, filename)

@app.route('/uploads/logo/<filename>')
def uploaded_logo(filename):
    return send_from_directory(LOGO_DIR, filename)

# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════
@app.route('/')
def dashboard():
    db = get_db(); mois = date.today().strftime('%Y-%m')
    stats = {
        'nb_produits':   db.execute("SELECT COUNT(*) FROM produits WHERE actif=1").fetchone()[0],
        'nb_clients':    db.execute("SELECT COUNT(*) FROM clients WHERE actif=1").fetchone()[0],
        'nb_commandes':  db.execute("SELECT COUNT(*) FROM commandes").fetchone()[0],
        'nb_factures':   db.execute("SELECT COUNT(*) FROM factures").fetchone()[0],
        'stock_alerte':  db.execute("SELECT COUNT(*) FROM produits WHERE stock<=stock_min AND actif=1").fetchone()[0],
        'cmd_attente':   db.execute("SELECT COUNT(*) FROM commandes WHERE statut='en_attente'").fetchone()[0],
        'fact_impayees': db.execute("SELECT COUNT(*) FROM factures WHERE statut='non_payee'").fetchone()[0],
    }
    r = db.execute("""SELECT COALESCE(SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)),0) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id WHERE strftime('%Y-%m',c.date_commande)=?""", (mois,)).fetchone()
    stats['ca_mois'] = r['ca'] if r else 0
    recent_cmds = db.execute("""SELECT c.*, cl.nom as client_nom FROM commandes c
        JOIN clients cl ON cl.id=c.client_id ORDER BY c.created_at DESC LIMIT 6""").fetchall()
    top_produits_raw = db.execute("""SELECT p.id, p.nom, SUM(l.quantite) as qte,
               SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)) as ca
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id
        JOIN commandes c ON c.id=l.commande_id WHERE strftime('%Y-%m',c.date_commande)=?
        GROUP BY p.id ORDER BY ca DESC LIMIT 5""", (mois,)).fetchall()
    top_produits = [{'p': dict(p), 'img': get_produit_image_principale(p['id'])} for p in top_produits_raw]
    params = get_all_params()
    return render_template('dashboard.html', stats=stats, recent_cmds=recent_cmds,
                           top_produits=top_produits, params=params)

# ══════════════════════════════════════════════════════════════
#  PRODUITS
# ══════════════════════════════════════════════════════════════
@app.route('/produits')
def produits():
    db = get_db(); q = request.args.get('q',''); cat = request.args.get('cat','')
    query = "SELECT p.*, c.nom as cat_nom FROM produits p LEFT JOIN categories c ON c.id=p.categorie_id WHERE p.actif=1"
    args = []
    if q: query += " AND (p.nom LIKE ? OR p.reference LIKE ?)"; args += [f'%{q}%',f'%{q}%']
    if cat: query += " AND p.categorie_id=?"; args.append(cat)
    query += " ORDER BY p.nom"
    produits_list = db.execute(query, args).fetchall()
    produits_data = [{'p': dict(p), 'img': get_produit_image_principale(p['id'])} for p in produits_list]
    categories = db.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    params = get_all_params()
    return render_template('produits.html', produits_data=produits_data,
                           categories=categories, q=q, cat=cat, params=params)

@app.route('/produits/nouveau', methods=['GET','POST'])
def nouveau_produit():
    db = get_db(); categories = db.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    params = get_all_params()
    if request.method == 'POST':
        f   = request.form
        ref = (f.get('reference') or '').strip() or f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            db.execute("""INSERT INTO produits (reference,nom,description,categorie_id,prix_achat,prix_vente,tva,stock,stock_min,unite)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (ref, f['nom'], f.get('description') or None, f.get('categorie_id') or None,
                 float(f.get('prix_achat',0) or 0), float(f['prix_vente']),
                 float(f.get('tva', get_param('tva_defaut','18')) or 18),
                 int(f.get('stock',0) or 0), int(f.get('stock_min',5) or 5), f.get('unite','unité')))
            db.commit()
            pid = db.execute("SELECT id FROM produits WHERE reference=?", (ref,)).fetchone()['id']
            _process_uploaded_images(db, pid, request.files)
            db.commit()
            flash('Produit créé avec succès !', 'success')
            return redirect(url_for('produits'))
        except Exception as e:
            flash(f'Erreur : {e}', 'danger')
    return render_template('produit_form.html', produit=None, images=[],
                           categories=categories, params=params)

@app.route('/produits/<int:id>/modifier', methods=['GET','POST'])
def modifier_produit(id):
    db = get_db(); produit = db.execute("SELECT * FROM produits WHERE id=?", (id,)).fetchone()
    categories = db.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    params = get_all_params()
    if not produit: flash('Produit introuvable.','danger'); return redirect(url_for('produits'))
    if request.method == 'POST':
        f = request.form
        try:
            db.execute("""UPDATE produits SET reference=?,nom=?,description=?,categorie_id=?,
                prix_achat=?,prix_vente=?,tva=?,stock=?,stock_min=?,unite=? WHERE id=?""",
                (f['reference'],f['nom'],f.get('description') or None,f.get('categorie_id') or None,
                 float(f.get('prix_achat',0) or 0),float(f['prix_vente']),float(f.get('tva',18) or 18),
                 int(f.get('stock',0) or 0),int(f.get('stock_min',5) or 5),f.get('unite','unité'),id))
            _process_uploaded_images(db, id, request.files)
            pid = f.get('principale_id')
            if pid:
                db.execute("UPDATE produit_images SET principale=0 WHERE produit_id=?", (id,))
                db.execute("UPDATE produit_images SET principale=1 WHERE id=? AND produit_id=?", (pid,id))
            db.commit()
            flash('Produit modifié !','success'); return redirect(url_for('produits'))
        except Exception as e:
            flash(f'Erreur : {e}','danger')
    images = get_produit_images(id)
    return render_template('produit_form.html', produit=produit, images=images,
                           categories=categories, params=params)

def _process_uploaded_images(db, produit_id, files):
    uploaded = files.getlist('images[]')
    existing = db.execute("SELECT COUNT(*) as c FROM produit_images WHERE produit_id=?", (produit_id,)).fetchone()['c']
    for i, fo in enumerate(uploaded):
        result = save_image(fo)
        if result:
            fn, tfn = result
            db.execute("INSERT INTO produit_images (produit_id,filename,thumb_filename,principale,ordre) VALUES (?,?,?,?,?)",
                       (produit_id, fn, tfn, 1 if (existing == 0 and i == 0) else 0, existing+i))

@app.route('/produits/<int:id>/supprimer', methods=['POST'])
def supprimer_produit(id):
    db = get_db(); db.execute("UPDATE produits SET actif=0 WHERE id=?", (id,)); db.commit()
    flash('Produit archivé.','info'); return redirect(url_for('produits'))

@app.route('/produits/image/<int:img_id>/supprimer', methods=['POST'])
def supprimer_image_produit(img_id):
    db = get_db(); img = db.execute("SELECT * FROM produit_images WHERE id=?", (img_id,)).fetchone()
    if not img: return jsonify({'error':'Image introuvable'}), 404
    delete_image_files(img['filename'], img['thumb_filename'])
    db.execute("DELETE FROM produit_images WHERE id=?", (img_id,))
    if img['principale']:
        nxt = db.execute("SELECT id FROM produit_images WHERE produit_id=? ORDER BY ordre,id LIMIT 1", (img['produit_id'],)).fetchone()
        if nxt: db.execute("UPDATE produit_images SET principale=1 WHERE id=?", (nxt['id'],))
    db.commit(); return jsonify({'ok':True})

@app.route('/produits/image/<int:img_id>/principale', methods=['POST'])
def set_image_principale(img_id):
    db = get_db(); img = db.execute("SELECT * FROM produit_images WHERE id=?", (img_id,)).fetchone()
    if not img: return jsonify({'error':'Image introuvable'}), 404
    db.execute("UPDATE produit_images SET principale=0 WHERE produit_id=?", (img['produit_id'],))
    db.execute("UPDATE produit_images SET principale=1 WHERE id=?", (img_id,))
    db.commit(); return jsonify({'ok':True})

@app.route('/produits/<int:produit_id>/images/reorder', methods=['POST'])
def reorder_images(produit_id):
    ids = (request.json or {}).get('ids', []); db = get_db()
    for i, iid in enumerate(ids):
        db.execute("UPDATE produit_images SET ordre=? WHERE id=? AND produit_id=?", (i, iid, produit_id))
    db.commit(); return jsonify({'ok':True})

@app.route('/produits/<int:id>/detail')
def detail_produit(id):
    db = get_db()
    p  = db.execute("SELECT p.*, c.nom as cat_nom FROM produits p LEFT JOIN categories c ON c.id=p.categorie_id WHERE p.id=?", (id,)).fetchone()
    if not p: return jsonify({'error':'Introuvable'}), 404
    return jsonify({'produit': row_to_dict(p), 'images': get_produit_images(id)})

# ══════════════════════════════════════════════════════════════
#  CLIENTS
# ══════════════════════════════════════════════════════════════
@app.route('/clients')
def clients():
    db = get_db(); q = request.args.get('q','')
    query = "SELECT * FROM clients WHERE actif=1"; args = []
    if q: query += " AND (nom LIKE ? OR code LIKE ? OR email LIKE ? OR telephone LIKE ?)"; args += [f'%{q}%']*4
    query += " ORDER BY nom"
    return render_template('clients.html', clients=db.execute(query,args).fetchall(), q=q, params=get_all_params())

@app.route('/clients/nouveau', methods=['GET','POST'])
def nouveau_client():
    db = get_db(); params = get_all_params()
    if request.method == 'POST':
        f = request.form; code = (f.get('code') or '').strip() or f"CLI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            db.execute("INSERT INTO clients (code,nom,prenom,email,telephone,adresse,ville,pays,type_client,remise) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (code,f['nom'],f.get('prenom') or None,f.get('email') or None,f.get('telephone') or None,
                 f.get('adresse') or None,f.get('ville') or None,f.get('pays','Sénégal'),f.get('type_client','particulier'),float(f.get('remise',0) or 0)))
            db.commit(); flash('Client créé !','success'); return redirect(url_for('clients'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('client_form.html', client=None, params=params)

@app.route('/clients/<int:id>/modifier', methods=['GET','POST'])
def modifier_client(id):
    db = get_db(); client = db.execute("SELECT * FROM clients WHERE id=?", (id,)).fetchone(); params = get_all_params()
    if not client: flash('Client introuvable.','danger'); return redirect(url_for('clients'))
    if request.method == 'POST':
        f = request.form
        try:
            db.execute("UPDATE clients SET code=?,nom=?,prenom=?,email=?,telephone=?,adresse=?,ville=?,pays=?,type_client=?,remise=? WHERE id=?",
                (f['code'],f['nom'],f.get('prenom') or None,f.get('email') or None,f.get('telephone') or None,
                 f.get('adresse') or None,f.get('ville') or None,f.get('pays','Sénégal'),f.get('type_client','particulier'),float(f.get('remise',0) or 0),id))
            db.commit(); flash('Client modifié !','success'); return redirect(url_for('clients'))
        except Exception as e: flash(f'Erreur : {e}','danger')
    return render_template('client_form.html', client=client, params=params)

@app.route('/clients/<int:id>/supprimer', methods=['POST'])
def supprimer_client(id):
    db = get_db(); db.execute("UPDATE clients SET actif=0 WHERE id=?", (id,)); db.commit()
    flash('Client archivé.','info'); return redirect(url_for('clients'))

# ══════════════════════════════════════════════════════════════
#  COMMANDES
# ══════════════════════════════════════════════════════════════
@app.route('/commandes')
def commandes():
    db = get_db(); statut = request.args.get('statut',''); q = request.args.get('q','')
    query = "SELECT c.*, cl.nom as client_nom FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE 1=1"; args = []
    if statut: query += " AND c.statut=?"; args.append(statut)
    if q: query += " AND (c.numero LIKE ? OR cl.nom LIKE ?)"; args += [f'%{q}%',f'%{q}%']
    query += " ORDER BY c.created_at DESC"
    commandes_list = db.execute(query, args).fetchall()
    commandes_data = [{'cmd':c,'ttc':commande_totaux(c['id'])['ttc']} for c in commandes_list]
    return render_template('commandes.html', commandes_data=commandes_data, statut=statut, q=q, params=get_all_params())

def _build_produits_for_form():
    db = get_db()
    raw = db.execute("SELECT id,nom,reference,prix_vente,tva,stock,unite FROM produits WHERE actif=1 ORDER BY nom").fetchall()
    result = rows_to_list(raw)
    for p in result:
        img = get_produit_image_principale(p['id'])
        p['thumb'] = f"/uploads/thumbs/{img['thumb_filename']}" if img else None
    return result

@app.route('/commandes/nouvelle', methods=['GET','POST'])
def nouvelle_commande():
    db = get_db()
    clients_list = db.execute("SELECT id,code,nom,prenom FROM clients WHERE actif=1 ORDER BY nom").fetchall()
    produits_list = _build_produits_for_form(); params = get_all_params()
    if request.method == 'POST':
        f = request.form; numero = next_numero('CMD','commandes','numero')
        try:
            db.execute("INSERT INTO commandes (numero,client_id,date_commande,date_livraison,statut,remise_globale,notes) VALUES (?,?,?,?,?,?,?)",
                (numero,int(f['client_id']),f.get('date_commande') or date.today().isoformat(),
                 f.get('date_livraison') or None,f.get('statut','en_attente'),float(f.get('remise_globale',0) or 0),f.get('notes') or None))
            db.commit()
            cmd_id = db.execute("SELECT id FROM commandes WHERE numero=?", (numero,)).fetchone()['id']
            _save_lignes(db, cmd_id, request.form, update_stock=True); db.commit()
            flash(f'Commande {numero} créée !','success'); return redirect(url_for('voir_commande', id=cmd_id))
        except Exception as e: db.rollback(); flash(f'Erreur : {e}','danger')
    return render_template('commande_form.html', commande=None, clients=clients_list,
                           produits=produits_list, lignes=[], params=params, mode='new')

@app.route('/commandes/<int:id>')
def voir_commande(id):
    db = get_db()
    commande = db.execute("""SELECT c.*, cl.nom as client_nom, cl.email as client_email, cl.telephone as client_tel,
               cl.adresse as client_adresse, cl.ville as client_ville, cl.pays as client_pays, cl.code as client_code
        FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE c.id=?""", (id,)).fetchone()
    if not commande: flash('Commande introuvable.','danger'); return redirect(url_for('commandes'))
    totaux  = commande_totaux(id)
    facture = db.execute("SELECT * FROM factures WHERE commande_id=?", (id,)).fetchone()
    return render_template('commande_detail.html', commande=commande, totaux=totaux,
                           facture=facture, params=get_all_params())

@app.route('/commandes/<int:id>/modifier', methods=['GET','POST'])
def modifier_commande(id):
    db = get_db()
    commande = db.execute("SELECT c.*, cl.nom as client_nom FROM commandes c JOIN clients cl ON cl.id=c.client_id WHERE c.id=?", (id,)).fetchone()
    if not commande: flash('Commande introuvable.','danger'); return redirect(url_for('commandes'))
    if commande['statut'] in ('livree','annulee'):
        flash(f'Impossible de modifier une commande {commande["statut"]}.','warning')
        return redirect(url_for('voir_commande', id=id))
    clients_list  = db.execute("SELECT id,code,nom,prenom FROM clients WHERE actif=1 ORDER BY nom").fetchall()
    produits_list = _build_produits_for_form()
    lignes = rows_to_list(db.execute("SELECT l.*, p.nom as produit_nom FROM lignes_commande l JOIN produits p ON p.id=l.produit_id WHERE l.commande_id=?", (id,)).fetchall())
    params = get_all_params()
    if request.method == 'POST':
        f = request.form
        try:
            for l in db.execute("SELECT produit_id,quantite FROM lignes_commande WHERE commande_id=?", (id,)).fetchall():
                db.execute("UPDATE produits SET stock=stock+? WHERE id=?", (l['quantite'],l['produit_id']))
            db.execute("UPDATE commandes SET client_id=?,date_commande=?,date_livraison=?,statut=?,remise_globale=?,notes=? WHERE id=?",
                (int(f['client_id']),f.get('date_commande') or date.today().isoformat(),f.get('date_livraison') or None,
                 f.get('statut','en_attente'),float(f.get('remise_globale',0) or 0),f.get('notes') or None,id))
            db.execute("DELETE FROM lignes_commande WHERE commande_id=?", (id,))
            _save_lignes(db, id, request.form, update_stock=True); db.commit()
            db.execute("DELETE FROM factures WHERE commande_id=? AND statut='non_payee'", (id,)); db.commit()
            flash('Commande mise à jour !','success'); return redirect(url_for('voir_commande', id=id))
        except Exception as e: db.rollback(); flash(f'Erreur : {e}','danger')
    return render_template('commande_form.html', commande=commande, clients=clients_list,
                           produits=produits_list, lignes=lignes, params=params, mode='edit')

@app.route('/commandes/<int:id>/dupliquer', methods=['POST'])
def dupliquer_commande(id):
    db = get_db(); origine = db.execute("SELECT * FROM commandes WHERE id=?", (id,)).fetchone()
    if not origine: flash('Introuvable.','danger'); return redirect(url_for('commandes'))
    lignes = db.execute("SELECT * FROM lignes_commande WHERE commande_id=?", (id,)).fetchall()
    numero = next_numero('CMD','commandes','numero')
    try:
        db.execute("INSERT INTO commandes (numero,client_id,date_commande,statut,remise_globale,notes) VALUES (?,?,?,?,?,?)",
            (numero,origine['client_id'],date.today().isoformat(),'en_attente',origine['remise_globale'],f"Copie de {origine['numero']}"))
        db.commit()
        new_id = db.execute("SELECT id FROM commandes WHERE numero=?", (numero,)).fetchone()['id']
        for l in lignes:
            db.execute("INSERT INTO lignes_commande (commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES (?,?,?,?,?,?)",
                (new_id,l['produit_id'],l['quantite'],l['prix_unitaire'],l['remise'],l['tva']))
        db.commit(); flash(f'Commande dupliquée → {numero}','success')
        return redirect(url_for('voir_commande', id=new_id))
    except Exception as e:
        db.rollback(); flash(f'Erreur : {e}','danger')
        return redirect(url_for('voir_commande', id=id))

@app.route('/commandes/<int:id>/statut', methods=['POST'])
def changer_statut_commande(id):
    db = get_db(); db.execute("UPDATE commandes SET statut=? WHERE id=?", (request.form.get('statut'),id)); db.commit()
    flash('Statut mis à jour.','success'); return redirect(url_for('voir_commande', id=id))

@app.route('/commandes/<int:id>/supprimer', methods=['POST'])
def supprimer_commande(id):
    db = get_db()
    for l in db.execute("SELECT * FROM lignes_commande WHERE commande_id=?", (id,)).fetchall():
        db.execute("UPDATE produits SET stock=stock+? WHERE id=?", (l['quantite'],l['produit_id']))
    db.execute("DELETE FROM commandes WHERE id=?", (id,)); db.commit()
    flash('Commande supprimée.','info'); return redirect(url_for('commandes'))

@app.route('/commandes/<int:id>/ligne/ajouter', methods=['POST'])
def ajouter_ligne_commande(id):
    db = get_db(); cmd = db.execute("SELECT statut FROM commandes WHERE id=?", (id,)).fetchone()
    if not cmd or cmd['statut'] in ('livree','annulee'): return jsonify({'error':'Modification impossible'}), 400
    f = request.json or request.form
    try:
        pid = int(f.get('produit_id')); qte = int(f.get('quantite',1))
        db.execute("INSERT INTO lignes_commande (commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES (?,?,?,?,?,?)",
            (id,pid,qte,float(f.get('prix_unitaire',0)),float(f.get('remise',0)),float(f.get('tva',18))))
        db.execute("UPDATE produits SET stock=stock-? WHERE id=?", (qte,pid))
        db.commit(); return jsonify({'ok':True})
    except Exception as e: return jsonify({'error':str(e)}), 400

@app.route('/commandes/ligne/<int:ligne_id>/supprimer', methods=['POST'])
def supprimer_ligne_commande(ligne_id):
    db = get_db(); l = db.execute("SELECT * FROM lignes_commande WHERE id=?", (ligne_id,)).fetchone()
    if not l: return jsonify({'error':'Ligne introuvable'}), 404
    db.execute("UPDATE produits SET stock=stock+? WHERE id=?", (l['quantite'],l['produit_id']))
    db.execute("DELETE FROM lignes_commande WHERE id=?", (ligne_id,)); db.commit()
    return jsonify({'ok':True})

@app.route('/commandes/ligne/<int:ligne_id>/modifier', methods=['POST'])
def modifier_ligne_commande(ligne_id):
    db = get_db(); l = db.execute("SELECT * FROM lignes_commande WHERE id=?", (ligne_id,)).fetchone()
    if not l: return jsonify({'error':'Ligne introuvable'}), 404
    f = request.json or request.form; old_qte = l['quantite']; new_qte = int(f.get('quantite',old_qte))
    try:
        db.execute("UPDATE lignes_commande SET quantite=?,prix_unitaire=?,remise=?,tva=? WHERE id=?",
            (new_qte,float(f.get('prix_unitaire',l['prix_unitaire'])),float(f.get('remise',l['remise'])),float(f.get('tva',l['tva'])),ligne_id))
        db.execute("UPDATE produits SET stock=stock+? WHERE id=?", (old_qte-new_qte,l['produit_id']))
        db.commit(); return jsonify({'ok':True})
    except Exception as e: return jsonify({'error':str(e)}), 400

def _save_lignes(db, commande_id, form, update_stock=True):
    pids = form.getlist('produit_id[]'); qtes = form.getlist('quantite[]')
    pus  = form.getlist('prix_unitaire[]'); rems = form.getlist('remise_ligne[]'); tvas = form.getlist('tva_ligne[]')
    for i, pid in enumerate(pids):
        pid = (pid or '').strip()
        if not pid: continue
        qte = int(qtes[i] or 1); pu = float(pus[i] or 0)
        rem = float(rems[i] or 0) if i < len(rems) else 0.0
        tva = float(tvas[i] or 18) if i < len(tvas) else 18.0
        db.execute("INSERT INTO lignes_commande (commande_id,produit_id,quantite,prix_unitaire,remise,tva) VALUES (?,?,?,?,?,?)",
            (commande_id,int(pid),qte,pu,rem,tva))
        if update_stock: db.execute("UPDATE produits SET stock=stock-? WHERE id=?", (qte,int(pid)))

# ══════════════════════════════════════════════════════════════
#  FACTURES
# ══════════════════════════════════════════════════════════════
@app.route('/factures')
def factures():
    db = get_db(); statut = request.args.get('statut',''); q = request.args.get('q','')
    query = "SELECT f.*, c.nom as client_nom FROM factures f JOIN clients c ON c.id=f.client_id WHERE 1=1"; args = []
    if statut: query += " AND f.statut=?"; args.append(statut)
    if q: query += " AND (f.numero LIKE ? OR c.nom LIKE ?)"; args += [f'%{q}%',f'%{q}%']
    query += " ORDER BY f.created_at DESC"
    facs = db.execute(query,args).fetchall()
    facs_data = [{'fac':f,'ttc':commande_totaux(f['commande_id'])['ttc'] if f['commande_id'] else 0} for f in facs]
    return render_template('factures.html', factures_data=facs_data, statut=statut, q=q, params=get_all_params())

@app.route('/factures/generer/<int:commande_id>', methods=['POST'])
def generer_facture(commande_id):
    db = get_db()
    if db.execute("SELECT id FROM factures WHERE commande_id=?", (commande_id,)).fetchone():
        flash('Une facture existe déjà.','warning'); return redirect(url_for('voir_commande', id=commande_id))
    cmd = db.execute("SELECT * FROM commandes WHERE id=?", (commande_id,)).fetchone()
    numero = next_numero('FAC','factures','numero')
    db.execute("INSERT INTO factures (numero,commande_id,client_id,date_facture,date_echeance,statut) VALUES (?,?,?,?,?,?)",
        (numero,commande_id,cmd['client_id'],date.today().isoformat(),(date.today()+timedelta(days=30)).isoformat(),'non_payee'))
    db.commit()
    fac_id = db.execute("SELECT id FROM factures WHERE numero=?", (numero,)).fetchone()['id']
    flash(f'Facture {numero} générée !','success'); return redirect(url_for('voir_facture', id=fac_id))

@app.route('/factures/<int:id>')
def voir_facture(id):
    db = get_db()
    facture = db.execute("""SELECT f.*, c.nom as client_nom, c.email as client_email, c.telephone as client_tel,
               c.adresse as client_adresse, c.ville as client_ville, c.pays as client_pays, c.code as client_code
        FROM factures f JOIN clients c ON c.id=f.client_id WHERE f.id=?""", (id,)).fetchone()
    if not facture: flash('Facture introuvable.','danger'); return redirect(url_for('factures'))
    totaux = commande_totaux(facture['commande_id']) if facture['commande_id'] \
             else {'ht':0,'ht_net':0,'tva':0,'ttc':0,'lignes':[],'remise_globale':0,'remise_montant':0}
    return render_template('facture_detail.html', facture=facture, totaux=totaux, params=get_all_params())

@app.route('/factures/<int:id>/payer', methods=['POST'])
def marquer_payee(id):
    db = get_db(); db.execute("UPDATE factures SET statut='payee' WHERE id=?", (id,)); db.commit()
    flash('Facture payée.','success'); return redirect(url_for('voir_facture', id=id))

@app.route('/factures/<int:id>/annuler', methods=['POST'])
def annuler_facture(id):
    db = get_db(); db.execute("UPDATE factures SET statut='annulee' WHERE id=?", (id,)); db.commit()
    flash('Facture annulée.','info'); return redirect(url_for('voir_facture', id=id))

@app.route('/factures/<int:id>/pdf')
def telecharger_facture_pdf(id):
    db = get_db()
    facture = db.execute("""SELECT f.*, c.nom as client_nom, c.email as client_email, c.telephone as client_tel,
               c.adresse as client_adresse, c.ville as client_ville, c.pays as client_pays, c.code as client_code
        FROM factures f JOIN clients c ON c.id=f.client_id WHERE f.id=?""", (id,)).fetchone()
    if not facture: return "Facture introuvable", 404
    totaux = commande_totaux(facture['commande_id']) if facture['commande_id'] \
             else {'ht':0,'ht_net':0,'tva':0,'ttc':0,'lignes':[],'remise_globale':0,'remise_montant':0}
    pdf_buf = generer_pdf_facture(facture, totaux, get_all_params())
    return send_file(io.BytesIO(pdf_buf), mimetype='application/pdf',
                     as_attachment=False, download_name=f"Facture-{facture['numero']}.pdf")

# ══════════════════════════════════════════════════════════════
#  STATISTIQUES
# ══════════════════════════════════════════════════════════════
@app.route('/statistiques')
def statistiques():
    annee = request.args.get('annee', date.today().year); params = get_all_params()
    return render_template('statistiques.html', params=params, annee=annee,
                           annees=range(date.today().year-3, date.today().year+1))

@app.route('/api/stats/ca_mensuel')
def api_ca_mensuel():
    db = get_db(); annee = request.args.get('annee', date.today().year)
    rows = db.execute("""SELECT strftime('%m',c.date_commande) as mois,
               SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY mois ORDER BY mois""", (str(annee),)).fetchall()
    mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    data = {m: 0 for m in range(1,13)}
    for r in rows: data[int(r['mois'])] = round(float(r['ca'] or 0),2)
    return jsonify({'labels':mois,'values':list(data.values())})

@app.route('/api/stats/top_produits')
def api_top_produits():
    db = get_db(); annee = request.args.get('annee', date.today().year)
    rows = db.execute("""SELECT p.nom,SUM(l.quantite) as qte,SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)) as ca
        FROM lignes_commande l JOIN produits p ON p.id=l.produit_id JOIN commandes c ON c.id=l.commande_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY p.id ORDER BY ca DESC LIMIT 8""", (str(annee),)).fetchall()
    return jsonify({'labels':[r['nom'] for r in rows],'qte':[r['qte'] for r in rows],'values':[round(float(r['ca'] or 0),2) for r in rows]})

@app.route('/api/stats/clients_top')
def api_clients_top():
    db = get_db(); annee = request.args.get('annee', date.today().year)
    rows = db.execute("""SELECT cl.nom,COUNT(DISTINCT c.id) as nb_cmd,
               SUM(l.quantite*l.prix_unitaire*(1-l.remise/100)*(1-c.remise_globale/100)) as ca
        FROM lignes_commande l JOIN commandes c ON c.id=l.commande_id JOIN clients cl ON cl.id=c.client_id
        WHERE strftime('%Y',c.date_commande)=? AND c.statut!='annulee' GROUP BY cl.id ORDER BY ca DESC LIMIT 8""", (str(annee),)).fetchall()
    return jsonify({'labels':[r['nom'] for r in rows],'ca':[round(float(r['ca'] or 0),2) for r in rows],'cmds':[r['nb_cmd'] for r in rows]})

@app.route('/api/stats/statuts_commandes')
def api_statuts_commandes():
    db = get_db(); annee = request.args.get('annee', date.today().year)
    rows = db.execute("SELECT statut,COUNT(*) as nb FROM commandes WHERE strftime('%Y',date_commande)=? GROUP BY statut", (str(annee),)).fetchall()
    lm = {'en_attente':'En attente','confirmee':'Confirmée','expediee':'Expédiée','livree':'Livrée','annulee':'Annulée'}
    return jsonify({'labels':[lm.get(r['statut'],r['statut']) for r in rows],'values':[r['nb'] for r in rows]})

@app.route('/api/stats/evolution_clients')
def api_evolution_clients():
    db = get_db(); annee = request.args.get('annee', date.today().year)
    rows = db.execute("SELECT strftime('%m',created_at) as mois,COUNT(*) as nb FROM clients WHERE strftime('%Y',created_at)=? GROUP BY mois ORDER BY mois", (str(annee),)).fetchall()
    mois = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc']
    data = {m: 0 for m in range(1,13)}
    for r in rows: data[int(r['mois'])] = r['nb']
    return jsonify({'labels':mois,'values':list(data.values())})

@app.route('/api/produit_prix/<int:id>')
def produit_prix(id):
    db = get_db(); p = db.execute("SELECT prix_vente,tva,stock FROM produits WHERE id=?", (id,)).fetchone()
    if p: return jsonify({'prix':p['prix_vente'],'tva':p['tva'],'stock':p['stock']})
    return jsonify({}), 404

# ══════════════════════════════════════════════════════════════
#  PARAMÈTRES (+ upload logo)
# ══════════════════════════════════════════════════════════════
@app.route('/parametres', methods=['GET','POST'])
def parametres():
    db = get_db(); params = get_all_params()
    categories = db.execute("SELECT * FROM categories ORDER BY nom").fetchall()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save_params':
            for key in ['boutique_nom','boutique_adresse','boutique_ville','boutique_pays',
                        'boutique_telephone','boutique_email','boutique_ninea','boutique_rccm',
                        'devise','tva_defaut','couleur_primaire','logo_text']:
                db.execute("INSERT OR REPLACE INTO parametres VALUES (?,?)", (key, request.form.get(key,'')))
            # Upload logo
            logo_file = request.files.get('logo_file')
            if logo_file and logo_file.filename and allowed_file(logo_file.filename):
                # Supprimer ancien logo
                old_logo = params.get('logo_filename','')
                if old_logo:
                    old_path = os.path.join(LOGO_DIR, old_logo)
                    if os.path.exists(old_path): os.remove(old_path)
                ext = logo_file.filename.rsplit('.',1)[1].lower()
                if ext == 'jpg': ext = 'jpeg'
                uid = uuid.uuid4().hex; new_fn = f"logo_{uid}.{ext}"
                save_fmt = 'PNG' if ext == 'png' else 'JPEG'
                try:
                    img = PILImage.open(logo_file.stream).convert('RGBA' if ext == 'png' else 'RGB')
                    img.thumbnail((400,200), PILImage.LANCZOS)
                    img.save(os.path.join(LOGO_DIR, new_fn), format=save_fmt, quality=90, optimize=True)
                    db.execute("INSERT OR REPLACE INTO parametres VALUES (?,?)", ('logo_filename', new_fn))
                except Exception as e:
                    flash(f'Erreur logo : {e}', 'danger')
            db.commit(); flash('Paramètres enregistrés !','success')
        elif action == 'delete_logo':
            old_logo = params.get('logo_filename','')
            if old_logo:
                old_path = os.path.join(LOGO_DIR, old_logo)
                if os.path.exists(old_path): os.remove(old_path)
            db.execute("INSERT OR REPLACE INTO parametres VALUES (?,?)", ('logo_filename',''))
            db.commit(); flash('Logo supprimé.','info')
        elif action == 'add_categorie':
            nom = (request.form.get('cat_nom') or '').strip()
            if nom:
                try:
                    db.execute("INSERT INTO categories(nom) VALUES (?)", (nom,)); db.commit()
                    flash('Catégorie ajoutée !','success')
                except: flash('Cette catégorie existe déjà.','warning')
        elif action == 'del_categorie':
            db.execute("DELETE FROM categories WHERE id=?", (request.form.get('cat_id'),))
            db.commit(); flash('Catégorie supprimée.','info')
        return redirect(url_for('parametres'))
    return render_template('parametres.html', params=params, categories=categories)

# ══════════════════════════════════════════════════════════════
#  PDF FACTURE
# ══════════════════════════════════════════════════════════════
def generer_pdf_facture(facture, totaux, params):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet(); story = []; devise = params.get('devise','FCFA')
    try:
        hx = params.get('couleur_primaire','#1a56db').lstrip('#')
        primary = colors.Color(*[int(hx[i:i+2],16)/255 for i in (0,2,4)])
    except: primary = colors.HexColor('#1a56db')

    logo_text = params.get('logo_text','MB'); boutique = params.get('boutique_nom','Ma Boutique')
    logo_filename = params.get('logo_filename','')
    logo_path = os.path.join(LOGO_DIR, logo_filename) if logo_filename else None

    # En-tête
    if logo_path and os.path.exists(logo_path):
        logo = RLImage(logo_path, width=2.4*cm, height=2.4*cm)
        logo.hAlign = 'CENTER'
        logo_cell = logo
    else:
        logo_cell = Paragraph(f'<font color="white" size="18"><b>{logo_text}</b></font>',
                              ParagraphStyle('logo', alignment=TA_CENTER))
    hdr = [[
        logo_cell,
        Paragraph(f'<b><font size="16">{boutique}</font></b><br/>'
                  f'<font size="8.5" color="grey">{params.get("boutique_adresse","")}<br/>'
                  f'{params.get("boutique_ville","")} — {params.get("boutique_pays","")}<br/>'
                  f'Tél : {params.get("boutique_telephone","")}<br/>Email : {params.get("boutique_email","")}</font>',
                  styles['Normal']),
        Paragraph(f'<font size="20" color="white"><b>FACTURE</b></font><br/>'
                  f'<font size="10" color="white"><b>N° {facture["numero"]}</b></font>',
                  ParagraphStyle('fac', alignment=TA_RIGHT))
    ]]
    ht = Table(hdr, colWidths=[2.8*cm, 9.7*cm, 5.5*cm])
    ht.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,0),primary),('BACKGROUND',(2,0),(2,0),primary),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(0,0),0),
        ('RIGHTPADDING',(0,0),(0,0),0),
        ('TOPPADDING',(0,0),(0,0),4),
        ('BOTTOMPADDING',(0,0),(0,0),4),
        ('ALIGN',(0,0),(0,0),'CENTER'),
        ('RIGHTPADDING',(2,0),(2,0),10),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
    ]))
    story.append(ht); story.append(Spacer(1,0.4*cm))

    ninea = params.get('boutique_ninea',''); rccm = params.get('boutique_rccm','')
    statut_txt = '✓ PAYÉE' if facture['statut']=='payee' else 'NON PAYÉE'
    info = [[
        Paragraph(f'<font size="8" color="grey">{ninea}<br/>{rccm}</font>', styles['Normal']),
        Paragraph(f'<b>Facturé à :</b><br/><b>{facture["client_nom"]}</b><br/>'
                  f'{facture["client_adresse"] or ""}<br/>{facture["client_ville"] or ""}'
                  f'{" — "+facture["client_pays"] if facture["client_pays"] else ""}<br/>'
                  f'Code : {facture["client_code"] or ""}', ParagraphStyle('cl',leftIndent=8)),
        Paragraph(f'<b>Date :</b> {facture["date_facture"] or date.today().isoformat()}<br/>'
                  f'<b>Échéance :</b> {facture["date_echeance"] or ""}<br/>'
                  f'<b>Statut :</b> {statut_txt}', ParagraphStyle('dt',alignment=TA_RIGHT))
    ]]
    it = Table(info, colWidths=[6*cm,7*cm,5.5*cm])
    it.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4)]))
    story.append(it); story.append(Spacer(1,0.5*cm))

    th = ParagraphStyle('th',alignment=TA_CENTER,fontSize=9,textColor=colors.white,fontName='Helvetica-Bold')
    td = ParagraphStyle('td',fontSize=9); tr2 = ParagraphStyle('tr2',fontSize=9,alignment=TA_RIGHT)
    tbl = [[Paragraph(h,th) for h in ['#','Désignation','Qté','P.U. HT','Rem.','TVA','Total HT']]]
    for i,l in enumerate(totaux['lignes'],1):
        pu=float(l['prix_unitaire']); qte=int(l['quantite']); rem=float(l['remise']); tvl=float(l['tva'])
        tbl.append([
            Paragraph(str(i),ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
            Paragraph(str(l['produit_nom']),td), Paragraph(str(qte),ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
            Paragraph(f"{pu:,.0f} {devise}",tr2), Paragraph(f"{rem:.0f}%",ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
            Paragraph(f"{tvl:.0f}%",ParagraphStyle('ci',alignment=TA_CENTER,fontSize=9)),
            Paragraph(f"{qte*pu*(1-rem/100):,.0f} {devise}",tr2),
        ])
    lt = Table(tbl, colWidths=[0.8*cm,6*cm,1.2*cm,2.8*cm,1.3*cm,1.3*cm,3.5*cm])
    lt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),primary),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f8faff'),colors.white]),
        ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#e5e7eb')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
    ]))
    story.append(lt); story.append(Spacer(1,0.4*cm))

    rg=totaux['remise_globale']; hn=totaux['ht_net']; tvn=totaux['tva']; ttc=totaux['ttc']
    tot_rows=[]
    if rg>0:
        tot_rows+=[['','Sous-total HT',f"{totaux['ht']:,.0f} {devise}"],
                   ['',f'Remise ({rg:.0f}%)',f"-{totaux['ht']*rg/100:,.0f} {devise}"]]
    tot_rows+=[
        ['','Total HT',f"{hn:,.0f} {devise}"],['','TVA',f"{tvn:,.0f} {devise}"],
        ['',Paragraph('<b>TOTAL TTC</b>',ParagraphStyle('tt',fontName='Helvetica-Bold',fontSize=11)),
             Paragraph(f'<b>{ttc:,.0f} {devise}</b>',ParagraphStyle('ttv',fontName='Helvetica-Bold',fontSize=11,alignment=TA_RIGHT))],
    ]
    tt2 = Table(tot_rows, colWidths=[9.5*cm,5*cm,4*cm])
    tt2.setStyle(TableStyle([
        ('ALIGN',(1,0),(2,-1),'RIGHT'),('LINEABOVE',(1,-1),(2,-1),1,primary),
        ('BACKGROUND',(1,-1),(2,-1),colors.HexColor('#f0f4ff')),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('GRID',(1,0),(2,-1),0.3,colors.HexColor('#e5e7eb')),
    ]))
    story.append(tt2)
    notes = facture['notes'] if not isinstance(facture,dict) else facture.get('notes','')
    if notes:
        story.append(Spacer(1,0.4*cm))
        story.append(Paragraph(f"<b>Notes :</b> {notes}", styles['Normal']))
    story.append(Spacer(1,1*cm))
    story.append(HRFlowable(width="100%",thickness=0.5,color=colors.lightgrey))
    story.append(Spacer(1,0.2*cm))
    footer = f"{boutique} | {params.get('boutique_adresse','')} | Tél : {params.get('boutique_telephone','')} | {ninea} | {rccm}"
    story.append(Paragraph(f'<font size="7" color="grey">{footer}</font>',ParagraphStyle('ft',alignment=TA_CENTER)))
    doc.build(story)
    return buffer.getvalue()

# ══════════════════════════════════════════════════════════════
#  LANCEMENT
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("\n"+"═"*56)
    print("  🏪  GESTION COMMERCIALE  — v3.0")
    print("═"*56)
    print("  ➜  http://127.0.0.1:5000")
    print("  ✅  Images produit + Logo boutique")
    print("═"*56+"\n")
    app.run(debug=False, port=5000)
