"""
Seed de démonstration
Entreprise : Taysir Digital Group
Exécuter une seule fois : python3 seed_demo.py
"""
import sqlite3, os, random
from datetime import date, timedelta

DB = os.path.join(os.path.dirname(__file__), 'database.db')

def seed():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    # ── Paramètres entreprise
    params = {
        'boutique_nom': 'Taysir Digital Group',
        'boutique_adresse': 'Médinatoul Mounawara, Pikine',
        'boutique_ville': 'Dakar',
        'boutique_pays': 'Sénégal',
        'boutique_telephone': '+221 76 455 03 58',
        'boutique_email': 'taysirdigitalgroup@gmail.com',
        'boutique_ninea': 'NINEA: 012987139',
        'boutique_rccm': 'RCCM: SN DKR 2026 A 14398',
        'devise': 'FCFA',
        'tva_defaut': '18',
        'logo_text': 'TDG',
    }

    for k, v in params.items():
        db.execute("INSERT OR REPLACE INTO parametres VALUES (?,?)", (k, v))
    db.commit()

    # ── Catégories
    cats = [
        'Marketing Digital',
        'Publicité Digitale',
        'Référencement',
        'Développement',
        'Automatisation',
        'Design Graphique',
        'Community Management',
        'Services Techniques'
    ]

    cat_ids = {}
    for c in cats:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
    db.commit()

    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits / Services
    produits = [

        # ─── MARKETING DIGITAL
        ('TDG-001','Audit marketing digital','Analyse complète présence en ligne',cat_ids.get('Marketing Digital'),0,50000,18,999,1,'service'),
        ('TDG-002','Stratégie digitale complète','Plan marketing détaillé',cat_ids.get('Marketing Digital'),0,150000,18,999,1,'service'),

        # ─── PUBLICITÉ
        ('TDG-003','Gestion Facebook Ads','Création + gestion campagnes Meta',cat_ids.get('Publicité Digitale'),0,100000,18,999,1,'mois'),
        ('TDG-004','Gestion Google Ads','Campagnes Google Ads',cat_ids.get('Publicité Digitale'),0,120000,18,999,1,'mois'),
        ('TDG-005','Publicité TikTok Ads','Campagnes TikTok',cat_ids.get('Publicité Digitale'),0,90000,18,999,1,'mois'),
        ('TDG-006','Publicité LinkedIn Ads','Campagnes B2B LinkedIn',cat_ids.get('Publicité Digitale'),0,130000,18,999,1,'mois'),

        # ─── RÉFÉRENCEMENT
        ('TDG-007','Création fiche Google Business','Création + optimisation',cat_ids.get('Référencement'),0,30000,18,999,1,'service'),
        ('TDG-008','Optimisation Google Maps','Amélioration visibilité locale',cat_ids.get('Référencement'),0,50000,18,999,1,'service'),
        ('TDG-009','Référencement Yango','Inscription plateforme Yango',cat_ids.get('Référencement'),0,25000,18,999,1,'service'),
        ('TDG-010','Référencement Yandex Maps','Ajout sur Yandex',cat_ids.get('Référencement'),0,25000,18,999,1,'service'),
        ('TDG-011','SEO mensuel','Optimisation SEO continue',cat_ids.get('Référencement'),0,120000,18,999,1,'mois'),

        # ─── COMMUNITY MANAGEMENT
        ('TDG-012','Gestion réseaux sociaux Basic','2 posts/semaine',cat_ids.get('Community Management'),0,80000,18,999,1,'mois'),
        ('TDG-013','Gestion réseaux sociaux Standard','4 posts/semaine',cat_ids.get('Community Management'),0,150000,18,999,1,'mois'),
        ('TDG-014','Gestion réseaux sociaux Premium','Publication quotidienne',cat_ids.get('Community Management'),0,250000,18,999,1,'mois'),

        # ─── DÉVELOPPEMENT
        ('TDG-015','Site web vitrine','Création site simple',cat_ids.get('Développement'),0,200000,18,999,1,'projet'),
        ('TDG-016','Application web','Développement web avancé',cat_ids.get('Développement'),0,500000,18,999,1,'projet'),
        ('TDG-017','Application mobile','App Android/iOS',cat_ids.get('Développement'),0,800000,18,999,1,'projet'),

        # ─── AUTOMATISATION
        ('TDG-018','Automatisation WhatsApp','Bots & réponses auto',cat_ids.get('Automatisation'),0,150000,18,999,1,'projet'),
        ('TDG-019','Automatisation marketing','Tunnel de vente auto',cat_ids.get('Automatisation'),0,200000,18,999,1,'projet'),

        # ─── DESIGN
        ('TDG-020','Création logo','Logo professionnel',cat_ids.get('Design Graphique'),0,50000,18,999,1,'service'),
        ('TDG-021','Création flyer','Flyer marketing',cat_ids.get('Design Graphique'),0,25000,18,999,1,'service'),
        ('TDG-022','Pack branding','Logo + charte graphique',cat_ids.get('Design Graphique'),0,150000,18,999,1,'projet'),

        # ─── SERVICES TECH
        ('TDG-023','Maintenance site web','Maintenance mensuelle',cat_ids.get('Services Techniques'),0,50000,18,999,1,'mois'),
        ('TDG-024','Hébergement web','Hébergement annuel',cat_ids.get('Services Techniques'),0,60000,18,999,1,'an'),
    ]

    prod_ids = {}
    for p in produits:
        db.execute("""INSERT OR IGNORE INTO produits
            (reference,nom,description,categorie_id,prix_achat,prix_vente,tva,stock,stock_min,unite)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", p)
    db.commit()

    for row in db.execute("SELECT id, reference, prix_vente, tva FROM produits"):
        prod_ids[row['reference']] = {'id': row['id'], 'prix': row['prix_vente'], 'tva': row['tva']}

    # ── Clients
    clients = [
        ('CLI-T001','Ba','Moussa','moussa@gmail.com','+221 77 111 11 11','Pikine','Dakar','Sénégal','particulier',0),
        ('CLI-T002','Sow','Aminata','aminata@societe.sn','+221 78 222 22 22','Dakar','Dakar','Sénégal','entreprise',10),
        ('CLI-T003','Fall','Cheikh','contact@fall.sn','+221 76 333 33 33','Guédiawaye','Dakar','Sénégal','entreprise',5),
    ]

    for c in clients:
        db.execute("""INSERT OR IGNORE INTO clients
            (code,nom,prenom,email,telephone,adresse,ville,pays,type_client,remise)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", c)
    db.commit()

    cli_ids = [r['id'] for r in db.execute("SELECT id FROM clients")]

    # ── Commandes
    statuts = ['en_attente','confirmee','expediee','livree','livree','annulee']
    prod_list = list(prod_ids.keys())
    today = date.today()

    commande_count = 0

    for mois_back in range(11, -1, -1):
        nb_cmd = random.randint(6, 15)

        for _ in range(nb_cmd):
            day = random.randint(1, 28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=day)

            num = f"CMD-TDG-{cmd_date.strftime('%Y%m')}-{commande_count+1:04d}"
            client_id = random.choice(cli_ids)
            statut = random.choice(statuts)

            db.execute("""INSERT OR IGNORE INTO commandes
                (numero,client_id,date_commande,date_livraison,statut,remise_globale,notes)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    num,
                    client_id,
                    cmd_date.isoformat(),
                    (cmd_date + timedelta(days=random.randint(3,10))).isoformat(),
                    statut,
                    random.choice([0,5,10]),
                    "Prestation marketing / IT"
                )
            )
            db.commit()

            cmd_id = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()['id']

            # lignes
            for ref in random.sample(prod_list, random.randint(1,3)):
                p = prod_ids[ref]
                db.execute("""INSERT INTO lignes_commande
                    (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                    VALUES (?,?,?,?,?,?)""",
                    (
                        cmd_id,
                        p['id'],
                        random.randint(1,2),
                        p['prix'],
                        random.choice([0,5]),
                        p['tva']
                    )
                )
            db.commit()

            commande_count += 1

            # Factures
            if statut == 'livree':
                db.execute("""INSERT OR IGNORE INTO factures
                    (numero,commande_id,client_id,date_facture,date_echeance,statut,notes)
                    VALUES (?,?,?,?,?,?,?)""",
                    (
                        f"FAC-TDG-{cmd_date.strftime('%Y%m')}-{commande_count:04d}",
                        cmd_id,
                        client_id,
                        cmd_date.isoformat(),
                        (cmd_date + timedelta(days=30)).isoformat(),
                        random.choice(['payee','non_payee']),
                        "Facture services digitaux"
                    )
                )
                db.commit()

    print(f"✅ Seed Taysir Digital Group OK : {commande_count} commandes")
    db.close()


if __name__ == '__main__':
    seed()
