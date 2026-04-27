# 🏪 Gestion Commerciale — Application Web Complète (Flask)

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-Lightweight-black)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)
![License](https://img.shields.io/badge/License-MIT-orange)

> 💼 Une application moderne de **gestion commerciale complète** (Produits, Clients, Commandes, Factures, Paiements, Statistiques) utilisable en local ou en production.

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

## 🆕 Nouvelles fonctionnalités (Version V4)

- 🖼️ **Images produits** (upload et affichage)
- 💳 **Méthodes de paiement personnalisées**
  - QR Code (Wave, Orange Money, bancaire…)
  - Numéro de téléphone marchand
- 🧾 **Factures intelligentes**
  - QR Code intégré pour paiement
  - Numéro de paiement affiché
  - Compatible Mobile Money & Banque
- 💰 Préparation à l’intégration **paiements digitaux**

---

## 📦 Modules & Fonctionnalités

| Module | Fonctionnalités |
|---|---|
| **📊 Dashboard** | KPIs en temps réel, dernières commandes, top produits |
| **📦 Produits** | CRUD, images, catégories, stock, alertes rupture, TVA |
| **👥 Clients** | CRUD, particuliers/entreprises, remises |
| **🧾 Commandes** | Multi-lignes, remises dynamiques |
| **💰 Factures** | Génération + QR paiement + suivi |
| **💳 Paiements** | QR code, téléphone, méthodes personnalisées |
| **🖨️ PDF** | Factures professionnelles avec QR code |
| **📈 Statistiques** | CA, top clients/produits |
| **⚙️ Paramètres** | Infos entreprise, branding |

---

## 🧠 Points forts

- ⚡ Ultra rapide (Flask + SQLite)
- 🎨 Interface moderne (Tailwind CSS)
- 📄 PDF professionnel (ReportLab)
- 📊 Graphiques dynamiques (Chart.js)
- 💳 Support Mobile Money (Wave, Orange Money…)
- 🔌 API REST intégrée
- 🧩 Architecture simple et extensible
- 💻 Fonctionne **offline en local**

---

## 🚀 Installation (Développement)

### 1. Cloner le projet

```bash
git clone git@github.com:aliou90/Gestion-Commerciale-App---App-Complet.git
cd Gestion-Commerciale-App---App-Complet
````

---

### 2. Installer les dépendances

```bash
pip install flask reportlab matplotlib qrcode pillow
```

---

### 3. Lancer l'application

```bash
python3 app.py
```

👉 Ouvrir :

```
http://127.0.0.1:5000
```

---

### 4. Charger les données de démo

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
├── static/        ← images produits & QR
└── templates/
```

---

## ⚙️ Configuration

Depuis **Paramètres** :

* Nom entreprise
* Adresse / Contact
* NINEA / RCCM
* Devise
* Logo / Branding
* QR Code paiement
* Numéro Mobile Money

👉 Utilisé automatiquement dans les **factures PDF**

---

## 📊 API REST

| Endpoint                       | Description  |
| ------------------------------ | ------------ |
| `/api/stats/ca_mensuel`        | CA mensuel   |
| `/api/stats/top_produits`      | Top produits |
| `/api/stats/clients_top`       | Top clients  |
| `/api/stats/statuts_commandes` | Répartition  |
| `/api/stats/evolution_clients` | Croissance   |

---

## 🖨️ Facture PDF (Pro)

* Logo entreprise
* Infos légales
* Tableau détaillé
* TVA automatique
* QR Code paiement
* Numéro Mobile Money
* Format imprimable

---

## 🚀 Déploiement

### Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

### Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install flask reportlab matplotlib qrcode pillow gunicorn
CMD ["gunicorn","-w","4","-b","0.0.0.0:8000","app:app"]
```

---

## 🔐 Sécurité (à améliorer)

* Authentification
* HTTPS
* CSRF
* Backup DB

---

## 💡 Roadmap

* 🔑 Auth utilisateurs
* ☁️ SaaS multi-entreprises
* 📱 Mobile App
* 💳 Paiement en ligne (Wave API, Stripe)
* 📦 Fournisseurs
* 📤 Export Excel

---

## 👨‍💻 Auteur

**Taysir Digital Group**
📧 [taysirdigitalgroup@gmail.com](mailto:taysirdigitalgroup@gmail.com)
📞 +221 76 455 03 58

---

## ⭐ Support

👉 Mets une ⭐
👉 Partage 🙌

---

## 📜 Licence

MIT License

```
