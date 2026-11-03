#!/usr/bin/env python3
"""Surveille les annonces visa Portugal (Maroc) et alerte sur Telegram.

Sources publiques (pas de connexion, pas de CAPTCHA) :
  - "Avis importants" sur la page BLS Portugal Maroc (journées portes ouvertes, etc.)
  - Actualités de l'Ambassade du Portugal à Rabat

Usage :
  python3 bot.py            vérifie une fois et alerte si quelque chose a changé
  python3 bot.py --test     envoie un message Telegram de test
  python3 bot.py --chat-id  enregistre ton identifiant Telegram (après /start)
  python3 bot.py --rappel   envoie le rappel hebdomadaire (lancé le vendredi)
"""
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CONFIG = DOSSIER / "config.json"
ETAT = DOSSIER / "etat.json"

BLS_URL = "https://www.blsinternational.com/portugal/morocco/"
AMBASSADE_URL = "https://rabat.embaixadaportugal.mne.gov.pt/fr/l-ambassade/actualites"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def telecharger(url):
    # curl plutôt que urllib : le Python d'Apple ne gère pas le TLS récent du site de l'ambassade
    r = subprocess.run(["curl", "-sSfL", "--max-time", "60", "-A", UA, url],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"{url} : {r.stderr.decode(errors='replace').strip()}")
    return r.stdout.decode("utf-8", errors="replace")


def en_texte(fragment):
    fragment = re.sub(r"<(script|style).*?</\1>", " ", fragment, flags=re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def avis_bls(page):
    """Texte de la section "Avis importants" (sans les parties commentées)."""
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    m = re.search(r"<h2>\s*Avis importants\s*</h2>(.*?)</section>", page, flags=re.S)
    if not m:
        raise ValueError("Section 'Avis importants' introuvable : la page BLS a peut-être changé.")
    return en_texte(m.group(1))


def actus_ambassade(page):
    liens = re.findall(r'href="(/fr/l-ambassade/actualites/[^"]+)"', page)
    return sorted(set(liens))


def telegram(cfg, methode, donnees=None):
    """Appelle l'API Telegram (POST pour ne pas mettre le texte dans l'URL)."""
    cmd = ["curl", "-sS", "--max-time", "30",
           f"https://api.telegram.org/bot{cfg['telegram_token']}/{methode}"]
    for cle, val in (donnees or {}).items():
        cmd += ["--data-urlencode", f"{cle}={val}"]
    r = subprocess.run(cmd, capture_output=True)
    try:
        rep = json.loads(r.stdout or b"{}")
    except json.JSONDecodeError:
        rep = {}
    if not rep.get("ok"):
        raise RuntimeError("Telegram a refusé : " + rep.get("description", r.stderr.decode(errors="replace")))
    return rep["result"]


def envoyer(cfg, texte):
    telegram(cfg, "sendMessage", {"chat_id": cfg["telegram_chat_id"], "text": texte[:4000]})
    print("Message Telegram envoyé.")


def trouver_chat_id(cfg):
    """Récupère ton identifiant de conversation après que tu as écrit au bot."""
    messages = telegram(cfg, "getUpdates")
    if not messages:
        sys.exit("Aucun message reçu : ouvre ton bot dans Telegram, appuie sur Démarrer (/start), puis relance.")
    chat_id = messages[-1]["message"]["chat"]["id"]
    cfg["telegram_chat_id"] = str(chat_id)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Identifiant enregistré dans config.json.")


def message_bls(texte):
    date = re.search(r"aura lieu le ([^.]*?\d{4}[^.]*)\.", texte)
    capacite = re.search(r"\((\d+) personnes\)", texte)
    if "portes ouvertes" in texte.lower() and date:
        msg = "🚨 VISA PORTUGAL – Journée PORTES OUVERTES à BLS Rabat, sans rendez-vous :\n" \
              f"📅 {date.group(1).strip()}"
        if capacite:
            msg += f"\n👥 Limite : {capacite.group(1)} personnes, viens TRÈS tôt."
        return msg + f"\n\nDétails : {BLS_URL}"
    return f"📢 VISA PORTUGAL – L'annonce BLS a changé :\n\n{texte[:600]}…\n\n{BLS_URL}"


def charger(chemin, defaut):
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defaut


def verifier(cfg):
    etat = charger(ETAT, {})
    premier_lancement = not etat
    alertes = []
    # Source principale : BLS. On prévient si elle échoue 3 fois de suite.
    try:
        texte = avis_bls(telecharger(BLS_URL))
        empreinte = hashlib.sha256(texte.encode()).hexdigest()
        if empreinte != etat.get("bls_empreinte"):
            alertes.append(message_bls(texte))
            etat["bls_empreinte"] = empreinte
        etat["echecs"] = 0
    except Exception as e:  # site indisponible, page modifiée…
        etat["echecs"] = etat.get("echecs", 0) + 1
        print("Erreur :", e, file=sys.stderr)
        if etat["echecs"] == 3:  # une seule alerte, après 3 échecs de suite
            alertes.append(f"⚠️ Bot visa : 3 vérifications BLS ratées de suite.\nDernière erreur : {e}")

    # Source secondaire : l'ambassade (bloque les serveurs GitHub). Échec silencieux.
    try:
        liens = actus_ambassade(telecharger(AMBASSADE_URL))
        nouveaux = [l for l in liens if l not in etat.get("ambassade_liens", [])]
        if nouveaux and "ambassade_liens" in etat:
            titres = "\n".join("• " + urllib.parse.unquote(l.rsplit("/", 1)[-1]).replace("-", " ")
                               for l in nouveaux)
            alertes.append(f"🏛️ Nouvelle actualité de l'Ambassade du Portugal :\n{titres}\n\n{AMBASSADE_URL}")
        etat["ambassade_liens"] = liens
    except Exception as e:
        print("Ambassade inaccessible :", e, file=sys.stderr)

    if premier_lancement:
        alertes.insert(0, "✅ Bot visa Portugal activé. Tu seras alerté à chaque nouvelle annonce.\n"
                          "Annonce actuelle ci-dessous 👇")
    for a in alertes:
        envoyer(cfg, a)
    if not alertes:
        print("Rien de nouveau.")
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    cfg = charger(CONFIG, None)
    if os.environ.get("TELEGRAM_TOKEN"):  # sur GitHub Actions : secrets du dépôt
        cfg = {"telegram_token": os.environ["TELEGRAM_TOKEN"],
               "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")}
    if not cfg or "XXXX" in cfg.get("telegram_token", "XXXX"):
        sys.exit("Mets d'abord le code de ton bot Telegram dans config.json (voir README.md).")
    if "--chat-id" in sys.argv:
        return trouver_chat_id(cfg)
    if not cfg.get("telegram_chat_id"):
        sys.exit("Lance d'abord : python3 bot.py --chat-id")
    if "--test" in sys.argv:
        envoyer(cfg, "👋 Test du bot visa Portugal : ça marche !")
    elif "--rappel" in sys.argv:
        envoyer(cfg, "⏰ Vendredi : jour d'ouverture des rendez-vous visa Portugal.\n"
                     f"Connecte-toi vite sur BLS : {BLS_URL}")
    else:
        verifier(cfg)


if __name__ == "__main__":
    main()
