@echo off
REM Launch BabysitterPOC in Claude Code via WSL
wt.exe -p "Ubuntu" --title "BabysitterPOC - Claude Code" wsl -d Ubuntu -- bash -c "cd /home/grees/greesCoding/claude-projects/babysitterPOC && exec bash -c 'claude code'"
