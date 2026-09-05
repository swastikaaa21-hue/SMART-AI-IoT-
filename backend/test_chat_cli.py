"""
SMART AI IoT - Clean Terminal Chat Interface
"""

import asyncio
import os
import sys
import uuid
import logging

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Mute all background logs/debug messages to keep console clean
os.environ["LOG_LEVEL"] = "CRITICAL"
logging.disable(logging.CRITICAL)

for log_name in ["app", "gemini_service", "sqlalchemy", "sqlalchemy.engine", "main"]:
    l = logging.getLogger(log_name)
    l.setLevel(logging.CRITICAL)
    l.propagate = False

from app.db.session import AsyncSessionLocal
from app.services.gemini_service import gemini_service
from app.api.v1.endpoints.chat import _execute_function

async def main():
    # Initialise Gemini
    gemini_service.initialise()
    session_id = str(uuid.uuid4())

    # Jika dijalankan via command `hallo jarkvis` atau ada argumen
    args = sys.argv[1:]
    wake_input = " ".join(args).strip() if args else "hallo jarkvis"

    print("=" * 60)
    print("🤖 JARKVIS - Asisten Rumah Pintar")
    print("Ketik 'keluar' atau 'exit' untuk mengakhiri.")
    print("=" * 60)
    print("Sedang menyambungkan ke Jarkvis...", end="\r", flush=True)

    # Sambut pertama kali
    async with AsyncSessionLocal() as db:
        async def executor(name: str, args_dict: dict):
            return await _execute_function(name, args_dict, db)

        try:
            response = await gemini_service.chat(
                message=wake_input,
                session_id=session_id,
                function_executor=executor,
            )
            print(" " * 40, end="\r")
            print(f"Jarkvis: {response['reply']}")
        except Exception:
            print(" " * 40, end="\r")
            print("Jarkvis: Yo! Ada yang bisa gue bantu?")

    while True:
        try:
            user_input = input("\nAnda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCabut dulu bro!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "keluar", "quit", "q"]:
            print("\nSiap, gue standby ya bro!")
            break

        print("Ngetik...", end="\r", flush=True)

        async with AsyncSessionLocal() as db:
            async def executor(name: str, args_dict: dict):
                return await _execute_function(name, args_dict, db)

            try:
                response = await gemini_service.chat(
                    message=user_input,
                    session_id=session_id,
                    function_executor=executor,
                )
                print(" " * 30, end="\r")
                print(f"Jarkvis: {response['reply']}")
            except Exception:
                print(" " * 30, end="\r")
                print("Jarkvis: Eh sori bro, lagi error dikit nih. Coba lagi ya?")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSampai jumpa!")
