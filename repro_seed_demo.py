"""
Script pour peupler la base avec des données de démonstration.
Entreprise : Repro Graphic - Pikine
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
        'boutique_nom': 'Repro Graphic - Pikine',
        'boutique_adresse': 'Pikine Rue 10',
        'boutique_ville': 'Dakar',
        'boutique_pays': 'Sénégal',
        'boutique_telephone': '+221 77 000 11 22',
        'boutique_email': 'reprographic.pikine@gmail.com',
        'boutique_ninea': 'NINEA: SN-DKR-2024-77889',
        'boutique_rccm': 'RCCM: DKR-2024-B-88991',
        'devise': 'FCFA',
        'tva_defaut': '18',
        'logo_text': 'RG',
    }

    for k, v in params.items():
        db.execute("INSERT OR REPLACE INTO parametres (cle,valeur) VALUES (?,?)", (k, v))
    db.commit()

    # ── Catégories
    cats = [
        'Impression',
        'Personnalisation',
        'Consommables',
        'Machines',
        'Supports & Cadeaux',
        'Fournitures',
        'Événementiel'
    ]

    cat_ids = {}
    for c in cats:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
    db.commit()

    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits / Services
    produits = [
        # Impression
        ('REP-001','Impression A4 Noir & Blanc','Impression simple',cat_ids.get('Impression'),10,50,18,1000,100,'feuille'),
        ('REP-002','Impression A4 Couleur','Impression couleur HD',cat_ids.get('Impression'),50,150,18,800,100,'feuille'),
        ('REP-003','Impression Grand Format','Bâche, vinyle, affiches',cat_ids.get('Impression'),2000,5000,18,100,10,'m²'),

        # Personnalisation
        ('REP-004','T-shirt personnalisé','Impression DTF sur textile',cat_ids.get('Personnalisation'),1500,5000,18,50,10,'unité'),
        ('REP-005','Casquette personnalisée','Flocage casquette',cat_ids.get('Personnalisation'),1000,3500,18,40,10,'unité'),
        ('REP-006','Tasse personnalisée','Sublimation tasse',cat_ids.get('Personnalisation'),1500,4000,18,60,10,'unité'),
        ('REP-007','Écharpe remise diplôme','Personnalisation événement',cat_ids.get('Événementiel'),2000,6000,18,50,10,'unité'),

        # Consommables
        ('REP-008','Poudre DTF','Consommable impression textile',cat_ids.get('Consommables'),8000,15000,18,30,5,'kg'),
        ('REP-009','Encre PVC/Vinyl','Encre professionnelle',cat_ids.get('Consommables'),5000,12000,18,40,5,'litre'),
        ('REP-010','Papier photo','Papier haute qualité',cat_ids.get('Consommables'),2000,5000,18,100,20,'paquet'),

        # Machines
        ('REP-011','Machine presse','Machine transfert thermique',cat_ids.get('Machines'),120000,250000,18,5,1,'unité'),
        ('REP-012','Machine plastification','Plastifieuse pro',cat_ids.get('Machines'),50000,120000,18,6,1,'unité'),
        ('REP-013','Machine découpe PVC','Découpe vinyle',cat_ids.get('Machines'),150000,300000,18,3,1,'unité'),

        # Supports & Cadeaux
        ('REP-014','Magic Mirror','Cadre photo lumineux',cat_ids.get('Supports & Cadeaux'),3000,8000,18,30,5,'unité'),
        ('REP-015','Thermos café','Petit modèle',cat_ids.get('Supports & Cadeaux'),2000,5000,18,40,5,'unité'),
        ('REP-016','Goblet personnalisé','Gobelet événement',cat_ids.get('Supports & Cadeaux'),500,1500,18,100,20,'unité'),

        # Fournitures
        ('REP-017','Carte PVC','Carte rigide impression',cat_ids.get('Fournitures'),300,1000,18,500,50,'unité'),
        ('REP-018','Colle double face','Adhésif pro',cat_ids.get('Fournitures'),500,1500,18,200,20,'rouleau'),
        ('REP-019','Lutin documents','Support documents',cat_ids.get('Fournitures'),1000,2500,18,100,10,'unité'),

        # Événementiel
        ('REP-020','Bracelet événementiel','Bracelet personnalisé',cat_ids.get('Événementiel'),200,800,18,500,50,'unité'),
        ('REP-021','Sachet baptême','Sachet personnalisé',cat_ids.get('Événementiel'),300,1000,18,300,50,'unité'),
        ('REP-022','Éventail personnalisé','Éventail promo',cat_ids.get('Événementiel'),500,1500,18,200,20,'unité'),
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
        ('CLI-R001','Diallo','Aminata','aminata@gmail.com','+221 77 123 00 00','Pikine','Dakar','Sénégal','particulier',0),
        ('CLI-R002','Fall','Ibrahima','fall@business.sn','+221 78 456 00 00','Guédiawaye','Dakar','Sénégal','entreprise',10),
        ('CLI-R003','Sarr','Moussa','m.sarr@gmail.com','+221 70 789 00 00','Keur Massar','Dakar','Sénégal','particulier',0),
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
        nb_cmd = random.randint(8, 20)  # plus fréquent que menuiserie

        for _ in range(nb_cmd):
            day = random.randint(1, 28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=day)

            num = f"CMD-REP-{cmd_date.strftime('%Y%m')}-{commande_count+1:04d}"
            client_id = random.choice(cli_ids)
            statut = random.choice(statuts)

            db.execute("""INSERT OR IGNORE INTO commandes 
                (numero,client_id,date_commande,date_livraison,statut,remise_globale,notes)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    num,
                    client_id,
                    cmd_date.isoformat(),
                    (cmd_date + timedelta(days=random.randint(1,5))).isoformat(),
                    statut,
                    random.choice([0,5,10]),
                    "Commande reprographie"
                )
            )
            db.commit()

            cmd_id = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()['id']

            # lignes (beaucoup d'articles, petites quantités ou grandes séries)
            for ref in random.sample(prod_list, random.randint(2,5)):
                p = prod_ids[ref]
                db.execute("""INSERT INTO lignes_commande 
                    (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                    VALUES (?,?,?,?,?,?)""",
                    (
                        cmd_id,
                        p['id'],
                        random.randint(1,50),
                        p['prix'],
                        random.choice([0,5]),
                        p['tva']
                    )
                )
            db.commit()

            commande_count += 1

            # Facture
            if statut == 'livree':
                db.execute("""INSERT OR IGNORE INTO factures 
                    (numero,commande_id,client_id,date_facture,date_echeance,statut,notes)
                    VALUES (?,?,?,?,?,?,?)""",
                    (
                        f"FAC-REP-{cmd_date.strftime('%Y%m')}-{commande_count:04d}",
                        cmd_id,
                        client_id,
                        cmd_date.isoformat(),
                        (cmd_date + timedelta(days=15)).isoformat(),
                        random.choice(['payee','non_payee']),
                        "Facture reprographie"
                    )
                )
                db.commit()

    print(f"✅ Seed reprographie OK : {commande_count} commandes")
    db.close()


if __name__ == '__main__':
    seed()
