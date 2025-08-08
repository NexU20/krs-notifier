import json
import requests
import datetime
import os

# --- Parameter konfigurasi ---
NIM = os.getenv("NIM")
PASSWORD = os.getenv("PASSWORD")
TAHUN_MASUK = 2023
TOKEN_BOT = os.getenv("TELEGRAM_BOT_TOKEN")
# CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# CHAT_ID = "1309796236"
URL = f"https://api.telegram.org/bot{TOKEN_BOT}/getUpdates"
known_chat_ids = set()

user_agent = "Mozilla/5.0"
endpoint_base = "https://api.uinjkt.ac.id/ais/resources/mahasiswa-v3/penawaran_krs/"

# Util: get chat_ids from Telegram
def get_chat_ids():
    response = requests.get(URL)
    data = response.json()

    for result in data.get("result", []):
        chat_id = result["message"]["chat"]["id"]
        if chat_id not in known_chat_ids:
            known_chat_ids.add(chat_id)
            with open("chat_ids.txt", "a") as f:
                f.write(str(chat_id) + "\n")

# User: get chat_ids from file
def load_chat_ids(file_path="chat_ids.txt"):
    try:
        with open(file_path, "r") as f:
            chat_ids = [line.strip() for line in f.readlines() if line.strip()]
            print(list(set(chat_ids)))
            return list(set(chat_ids))  # menghapus duplikat
    except FileNotFoundError:
        print("File chat_ids.txt tidak ditemukan.")
        return []

# --- Hitung semester saat ini ---
def get_sms(tahun_masuk):
    now = datetime.datetime.now()
    tahun_ini = now.year
    bulan_ini = now.month
    semester_ke = 1 if bulan_ini >= 8 else 2  # Ganjil = Agustus+, Genap = Januari - Juli
    sms = ((tahun_ini - tahun_masuk) * 2) + semester_ke
    return sms

# --- Ambil JWT token untuk autentikasi ---
def login():
    url = f"https://api.uinjkt.ac.id/ais/resources/mahasiswa-v3/login/{NIM}/{PASSWORD}"
    try:
        response = requests.post(url)
        response.raise_for_status()
        data = response.json()

        if data.get("code") == "200" and data.get("status") == "OK":
            token = data["data"].get("token")
            print("Login berhasil. Token diterima.")
            return token
        else:
            print("Login gagal:", data["data"].get("token"))
            return None
    except Exception as e:
        print("Kesalahan saat login:", str(e))
        return None


# --- Format isi perkuliahan untuk pesan telegram ---
def format_perkuliahan(perkuliahan_list, sms):
    lines = [f"Oh Great Master, KRS anda untuk semester {sms} sudah bisa diisi, berikut matakuliah yang tersedia:\n"]
    for i, kuliah in enumerate(perkuliahan_list, start=1):
        nama = kuliah.get("matakuliahNama", "MATAKULIAH TIDAK DIKETAHUI")
        dosen = kuliah.get("dosen1Nama", "DOSEN TIDAK DIKETAHUI")
        lines.append(f"{i}. {nama} ({dosen})")
    return "\n".join(lines)


# --- Kirim notifikasi ke Telegram ---
def send_telegram_message(bot_token, message, chat_ids):
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, data=payload)
            print(f"Sent to {chat_id}: {response.status_code}")
        except Exception as e:
            print(f"Error sending to {chat_id}: {e}")

# def kirim_notifikasi(pesan):
#     if not TOKEN_BOT or not CHAT_ID:
#         print("⚠️ Token Telegram atau Chat ID tidak ditemukan di env.")
#         return

#     url = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
#     payload = {"chat_id": CHAT_ID, "text": pesan}
#     response = requests.post(url, data=payload)

#     if response.status_code == 200:
#         print("📨 Notifikasi berhasil dikirim kepada Master.")
#     else:
#         print("❗ Gagal mengirim notifikasi:", response.text)

# --- Proses utama pengecekan ---
def cek_krs(token):
    sms = get_sms(TAHUN_MASUK)
    url = f"{endpoint_base}{sms}"
    headers = {
        "Token": f"{token}"
    }

    print(f"🔍 Mengecek status KRS semester {sms}...")

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            if data and isinstance(data.get("perkuliahan"), list) and len(data["perkuliahan"]) > 0 or data is not None:
                pesan = format_perkuliahan(data["perkuliahan"], sms)
                print("✅ KRS tersedia, mengirim notifikasi ke Master...")
                chat_ids = load_chat_ids()  # Ambil chat_ids dari file
                send_telegram_message(TOKEN_BOT, pesan + "\n\nPraise The Fool!", chat_ids)
                # kirim_notifikasi(pesan + "\n\nPraise The Fool!")
            else:
                print("❌ KRS belum tersedia (data kosong/null).")
        else:
            print(f"⚠️ Status error dari API: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"💥 Terjadi error saat cek KRS: {e}")

# --- Jalankan ---
if __name__ == "__main__":
    get_chat_ids()  # Ambil chat_ids dari Telegram
    login_token = login()
    # print("🔑 Token login:", login_token)
    cek_krs(login_token)