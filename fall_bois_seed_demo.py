"""
Script pour peupler la base avec des données de démonstration.
Entreprise : Menuiserie & Décoration
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
        'boutique_nom': 'Fall Bois Industries',
        'boutique_adresse': 'Zone Artisanale',
        'boutique_ville': 'Dakar',
        'boutique_pays': 'Sénégal',
        'boutique_telephone': '+221 77 965 21 28',
        'boutique_email': 'fallbois.industrie@gmail.com',
        'boutique_ninea': 'NINEA: SN-DKR-2024-12345',
        'boutique_rccm': 'RCCM: DKR-2024-B-56789',
        'devise': 'FCFA',
        'tva_defaut': '18',
        'logo_text': 'FBI',
    }

    for k, v in params.items():
        db.execute("INSERT OR REPLACE INTO parametres (cle,valeur) VALUES (?,?)", (k, v))
    db.commit()

    # ── Catégories
    cats = [
        'Lits',
        'Armoires',
        'Tables & Chaises',
        'Cuisines modernes',
        'Décoration intérieure',
        'Faux plafonds',
        'Portes & Fenêtres'
    ]

    cat_ids = {}
    for c in cats:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
    db.commit()

    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits
    produits = [
        ('MEN-001','Lit double bois massif','Lit solide en bois rouge verni',cat_ids.get('Lits'),75000,150000,18,10,2,'unité'),
        ('MEN-002','Lit superposé enfant','Lit gain de place pour enfants',cat_ids.get('Lits'),90000,180000,18,5,1,'unité'),

        ('MEN-003','Armoire 3 battants','Grande armoire avec miroir',cat_ids.get('Armoires'),85000,200000,18,8,2,'unité'),
        ('MEN-004','Dressing sur mesure','Fabrication personnalisée',cat_ids.get('Armoires'),120000,350000,18,3,1,'unité'),

        ('MEN-005','Table à manger 6 places','Bois massif + finition moderne',cat_ids.get('Tables & Chaises'),60000,140000,18,6,2,'unité'),
        ('MEN-006','Chaise design bois','Chaise moderne résistante',cat_ids.get('Tables & Chaises'),8000,20000,18,30,5,'unité'),

        ('MEN-007','Cuisine moderne complète','Installation cuisine équipée',cat_ids.get('Cuisines modernes'),250000,600000,18,2,1,'unité'),
        ('MEN-008','Placard cuisine','Placard sur mesure',cat_ids.get('Cuisines modernes'),150000,350000,18,4,1,'unité'),

        ('MEN-009','Décoration salon','Aménagement intérieur moderne',cat_ids.get('Décoration intérieure'),50000,150000,18,10,2,'unité'),
        ('MEN-010','Décoration chambre','Design complet chambre',cat_ids.get('Décoration intérieure'),60000,180000,18,8,2,'unité'),

        ('MEN-011','Faux plafond simple','Plafond standard',cat_ids.get('Faux plafonds'),30000,90000,18,20,5,'m²'),
        ('MEN-012','Faux plafond LED','Plafond avec éclairage intégré',cat_ids.get('Faux plafonds'),50000,150000,18,15,3,'m²'),

        ('MEN-013','Porte bois intérieure','Porte solide et esthétique',cat_ids.get('Portes & Fenêtres'),25000,75000,18,20,5,'unité'),
        ('MEN-014','Fenêtre aluminium','Fenêtre vitrée moderne',cat_ids.get('Portes & Fenêtres'),40000,120000,18,15,3,'unité'),
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
        ('CLI-1001','Diop','Mamadou','m.diop@email.sn','+221 77 111 11 11','Parcelles','Dakar','Sénégal','particulier',0),
        ('CLI-1002','Ba','Awa','awa.ba@gmail.com','+221 70 222 22 22','Guédiawaye','Dakar','Sénégal','particulier',0),
        ('CLI-1003','Sow','Cheikh','csow@sowgroup.sn','+221 78 333 33 33','Almadies','Dakar','Sénégal','entreprise',10),
        ('CLI-1004','Fall','Oumar','fall@sarl.sn','+221 76 444 44 44','Thiès','Thiès','Sénégal','entreprise',8),
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
        nb_cmd = random.randint(4, 10)

        for _ in range(nb_cmd):
            day = random.randint(1, 28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=day)

            num = f"CMD-MEN-{cmd_date.strftime('%Y%m')}-{commande_count+1:04d}"
            client_id = random.choice(cli_ids)
            statut = random.choice(statuts)

            date_livraison = (cmd_date + timedelta(days=random.randint(5,15))).isoformat()

            db.execute("""INSERT OR IGNORE INTO commandes 
                (numero,client_id,date_commande,date_livraison,statut,remise_globale,notes)
                VALUES (?,?,?,?,?,?,?)""",
                (num, client_id, cmd_date.isoformat(), date_livraison, statut,
                 random.choice([0,5,10]),
                 "Commande menuiserie / décoration")
            )
            db.commit()

            cmd_id = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()['id']

            # lignes
            for ref in random.sample(prod_list, random.randint(1,3)):
                p = prod_ids[ref]
                db.execute("""INSERT INTO lignes_commande 
                    (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                    VALUES (?,?,?,?,?,?)""",
                    (cmd_id, p['id'], random.randint(1,3), p['prix'], random.choice([0,5]), p['tva'])
                )
            db.commit()

            commande_count += 1

            # facture
            if statut == 'livree':
                db.execute("""INSERT OR IGNORE INTO factures 
                    (numero,commande_id,client_id,date_facture,date_echeance,statut,notes)
                    VALUES (?,?,?,?,?,?,?)""",
                    (
                        f"FAC-MEN-{cmd_date.strftime('%Y%m')}-{commande_count:04d}",
                        cmd_id,
                        client_id,
                        cmd_date.isoformat(),
                        (cmd_date + timedelta(days=30)).isoformat(),
                        random.choice(['payee','non_payee']),
                        "Facture menuiserie"
                    )
                )
                db.commit()

    print(f"✅ Seed menuiserie OK : {commande_count} commandes")
    db.close()


if __name__ == '__main__':
    seed()
