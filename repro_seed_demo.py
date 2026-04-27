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
        db.execute("INSERT OR REPLACE INTO parametres VALUES (?,?)", (k, v))
    db.commit()

    # ── Catégories
    cats = [
        'Impression','Personnalisation','Consommables',
        'Machines','Supports & Cadeaux','Fournitures','Événementiel'
    ]

    cat_ids = {}
    for c in cats:
        db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
    db.commit()

    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits
    produits = [
        ('REP-001','Impression A4 Noir & Blanc','Impression simple rapide',cat_ids['Impression'],10,50,18,1000,100,'feuille',1),
        ('REP-002','Impression A4 Couleur','Impression couleur HD',cat_ids['Impression'],50,150,18,800,100,'feuille',1),
        ('REP-003','Impression Grand Format','Bâche, vinyle, affiches',cat_ids['Impression'],2000,5000,18,100,10,'m²',1),

        ('REP-004','T-shirt personnalisé','Impression DTF textile',cat_ids['Personnalisation'],1500,5000,18,50,10,'unité',1),
        ('REP-005','Casquette personnalisée','Flocage casquette',cat_ids['Personnalisation'],1000,3500,18,40,10,'unité',1),
        ('REP-006','Tasse personnalisée','Sublimation tasse',cat_ids['Personnalisation'],1500,4000,18,60,10,'unité',1),
        ('REP-007','Écharpe diplôme','Écharpe personnalisée événement',cat_ids['Événementiel'],2000,6000,18,50,10,'unité',1),

        ('REP-008','Poudre DTF','Consommable impression textile',cat_ids['Consommables'],8000,15000,18,30,5,'kg',1),
        ('REP-009','Encre PVC/Vinyl','Encre professionnelle',cat_ids['Consommables'],5000,12000,18,40,5,'litre',1),
        ('REP-010','Papier photo','Papier haute qualité',cat_ids['Consommables'],2000,5000,18,100,20,'paquet',1),

        ('REP-011','Machine presse','Machine transfert thermique',cat_ids['Machines'],120000,250000,18,5,1,'unité',1),
        ('REP-012','Machine plastification','Plastifieuse pro',cat_ids['Machines'],50000,120000,18,6,1,'unité',1),
        ('REP-013','Machine découpe PVC','Découpe vinyle',cat_ids['Machines'],150000,300000,18,3,1,'unité',1),

        ('REP-014','Magic Mirror','Cadre photo lumineux',cat_ids['Supports & Cadeaux'],3000,8000,18,30,5,'unité',1),
        ('REP-015','Thermos café','Thermos petit modèle',cat_ids['Supports & Cadeaux'],2000,5000,18,40,5,'unité',1),
        ('REP-016','Goblet personnalisé','Gobelet événement',cat_ids['Supports & Cadeaux'],500,1500,18,100,20,'unité',1),

        ('REP-017','Carte PVC','Carte rigide impression',cat_ids['Fournitures'],300,1000,18,500,50,'unité',1),
        ('REP-018','Colle double face','Adhésif pro',cat_ids['Fournitures'],500,1500,18,200,20,'rouleau',1),
        ('REP-019','Lutin documents','Support documents',cat_ids['Fournitures'],1000,2500,18,100,10,'unité',1),

        ('REP-020','Bracelet événementiel','Bracelet personnalisé',cat_ids['Événementiel'],200,800,18,500,50,'unité',1),
        ('REP-021','Sachet baptême','Sachet personnalisé',cat_ids['Événementiel'],300,1000,18,300,50,'unité',1),
        ('REP-022','Éventail personnalisé','Éventail promo',cat_ids['Événementiel'],500,1500,18,200,20,'unité',1),
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
        ('CLI-R001','Diallo','Aminata','aminata@gmail.com','+221771230000','Pikine','Dakar','Sénégal','particulier',0,1),
        ('CLI-R002','Fall','Ibrahima','fall@business.sn','+221784560000','Guédiawaye','Dakar','Sénégal','entreprise',10,1),
        ('CLI-R003','Sarr','Moussa','m.sarr@gmail.com','+221707890000','Keur Massar','Dakar','Sénégal','particulier',0,1),
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
        for _ in range(random.randint(8,20)):

            day = random.randint(1,28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=min(day,28))

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
                ))
            db.commit()

            cmd = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()
            if not cmd:
                continue

            cmd_id = cmd['id']

            for ref in random.sample(list(prod_ids.keys()), random.randint(2,5)):
                p = prod_ids[ref]
                db.execute("""INSERT INTO lignes_commande
                    (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                    VALUES (?,?,?,?,?,?)""",
                    (cmd_id, p['id'], random.randint(1,50), p['prix_vente'], random.choice([0,5]), p['tva']))
            db.commit()

            commande_count += 1

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
                    ))
                db.commit()

    print(f"✅ Seed Repro OK : {commande_count} commandes")
    db.close()


if __name__ == '__main__':
    seed()
