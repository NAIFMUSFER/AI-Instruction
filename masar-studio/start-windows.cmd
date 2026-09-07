@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
 echo Node.js 22.16 or newer is required. Read README.md.
 pause
 exit /b 1
)
echo Open http://localhost:3000 in your browser after the server starts.
node --env-file-if-exists=.env server/server.mjs
pause
