"""
Script pour peupler la base avec des données de démonstration.
Exécuter une seule fois : python3 seed_demo.py
"""
import sqlite3, os, random
from datetime import date, timedelta, datetime

DB = os.path.join(os.path.dirname(__file__), 'database.db')

def seed():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    # ── Catégories
    cats = ['Électronique', 'Vêtements', 'Alimentation', 'Fournitures Bureau', 'Cosmétiques']
    cat_ids = {}
    for c in cats:
        try:
            db.execute("INSERT OR IGNORE INTO categories(nom) VALUES (?)", (c,))
        except: pass
    db.commit()
    for row in db.execute("SELECT id, nom FROM categories"):
        cat_ids[row['nom']] = row['id']

    # ── Produits
    produits = [
        ('ELEC-001','Smartphone Galaxy A54',cat_ids.get('Électronique'),15000,195000,18,50,5,'unité'),
        ('ELEC-002','Écouteurs Bluetooth',cat_ids.get('Électronique'),3500,18500,18,80,10,'unité'),
        ('ELEC-003','Chargeur USB-C 65W',cat_ids.get('Électronique'),2000,8500,18,120,15,'unité'),
        ('ELEC-004','Câble HDMI 2m',cat_ids.get('Électronique'),800,3500,18,200,20,'unité'),
        ('VET-001','T-shirt coton Bio',cat_ids.get('Vêtements'),1500,6500,0,150,20,'unité'),
        ('VET-002','Jean slim stretch',cat_ids.get('Vêtements'),4500,22000,0,80,10,'unité'),
        ('VET-003','Robe Wax imprimée',cat_ids.get('Vêtements'),5000,28000,0,60,8,'unité'),
        ('ALI-001','Huile d\'arachide 5L',cat_ids.get('Alimentation'),3200,5500,0,300,30,'bidon'),
        ('ALI-002','Riz parfumé 25kg',cat_ids.get('Alimentation'),12000,18500,0,200,25,'sac'),
        ('ALI-003','Café Touba 500g',cat_ids.get('Alimentation'),1200,3500,0,400,50,'sachet'),
        ('FOU-001','Ramette papier A4',cat_ids.get('Fournitures Bureau'),1800,4500,18,300,30,'ramette'),
        ('FOU-002','Stylo Bille (lot 12)',cat_ids.get('Fournitures Bureau'),500,2200,18,500,50,'lot'),
        ('FOU-003','Classeur A4',cat_ids.get('Fournitures Bureau'),800,2800,18,400,40,'unité'),
        ('COS-001','Crème hydratante 200ml',cat_ids.get('Cosmétiques'),2500,9500,18,200,20,'tube'),
        ('COS-002','Savon Karité 100g',cat_ids.get('Cosmétiques'),500,2200,18,500,50,'unité'),
    ]
    prod_ids = {}
    for p in produits:
        try:
            db.execute("""INSERT OR IGNORE INTO produits (reference,nom,categorie_id,prix_achat,prix_vente,tva,stock,stock_min,unite)
                VALUES (?,?,?,?,?,?,?,?,?)""", p)
        except Exception as e:
            print(f"Produit {p[0]}: {e}")
    db.commit()
    for row in db.execute("SELECT id, reference, prix_vente, tva FROM produits"):
        prod_ids[row['reference']] = {'id': row['id'], 'prix': row['prix_vente'], 'tva': row['tva']}

    # ── Clients
    clients = [
        ('CLI-0001','Diallo','Amadou','amadou.diallo@email.sn','+221 77 123 45 67','Rue 12 Medina','Dakar','Sénégal','entreprise',5),
        ('CLI-0002','Ndiaye','Fatou','f.ndiaye@gmail.com','+221 70 234 56 78','VDN Sacré-Cœur','Dakar','Sénégal','particulier',0),
        ('CLI-0003','Sow','Ousmane','o.sow@sow-trading.sn','+221 78 345 67 89','Rue des Almadies','Dakar','Sénégal','entreprise',10),
        ('CLI-0004','Ba','Mariama','m.ba@hotmail.com','+221 76 456 78 90','Rufisque Centre','Rufisque','Sénégal','particulier',0),
        ('CLI-0005','Diop','Ibrahima','i.diop@diop-sarl.sn','+221 77 567 89 01','Zone Industrielle','Thiès','Sénégal','entreprise',8),
        ('CLI-0006','Sarr','Rokhaya','r.sarr@gmail.com','+221 70 678 90 12','Pikine Icotaf','Pikine','Sénégal','particulier',0),
        ('CLI-0007','Fall','Cheikh','cheikh.fall@fall-group.sn','+221 78 789 01 23','Plateau','Dakar','Sénégal','entreprise',15),
        ('CLI-0008','Mbaye','Adja',None,'+221 76 890 12 34','Grand Yoff','Dakar','Sénégal','particulier',0),
    ]
    cli_ids = []
    for c in clients:
        try:
            db.execute("""INSERT OR IGNORE INTO clients (code,nom,prenom,email,telephone,adresse,ville,pays,type_client,remise)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", c)
        except: pass
    db.commit()
    cli_ids = [r['id'] for r in db.execute("SELECT id FROM clients ORDER BY id")]

    # ── Commandes (12 mois de données)
    statuts = ['en_attente','confirmee','confirmee','expediee','livree','livree','livree','annulee']
    prod_list = list(prod_ids.keys())
    today = date.today()

    commande_count = 0
    for mois_back in range(11, -1, -1):
        nb_cmd = random.randint(6, 15)
        for _ in range(nb_cmd):
            day = random.randint(1, 28)
            cmd_date = (today.replace(day=1) - timedelta(days=30*mois_back)).replace(day=min(day, 28))
            num = f"CMD-{cmd_date.strftime('%Y%m')}-{commande_count+1:04d}"
            client_id = random.choice(cli_ids)
            statut = random.choice(statuts)
            remise_glob = random.choice([0, 0, 0, 5, 10])
            try:
                db.execute("""INSERT OR IGNORE INTO commandes (numero,client_id,date_commande,statut,remise_globale)
                    VALUES (?,?,?,?,?)""",
                    (num, client_id, cmd_date.isoformat(), statut, remise_glob))
                db.commit()
                cmd_id = db.execute("SELECT id FROM commandes WHERE numero=?", (num,)).fetchone()['id']

                # Lignes (2 à 5 produits par commande)
                nb_lignes = random.randint(2, 5)
                prods_choisis = random.sample(prod_list, min(nb_lignes, len(prod_list)))
                for ref in prods_choisis:
                    p = prod_ids[ref]
                    qte = random.randint(1, 10)
                    remise_ligne = random.choice([0, 0, 0, 5])
                    db.execute("""INSERT INTO lignes_commande (commande_id,produit_id,quantite,prix_unitaire,remise,tva)
                        VALUES (?,?,?,?,?,?)""",
                        (cmd_id, p['id'], qte, p['prix'], remise_ligne, p['tva']))
                db.commit()
                commande_count += 1

                # Facture pour commandes livrées
                if statut == 'livree':
                    fac_num = f"FAC-{cmd_date.strftime('%Y%m')}-{commande_count:04d}"
                    ech = (cmd_date + timedelta(days=30)).isoformat()
                    statut_fac = random.choice(['payee','payee','payee','non_payee'])
                    try:
                        db.execute("""INSERT OR IGNORE INTO factures (numero,commande_id,client_id,date_facture,date_echeance,statut)
                            VALUES (?,?,?,?,?,?)""",
                            (fac_num, cmd_id, client_id, cmd_date.isoformat(), ech, statut_fac))
                        db.commit()
                    except: pass

            except Exception as e:
                print(f"Erreur commande {num}: {e}")

    print(f"✅ Données de démo insérées: {commande_count} commandes sur 12 mois")
    db.close()

if __name__ == '__main__':
    seed()
