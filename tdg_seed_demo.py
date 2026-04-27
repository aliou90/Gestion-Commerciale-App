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
        'Marketing Digital','Publicité Digitale','Référencement',
        'Développement','Automatisation','Design Graphique',
        'Community Management','Services Techniques'
    ]

    cat_ids = {}
    for c in cats:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
    db.commit()

    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits / Services
    produits = [
        ('TDG-001','Audit marketing digital','Analyse complète présence en ligne',cat_ids['Marketing Digital'],0,50000,18,999,1,'service',1),
        ('TDG-002','Stratégie digitale complète','Plan marketing détaillé',cat_ids['Marketing Digital'],0,150000,18,999,1,'service',1),

        ('TDG-003','Gestion Facebook Ads','Gestion campagnes Meta',cat_ids['Publicité Digitale'],0,100000,18,999,1,'mois',1),
        ('TDG-004','Gestion Google Ads','Campagnes Google',cat_ids['Publicité Digitale'],0,120000,18,999,1,'mois',1),
        ('TDG-005','Publicité TikTok Ads','Campagnes TikTok',cat_ids['Publicité Digitale'],0,90000,18,999,1,'mois',1),
        ('TDG-006','Publicité LinkedIn Ads','Campagnes B2B',cat_ids['Publicité Digitale'],0,130000,18,999,1,'mois',1),

        ('TDG-007','Création fiche Google Business','Création + optimisation',cat_ids['Référencement'],0,30000,18,999,1,'service',1),
        ('TDG-008','Optimisation Google Maps','Visibilité locale',cat_ids['Référencement'],0,50000,18,999,1,'service',1),
        ('TDG-009','Référencement Yango','Inscription Yango',cat_ids['Référencement'],0,25000,18,999,1,'service',1),
        ('TDG-010','Référencement Yandex','Ajout Yandex Maps',cat_ids['Référencement'],0,25000,18,999,1,'service',1),
        ('TDG-011','SEO mensuel','Optimisation continue',cat_ids['Référencement'],0,120000,18,999,1,'mois',1),

        ('TDG-012','Community Basic','2 posts/semaine',cat_ids['Community Management'],0,80000,18,999,1,'mois',1),
        ('TDG-013','Community Standard','4 posts/semaine',cat_ids['Community Management'],0,150000,18,999,1,'mois',1),
        ('TDG-014','Community Premium','Publication quotidienne',cat_ids['Community Management'],0,250000,18,999,1,'mois',1),

        ('TDG-015','Site web vitrine','Site simple',cat_ids['Développement'],0,200000,18,999,1,'projet',1),
        ('TDG-016','Application web','Solution web',cat_ids['Développement'],0,500000,18,999,1,'projet',1),
        ('TDG-017','Application mobile','App mobile',cat_ids['Développement'],0,800000,18,999,1,'projet',1),

        ('TDG-018','Automatisation WhatsApp','Bot automatisé',cat_ids['Automatisation'],0,150000,18,999,1,'projet',1),
        ('TDG-019','Tunnel marketing','Automatisation ventes',cat_ids['Automatisation'],0,200000,18,999,1,'projet',1),

        ('TDG-020','Création logo','Logo pro',cat_ids['Design Graphique'],0,50000,18,999,1,'service',1),
        ('TDG-021','Création flyer','Flyer marketing',cat_ids['Design Graphique'],0,25000,18,999,1,'service',1),
        ('TDG-022','Pack branding','Identité visuelle complète',cat_ids['Design Graphique'],0,150000,18,999,1,'projet',1),

        ('TDG-023','Maintenance site','Maintenance mensuelle',cat_ids['Services Techniques'],0,50000,18,999,1,'mois',1),
        ('TDG-024','Hébergement web','Hébergement annuel',cat_ids['Services Techniques'],0,60000,18,999,1,'an',1),
    ]

    prod_ids = {}
    for p in produits:
        db.execute("""INSERT OR IGNORE INTO produits
            (reference,nom,description,categorie_id,prix_achat,prix_vente,tva,stock,stock_min,unite,actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", p)
    db.commit()

    for row in db.execute("SELECT id, reference, prix_vente, tva FROM produits"):
        prod_ids[row['reference']] = dict(row)

    # ── Clients
    clients = [
        ('CLI-T001','Ba','Moussa','moussa@gmail.com','+221771111111','Pikine','Dakar','Sénégal','particulier',0,1),
        ('CLI-T002','Sow','Aminata','aminata@societe.sn','+221782222222','Dakar','Dakar','Sénégal','entreprise',10,1),
        ('CLI-T003','Fall','Cheikh','contact@fall.sn','+221763333333','Guédiawaye','Dakar','Sénégal','entreprise',5,1),
    ]

    for c in clients:
        db.execute("""INSERT OR IGNORE INTO clients
            (code,nom,prenom,email,telephone,adresse,ville,pays,type_client,remise,actif)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", c)
    db.commit()

    cli_ids = [r['id'] for r in db.execute("SELECT id FROM clients")]

    # ── Commandes
    statuts = ['en_attente','confirmee','expediee','livree','annulee']
    today = date.today()
    commande_count = 0

    for mois_back in range(11, -1, -1):
        for _ in range(random.randint(5,12)):

            day = random.randint(1,28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=min(day,28))

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
                ))
            db.commit()

            cmd = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()
            if not cmd:
                continue

            cmd_id = cmd['id']

            # 👉 TDG = souvent 1 service par commande
            ref = random.choice(list(prod_ids.keys()))
            p = prod_ids[ref]

            db.execute("""INSERT INTO lignes_commande
                (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                VALUES (?,?,?,?,?,?)""",
                (cmd_id, p['id'], 1, p['prix_vente'], random.choice([0,5]), p['tva']))
            db.commit()

            commande_count += 1

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
                    ))
                db.commit()

    print(f"✅ Seed TDG OK : {commande_count} commandes")
    db.close()

if __name__ == '__main__':
    seed()
