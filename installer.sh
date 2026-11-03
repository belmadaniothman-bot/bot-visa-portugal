#!/bin/bash
# Installe le bot pour qu'il tourne tout seul sur le Mac :
#  - vérification toutes les 15 minutes
#  - rappel WhatsApp chaque vendredi à 8h00
# Le bot est copié dans ~/.bot-visa-portugal (macOS bloque l'accès au Bureau
# pour les tâches automatiques).
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.bot-visa-portugal"
AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$DEST" "$AGENTS"
cp "$SRC/bot.py" "$SRC/config.json" "$DEST/"

ecrire_plist() { # $1 = nom, $2 = argument du bot, $3 = planification
  cat > "$AGENTS/$1.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$1</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>$DEST/bot.py</string>$2
  </array>
  $3
  <key>StandardOutPath</key><string>$DEST/bot.log</string>
  <key>StandardErrorPath</key><string>$DEST/bot.log</string>
</dict></plist>
EOF
  launchctl unload "$AGENTS/$1.plist" 2>/dev/null || true
  launchctl load "$AGENTS/$1.plist"
}

ecrire_plist com.botvisa.verif "" \
  "<key>StartInterval</key><integer>900</integer><key>RunAtLoad</key><true/>"
ecrire_plist com.botvisa.rappel "<string>--rappel</string>" \
  "<key>StartCalendarInterval</key><dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>"

echo "✅ Bot installé. Journal : $DEST/bot.log"
