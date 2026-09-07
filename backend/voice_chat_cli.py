"""
SMART AI IoT - Interactive Terminal Voice Assistant (Jarkvis).

Supports Indonesian Speech-to-Text (STT) with varied intonations,
Text-to-Speech (TTS) audio playback, and Gemini IoT Function Calling.
"""

import asyncio
import os
import sys
import threading
import time
import uuid
import logging

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Suppress background logs to keep terminal clean
os.environ["LOG_LEVEL"] = "CRITICAL"
logging.disable(logging.CRITICAL)

for log_name in ["app", "gemini_service", "voice_service", "sqlalchemy", "sqlalchemy.engine", "main"]:
    l = logging.getLogger(log_name)
    l.setLevel(logging.CRITICAL)
    l.propagate = False

from app.db.session import AsyncSessionLocal
from app.services.gemini_service import gemini_service
from app.services.voice_service import voice_service
from app.api.v1.endpoints.chat import _execute_function


class VoiceAssistantCLI:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.tts_enabled = True
        self.mode = "push_to_talk"  # "push_to_talk", "continuous", "text"

    def print_banner(self):
        print("\n" + "=" * 65)
        print("🤖  JARKVIS - Asisten Suara Pintar IoT (Bahasa Indonesia)")
        print("=" * 65)
        print("💡 Kontrol Rumah Pintar dengan Perintah Suara:")
        print("   • Tekan [ENTER]  : Mulai merekam suara Anda")
        print("   • Ketik 'c'      : Mode Continuous (Selalu mendengarkan)")
        print("   • Ketik 't'      : Mode Ketik Teks Manual")
        print("   • Ketik 's'      : Nyalakan/Matikan Suara Balasan (TTS)")
        print("   • Ketik 'keluar' : Keluar dari aplikasi")
        print("=" * 65 + "\n")

    def run_stt_callback(self, status: str, data: any):
        """Visual status indicator during voice recording."""
        if status == "calibrating":
            print("⏳ Menyesuaikan kebisingan ruangan...", end="\r", flush=True)
        elif status == "listening":
            print("🎙️  [MENDENGARKAN] Silakan bicara dalam Bahasa Indonesia...", end="\r", flush=True)
        elif status == "speech_detected":
            print("🗣️  [SUARA TERDETEKSI] Mendengarkan intonasi Anda...", end="\r", flush=True)

    async def process_command(self, user_text: str):
        """Send command to Gemini AI, execute IoT functions, and speak reply."""
        if not user_text or not user_text.strip():
            print("⚠️  Suara tidak terdeteksi atau kosong. Silakan coba lagi.")
            return

        print(f"\n🗣️  Anda: \"{user_text}\"")
        print("⚡  Jarkvis sedang memproses & mengeksekusi...", end="\r", flush=True)

        async with AsyncSessionLocal() as db:
            async def executor(name: str, args_dict: dict):
                return await _execute_function(name, args_dict, db)

            try:
                response = await gemini_service.chat(
                    message=user_text,
                    session_id=self.session_id,
                    function_executor=executor,
                )
                reply = response.get("reply", "Perintah berhasil diproses.")
                print(" " * 50, end="\r")
                print(f"🤖  Jarkvis: {reply}")

                # Play voice response in Indonesian
                if self.tts_enabled:
                    print("🔊  [Jarkvis Berbicara...]", end="\r", flush=True)
                    # Run audio playback in thread to avoid event loop blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, voice_service.speak, reply, True)
                    print(" " * 30, end="\r")

            except Exception as e:
                print(" " * 50, end="\r")
                print("🤖  Jarkvis: Maaf bro, ada kendala koneksi atau sistem.")

    async def run_voice_cycle(self) -> bool:
        """Run a single voice listening and processing cycle."""
        audio_bytes = voice_service.record_microphone(
            max_duration=12.0,
            silence_limit=1.3,
            sample_rate=16000,
            status_callback=self.run_stt_callback,
        )

        print(" " * 65, end="\r")

        if not audio_bytes:
            print("⚠️  Tidak ada suara terdeteksi. Silakan coba lagi.")
            return False

        print("🔍  Mengenali suara Bahasa Indonesia...", end="\r", flush=True)
        transcript = voice_service.transcribe_audio_bytes(audio_bytes, language="id-ID")
        print(" " * 50, end="\r")

        if not transcript or not transcript.strip():
            print("⚠️  Suara kurang jelas. Coba ucapkan dengan lebih jelas ya.")
            return False

        await self.process_command(transcript)
        return True

    async def start(self):
        # Initialise Gemini
        print("Sedang menginisialisasi Jarkvis Voice System...", end="\r", flush=True)
        gemini_service.initialise()
        self.print_banner()

        # Initial greeting with voice
        greeting = "Halo! Jarkvis siap mendengarkan perintah suara Anda."
        print(f"🤖  Jarkvis: {greeting}")
        if self.tts_enabled:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, voice_service.speak, greeting, True)

        while True:
            try:
                if self.mode == "push_to_talk":
                    prompt_info = "[🎙️ VOICE MODE] Tekan [ENTER] untuk bicara (atau ketik perintah/menu): "
                    user_input = input(f"\n{prompt_info}").strip()

                    if user_input.lower() in ["keluar", "exit", "quit", "q"]:
                        print("\n👋  Jarkvis standby. Sampai jumpa!")
                        if self.tts_enabled:
                            voice_service.speak("Sampai jumpa!", True)
                        break

                    if user_input.lower() == "s":
                        self.tts_enabled = not self.tts_enabled
                        state = "ON 🔊" if self.tts_enabled else "OFF 🔇"
                        print(f"🔊  Suara balasan Jarkvis: {state}")
                        continue

                    if user_input.lower() == "c":
                        self.mode = "continuous"
                        print("🔄  Beralih ke Mode Continuous (Selalu Mendengarkan). Tekan Ctrl+C untuk berhenti.")
                        continue

                    if user_input.lower() == "t":
                        self.mode = "text"
                        print("⌨️   Beralih ke Mode Teks.")
                        continue

                    if user_input == "":
                        # User pressed Enter -> Record Voice!
                        await self.run_voice_cycle()
                    else:
                        # User typed a text command directly
                        await self.process_command(user_input)

                elif self.mode == "continuous":
                    print("\n🎙️  [CONTINUOUS] Mendengarkan terus menerus... (Bicara langsung)")
                    success = await self.run_voice_cycle()
                    await asyncio.sleep(0.5)

                elif self.mode == "text":
                    user_input = input("\n⌨️  [TEXT] Anda: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ["keluar", "exit", "quit", "q"]:
                        print("\n👋  Jarkvis standby. Sampai jumpa!")
                        break
                    if user_input.lower() == "v":
                        self.mode = "push_to_talk"
                        print("🎙️  Beralih kembali ke Mode Suara.")
                        continue
                    if user_input.lower() == "s":
                        self.tts_enabled = not self.tts_enabled
                        state = "ON 🔊" if self.tts_enabled else "OFF 🔇"
                        print(f"🔊  Suara balasan Jarkvis: {state}")
                        continue
                    await self.process_command(user_input)

            except KeyboardInterrupt:
                if self.mode == "continuous":
                    print("\n⏸️  Kembali ke Mode Push-to-Talk.")
                    self.mode = "push_to_talk"
                    continue
                else:
                    print("\n👋  Sampai jumpa bro!")
                    break
            except Exception as e:
                print(f"\n⚠️  Error: {e}")


def main():
    try:
        assistant = VoiceAssistantCLI()
        asyncio.run(assistant.start())
    except KeyboardInterrupt:
        print("\nKeluar.")


if __name__ == "__main__":
    main()
