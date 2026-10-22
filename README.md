# Restock Tracker

Surveillance automatique de restocks Pokemon sur les sites francais.
Notifications Telegram instantanees quand un produit revient en stock.

## Deploiement en 1 clic (gratuit)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/lorenzoddqx/loloytb)

Apres le clic :
1. Connecte-toi avec GitHub
2. Remplis `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`
3. Clique "Apply" — le site est en ligne en 2 minutes

## Sites surveilles (14 sites fiables)

| Priorite | Sites |
|----------|-------|
| Haute | Amazon, Pokemon Center |
| Moyenne | Fnac, Micromania, Cultura, JoueClub, King Jouet, Smyths Toys, Philibert, Cardmarket |
| Normale | Cdiscount, Carrefour, Leclerc, Auchan |

+ tout autre site web via le scraper generique.

## Fonctionnement

- Scan automatique toutes les 30 secondes
- Amazon et Pokemon Center scannes en priorite
- Notification Telegram instantanee quand un produit revient en stock
- Dashboard web avec suivi en temps reel
- Historique des prix

## Configuration Telegram

1. Ouvre Telegram, cherche `@BotFather`
2. Envoie `/newbot`, choisis un nom
3. Copie le token
4. Envoie un message a ton bot, puis va sur `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Copie le `chat_id`
