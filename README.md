# 🏪 Gestion Commerciale — Application Web Complète (Flask)

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-Lightweight-black)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)
![License](https://img.shields.io/badge/License-MIT-orange)

> 💼 Une application moderne de **gestion commerciale complète** (Produits, Clients, Commandes, Factures, Statistiques) utilisable en local ou en production.

---

## 🚀 Aperçu de l'application

### 📊 Tableau de bord
![Dashboard](Screenshots/1%20Tableau%20de%20bord.png)

### 📦 Produits
![Produits](Screenshots/2%20Produits.png)

### 👥 Clients
![Clients](Screenshots/3%20Cliens.png)

### 🧾 Commandes
![Commandes](Screenshots/4%20Commandes.png)

### 💰 Factures
#### Liste
![Factures](Screenshots/5%201%20Factures%20List.png)

#### Détail
![Facture détail](Screenshots/5%202%20Facture%20details.png)

#### PDF imprimé
![Facture PDF](Screenshots/5%203%20Facture%20imprimée.png)

### 📈 Statistiques
![Stats 1](Screenshots/6%20Statistiques%201.png)
![Stats 2](Screenshots/6%20Statistiques%202.png)
![Stats 3](Screenshots/6%20Statistiques%203.png)

### ⚙️ Paramètres
![Paramètres](Screenshots/Param%C3%A8tres%201.png)
![Paramètres](Screenshots/Param%C3%A8tres%202.png)
![Paramètres](Screenshots/Param%C3%A8tres%203.png)

---

## 📦 Modules & Fonctionnalités

| Module | Fonctionnalités |
|---|---|
| **📊 Dashboard** | KPIs en temps réel, dernières commandes, top produits |
| **📦 Produits** | CRUD, catégories, stock, alertes rupture, TVA, prix HT/TTC |
| **👥 Clients** | CRUD, particuliers/entreprises, remises, contacts |
| **🧾 Commandes** | Multi-lignes, remises dynamiques, calculs automatiques |
| **💰 Factures** | Génération depuis commande, suivi paiement |
| **🖨️ PDF** | Factures professionnelles (logo, TVA, totaux) |
| **📈 Statistiques** | CA mensuel, top produits/clients, analytics |
| **⚙️ Paramètres** | Infos boutique, devise, thème, catégories |

---

## 🧠 Points forts

- ⚡ Ultra rapide (Flask + SQLite)
- 🎨 Interface moderne (Tailwind CSS)
- 📄 PDF professionnel (ReportLab)
- 📊 Graphiques dynamiques (Chart.js)
- 🔌 API REST intégrée
- 🧩 Architecture simple et extensible
- 💻 Fonctionne **offline en local**

---

## 🚀 Installation (Développement)

### 1. Cloner le projet

```bash
git clone git@github.com:aliou90/Gestion-Commerciale-App.git
cd Gestion-Commerciale-App
````

---

### 2. Installer les dépendances

```bash
pip install flask reportlab matplotlib
```

---

### 3. Lancer l'application

```bash
python3 app.py
```

👉 Ouvrir dans le navigateur :

```
http://127.0.0.1:5000
```

---

### 4. (Optionnel) Charger des données de démo

```bash
python3 seed_demo.py
```

---

## 📁 Structure du projet

```
gestion_commerciale/
├── app.py
├── seed_demo.py
├── database.db
├── README.md
├── Screenshots/
└── templates/
```

---

## ⚙️ Configuration

Depuis le menu **Paramètres** :

* Nom de la boutique
* Adresse / Contact
* NINEA / RCCM
* Devise (FCFA, € , $)
* Couleur principale
* Catégories produits

👉 Ces données sont automatiquement utilisées dans les **factures PDF**

---

## 📊 API REST (Statistiques)

| Endpoint                       | Description              |
| ------------------------------ | ------------------------ |
| `/api/stats/ca_mensuel`        | CA mensuel               |
| `/api/stats/top_produits`      | Produits les plus vendus |
| `/api/stats/clients_top`       | Meilleurs clients        |
| `/api/stats/statuts_commandes` | Répartition              |
| `/api/stats/evolution_clients` | Croissance clients       |

---

## 🖨️ Génération PDF

* Logo entreprise
* Infos légales
* Tableau détaillé
* TVA calculée
* Totaux propres
* Format professionnel imprimable

---

## 🚀 Déploiement en Production

### Option 1 — Gunicorn (recommandé)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

### Option 2 — Docker (option avancée)

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install flask reportlab matplotlib gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

---

### Option 3 — Hébergement VPS

* Nginx + Gunicorn
* SSL (Let's Encrypt)
* Reverse proxy

---

## 🔐 Sécurité (à améliorer en prod)

* Ajouter authentification (login)
* Protection CSRF
* HTTPS obligatoire
* Sauvegarde base SQLite

---

## 💡 Roadmap (Améliorations possibles)

* 🔑 Authentification utilisateurs
* ☁️ Version SaaS multi-entreprises
* 📱 Version mobile (Flutter / Android)
* 💳 Paiement intégré
* 📦 Gestion fournisseurs
* 📤 Export Excel / CSV

---

## 👨‍💻 Auteur

**Taysir Digital Group**
📧 Contact : (à taysirdigitalgroup@gmail.com | +221 76 455 03 58)

---

## ⭐ Support

Si ce projet t'aide :

👉 Mets une ⭐ sur le repo
👉 Partage 🙌

---

## 📜 Licence

MIT License

```
