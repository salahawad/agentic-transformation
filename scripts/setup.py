"""Create local configuration without overwriting existing credentials."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
env = root / '.env'
if env.exists():
    print('.env already exists; existing configuration preserved.')
else:
    env.touch(mode=0o600)
    env.write_text(f'ADMIN_PASSWORD={secrets.token_urlsafe(24)}\nPORT=8180\nBIND_ADDRESS=127.0.0.1\nCOOKIE_SECURE=false\n')
    print('Created private .env. Your administrator password is in this file.')
print('Start: docker compose up --build -d --wait')
print('Open: http://localhost:8180')
