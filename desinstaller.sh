#!/bin/bash
# Arrête et supprime le bot.
for n in com.botvisa.verif com.botvisa.rappel; do
  launchctl unload "$HOME/Library/LaunchAgents/$n.plist" 2>/dev/null
  rm -f "$HOME/Library/LaunchAgents/$n.plist"
done
rm -rf "$HOME/.bot-visa-portugal"
echo "Bot arrêté et supprimé."
