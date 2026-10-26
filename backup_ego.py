from datetime import datetime
import json
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

DB_CONNECTION_STRING = os.environ.get("SUPABASE_DB_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_TABLES = ["ego_settings", "ego_memories", "ego_messages"]

def enviar_para_telegram(caminho_arquivo, timestamp):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(caminho_arquivo, "rb") as f:
        files = {"document": f}
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": f"🧠 Backup automático do EGO.exe realizado com sucesso!\n📅 Data: {timestamp}"
        }
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            print("✅ Backup enviado com sucesso para o teu Telegram!")
        else:
            print(f"❌ Erro ao enviar para o Telegram: {response.text}")
            sys.exit(1)

def realizar_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"[{timestamp}] Iniciando extração do Supabase...")

    if not DB_CONNECTION_STRING or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERRO: Faltam variáveis de ambiente nos Secrets do GitHub.")
        sys.exit(1)

    backup_payload = {
        "metadata": {"project": "EGO.exe", "timestamp": timestamp},
        "database_dump": {}
    }

    conexao = psycopg2.connect(DB_CONNECTION_STRING, cursor_factory=RealDictCursor, connect_timeout=30)
    try:
        with conexao.cursor() as cursor:
            for tabela in TARGET_TABLES:
                cursor.execute(f"SELECT * FROM public.{tabela};")
                registros = cursor.fetchall()
                registros_limpos = []
                for row in registros:
                    row_limpa = {}
                    for k, v in row.items():
                        if isinstance(v, datetime):
                            row_limpa[k] = v.isoformat()
                        else:
                            row_limpa[k] = v
                    registros_limpos.append(row_limpa)
                backup_payload["database_dump"][tabela] = {"total": len(registros_limpos), "data": registros_limpos}

        nome_arquivo = f"ego_backup_{timestamp}.json"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f, ensure_ascii=False, indent=4)

        enviar_para_telegram(nome_arquivo, timestamp)
        os.remove(nome_arquivo) # Limpa o arquivo local após o envio

    except Exception as e:
        print(f"❌ Erro no processo: {e}")
        sys.exit(1)
    finally:
        conexao.close()

if __name__ == "__main__":
    realizar_backup()
