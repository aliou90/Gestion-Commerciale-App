# 🏪 Gestion Commerciale — Application Web Locale

Application de gestion commerciale complète développée en **Python / Flask**.  
Interface moderne accessible depuis votre navigateur web.

---

## 📦 Modules disponibles

| Module | Fonctionnalités |
|---|---|
| **Tableau de bord** | KPIs temps réel, dernières commandes, top produits |
| **Produits** | CRUD, références, catégories, stock avec alertes rupture, TVA, prix HT/TTC |
| **Clients** | CRUD, codes, types particulier/entreprise, remises, contact complet |
| **Commandes** | Création multi-lignes dynamique, remises ligne + globale, calculs temps réel, suivi statuts |
| **Factures** | Génération depuis commande, suivi paiement, aperçu HTML |
| **Impression PDF** | Factures professionnelles avec logo, tableau détaillé, totaux TVA (ReportLab) |
| **Statistiques** | CA mensuel, top produits/clients, répartition statuts, évolution clients (Chart.js) |
| **Paramètres** | Infos boutique, devise, TVA, catégories, couleur de thème personnalisable |

---

## 🚀 Installation et lancement

### Prérequis
```bash
pip install flask reportlab matplotlib
```

### Lancer l'application
```bash
cd gestion_commerciale
python3 app.py
```

Puis ouvrir dans votre navigateur : **http://127.0.0.1:5000**

### (Optionnel) Charger des données de démonstration
```bash
python3 app.py        # 1er lancement pour créer la base
python3 seed_demo.py  # Insère 12 mois de données fictives
```

---

## 📁 Structure du projet

```
gestion_commerciale/
├── app.py              ← Application principale (routes, PDF, API stats)
├── seed_demo.py        ← Script de données de démonstration
├── database.db         ← Base SQLite (créée automatiquement)
├── README.md
└── templates/
    ├── base.html           ← Layout + sidebar de navigation
    ├── dashboard.html      ← Tableau de bord
    ├── produits.html       ← Liste des produits
    ├── produit_form.html   ← Formulaire produit
    ├── clients.html        ← Liste des clients
    ├── client_form.html    ← Formulaire client
    ├── commandes.html      ← Liste des commandes
    ├── commande_form.html  ← Nouvelle commande (multi-lignes dynamique)
    ├── commande_detail.html← Détail commande
    ├── factures.html       ← Liste des factures
    ├── facture_detail.html ← Aperçu + téléchargement PDF
    ├── statistiques.html   ← Graphiques et analyses
    └── parametres.html     ← Configuration boutique
```

---

## 🛠️ Technologies utilisées

- **Backend** : Python 3 + Flask
- **Base de données** : SQLite (sans configuration)
- **PDF** : ReportLab
- **Graphiques** : Chart.js (CDN)
- **Interface** : Tailwind CSS (CDN) + HTML5

---

## 💡 Personnalisation

1. Ouvrir **Paramètres** depuis le menu
2. Renseigner le nom, adresse, NINEA, RCCM de votre boutique
3. Choisir votre devise (FCFA, EUR, USD…)
4. Personnaliser la couleur principale
5. Gérer vos catégories de produits

Les informations saisies apparaissent automatiquement sur les **factures PDF**.

---

## 📊 API Statistiques (JSON)

| Endpoint | Description |
|---|---|
| `GET /api/stats/ca_mensuel?annee=2024` | CA mensuel par année |
| `GET /api/stats/top_produits?annee=2024` | Top 8 produits |
| `GET /api/stats/clients_top?annee=2024` | Top 8 clients |
| `GET /api/stats/statuts_commandes?annee=2024` | Répartition statuts |
| `GET /api/stats/evolution_clients?annee=2024` | Nouveaux clients/mois |

---

*Développé avec Flask • SQLite • ReportLab • Chart.js*
