# Bot alerte visa Portugal (Rabat, Schengen court séjour)

Ce bot surveille toutes les 15 minutes :
- les **« Avis importants » de BLS Portugal Maroc**, où sont annoncées les journées
  **portes ouvertes sans rendez-vous** à Rabat (130 places, annoncées ~1 jour avant) ;
- les **actualités de l'Ambassade du Portugal à Rabat**.

Dès qu'une annonce change, tu reçois un **message Telegram**. Chaque **vendredi à 8h**, tu reçois
aussi un rappel pour essayer de réserver un rendez-vous sur le site BLS.

Le bot ne se connecte pas à ton compte BLS et ne réserve rien : il lit seulement des pages publiques.
C'est toi qui réserves ou qui te déplaces.

## 1. Créer ton bot Telegram (gratuit, 3 min)
1. Dans Telegram, cherche **@BotFather** (badge bleu officiel) et envoie `/newbot`.
2. Donne un nom (ex. `Alerte Visa`) puis un identifiant finissant par `bot` (ex. `alerte_visa_othman_bot`).
3. BotFather te donne un **token** du type `123456789:AAH…`. Colle-le dans `config.json`
   à la place de `XXXX`, entre les guillemets.
4. Clique sur le lien de ton bot (donné par BotFather) et appuie sur **Démarrer** (`/start`).

## 2. Relier et tester
```
python3 bot.py --chat-id
python3 bot.py --test
```
Tu dois recevoir « 👋 Test du bot visa Portugal : ça marche ! » dans Telegram.


## 3. Lancer en automatique
```
./installer.sh
```
Le Mac doit rester **allumé et pas en veille** pour que le bot tourne.
Journal : `~/.bot-visa-portugal/bot.log`. Pour tout arrêter : `./desinstaller.sh`.

Si tu modifies `config.json` après l'installation, relance `./installer.sh`.

## Version en ligne (Mac éteint) : GitHub Actions
Le fichier `.github/workflows/surveillance.yml` fait tourner le bot sur GitHub, gratuitement,
toutes les 15 minutes, plus un rappel le vendredi à 8h (heure du Maroc).
Le token et l'identifiant Telegram sont des **secrets** du dépôt (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`),
jamais dans le code. `etat.json` garde en mémoire les annonces déjà vues.

Lancer à la main : onglet **Actions** du dépôt → « Surveillance visa Portugal » → **Run workflow**
(mode `test` pour recevoir un message de test).
