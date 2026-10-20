# Restock Tracker

Application web pour surveiller les restocks et nouvelles sorties de produits (ETB Pokemon, consoles, etc.) sur plusieurs sites e-commerce.

## Sites supportes

- Amazon (FR, US, DE, UK)
- Fnac
- Micromania
- Pokemon Center
- Cdiscount
- Cultura

## Notifications

- **Discord** — webhook vers un salon de ton choix
- **Email** — alertes par email (Gmail ou autre SMTP)
- **Console** — affichage dans le terminal

## Installation

```bash
# Cloner le repo
git clone https://github.com/lorenzoddqx/loloytb.git
cd loloytb

# Installer les dependances
pip install -r requirements.txt

# Configurer les notifications
cp .env.example .env
# Editer .env avec tes identifiants Discord/email

# Lancer l'application
python app.py
```

L'app sera accessible sur `http://localhost:5000`

## Utilisation

1. Ouvrir `http://localhost:5000` dans ton navigateur
2. Coller le lien d'un produit a surveiller
3. L'app verifie automatiquement toutes les 2 minutes (configurable)
4. Tu recois une notification Discord/email des qu'un produit revient en stock

## Configuration (.env)

| Variable | Description |
|---|---|
| `DISCORD_WEBHOOK_URL` | URL du webhook Discord |
| `EMAIL_SENDER` | Adresse email d'envoi |
| `EMAIL_PASSWORD` | Mot de passe d'application |
| `EMAIL_RECEIVER` | Adresse email de reception |
| `CHECK_INTERVAL` | Intervalle de verification en secondes (defaut: 120) |
