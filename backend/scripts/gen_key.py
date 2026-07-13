"""Run with: python scripts/gen_key.py
Prints a fresh Fernet key to paste into TOKEN_ENCRYPTION_KEY in .env"""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(Fernet.generate_key().decode())
