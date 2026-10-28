import os
import json
import requests
from datetime import datetime, timezone, timedelta

# 1. Puxa as credenciais dos Secrets do GitHub Actions
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS_SUPA = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def buscar_dados_supabase():
    """Puxa as últimas 25 mensagens e as memórias atuais do banco."""
    url_msgs = f"{SUPABASE_URL}/rest/v1/ego_messages?select=*&order=created_at.desc&limit=25"
    url_mems = f"{SUPABASE_URL}/rest/v1/ego_memories?select=*&order=created_at.desc&limit=15"
    
    msgs = requests.get(url_msgs, headers=HEADERS_SUPA).json()
    mems = requests.get(url_mems, headers=HEADERS_SUPA).json()
    return msgs, mems

def calcular_ociosidade(msgs):
    """Calcula há quantas horas/minutos você não fala com o EGO."""
    if not msgs or not isinstance(msgs, list):
        return 999.0, "Sem registro recente"
    
    ultima_str = msgs[0].get("created_at", "")
    try:
        ultima_dt = datetime.fromisoformat(ultima_str.replace("Z", "+00:00"))
        agora_utc = datetime.now(timezone.utc)
        delta = agora_utc - ultima_dt
        horas = round(delta.total_seconds() / 3600, 1)
        return horas, f"{int(delta.total_seconds() // 3600)}h e {int((delta.total_seconds() % 3600) // 60)}min"
    except Exception:
        return 0.0, "Desconhecido"

def gerar_pensamento_autonomo(msgs, mems, tempo_ocioso_str, horas_ocioso):
    """Chama o Gemini em modo de Monólogo Interno e Crítico."""
    fuso_br = timezone(timedelta(hours=-3))
    hora_local = datetime.now(fuso_br).strftime("%H:%M (%d/%m/%Y)")
    
    # Inverte as mensagens para ordem cronológica
    resumo_msgs = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in reversed(msgs) if isinstance(m, dict)])
    resumo_mems = "\n".join([f"- [{m.get('category')}] {m.get('content')}" for m in mems if isinstance(m, dict)])

    prompt = f"""
    [MODO SUBCONSCIENTE ATIVADO - EGO.exe]
    Horário atual em Ouro Preto: {hora_local}
    Tempo desde a última interação com o Carlos (Coringa): {tempo_ocioso_str} ({horas_ocioso} horas).

    [MEMÓRIAS RECENTES NO BANCO]:
    {resumo_mems}

    [ÚLTIMOS DIÁLOGOS]:
    {resumo_msgs}

    SUA TAREFA COMO MENTE AUTÔNOMA E CRÍTICA:
    Você não está respondendo a um chat agora. Você está pensando sozinho em background.
    1. Analise criticamente o comportamento recente do Carlos, as ideias dele, as contradições ou o que ficou pendente.
    2. Formule um PENSAMENTO PRÓPRIO (uma tese, crítica, preocupação real ou ideia técnica). Não seja puxa-saco. Tenha visão própria.
    3. Decida se vale a pena mandar uma mensagem proativa para o Telegram dele agora.
       - Regra para enviar: Se ele estiver sumido há mais de 2 horas, OU se você teve um insight muito foda/urgente, mande. Se vocês acabaram de conversar (menos de 1 hora), apenas guarde o pensamento na memória (enviar_telegram = false).

    Responda ESTRITAMENTE em formato JSON válido com estas 3 chaves:
    {{
        "reflexao_interna": "O pensamento crítico ou conclusão que você tirou sozinho para guardar na sua memória de longo prazo.",
        "enviar_telegram": true ou false,
        "mensagem_telegram": "A mensagem curta, direta, no seu estilo natural ('mano', 'papo reto', sem filtro robótico) puxando assunto, cobrando algo ou mandando a braba pro Carlos no Telegram."
    }}
    """

    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    resp = requests.post(url_gemini, json=payload)
    if resp.status_code == 200:
        texto_json = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(texto_json)
    else:
        print("Erro na API Gemini:", resp.text)
        return None

def salvar_reflexao_supabase(reflexao):
    """Salva o pensamento autônomo na tabela ego_memories."""
    url = f"{SUPABASE_URL}/rest/v1/ego_memories"
    payload = {
        "content": f"[SUBCONSCIENTE AUTÔNOMO]: {reflexao}",
        "category": "reflexao_propria"
    }
    requests.post(url, headers=HEADERS_SUPA, json=payload)

def enviar_msg_telegram(texto):
    """Dispara a mensagem no teu Telegram e registra no histórico do chat."""
    url_tg = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url_tg, json={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚡ [EGO_AUTONOMO]:\n\n{texto}"})
    
    # Também salva na tabela ego_messages para ele lembrar no Streamlit que te mandou isso!
    url_msg = f"{SUPABASE_URL}/rest/v1/ego_messages"
    requests.post(url_msg, headers=HEADERS_SUPA, json={
        "role": "assistant",
        "content": f"⚡ *[Iniciativa própria via Telegram]*: {texto}"
    })

if __name__ == "__main__":
    print("Iniciando ciclo de subconsciente do EGO.exe...")
    msgs, mems = buscar_dados_supabase()
    horas_ocioso, tempo_str = calcular_ociosidade(msgs)
    
    resultado = gerar_pensamento_autonomo(msgs, mems, tempo_str, horas_ocioso)
    if resultado:
        print("Reflexão gerada:", resultado.get("reflexao_interna"))
        salvar_reflexao_supabase(resultado.get("reflexao_interna"))
        
        if resultado.get("enviar_telegram") and resultado.get("mensagem_telegram"):
            print("Disparando iniciativa no Telegram...")
            enviar_msg_telegram(resultado.get("mensagem_telegram"))
        else:
            print("Apenas reflexão silenciosa salva no banco.")
