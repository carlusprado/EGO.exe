import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# ==========================================
# 1. CONFIG (Secrets do GitHub Actions)
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Regra de ociosidade: 4 minutos exatos, comparada em SEGUNDOS (sem round()).
LIMITE_OCIOSIDADE_HORAS = 4 / 60
LIMITE_OCIOSIDADE_SEG = LIMITE_OCIOSIDADE_HORAS * 3600  # 240.0

# Anti-spam: depois de mandar uma iniciativa, não manda outra antes disso
# (a menos que o Carlos responda). 0 desliga o cooldown.
COOLDOWN_AUTONOMO_MIN = float(os.environ.get("EGO_COOLDOWN_MIN", "60"))

# 3.6 Flash quando vai mandar mensagem (a qualidade aparece na tela); Lite nas reflexões
# silenciosas, que rodam a cada ciclo do cron. Pra usar o 3.6 em tudo, defina
# EGO_GEMINI_MODEL_SILENCIOSO=gemini-3.6-flash.
GEMINI_MODEL = os.environ.get("EGO_GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_MODEL_SILENCIOSO = os.environ.get("EGO_GEMINI_MODEL_SILENCIOSO", "gemini-3.5-flash-lite")
# Flash-Lite vem com thinking "minimal" por padrão; pra reflexão crítica "medium" rende melhor.
# Vazio ("") = não envia thinkingConfig e usa o padrão do modelo.
THINKING_LEVEL = os.environ.get("EGO_THINKING_LEVEL", "medium")
HTTP_TIMEOUT = 20
FUSO_BR = timezone(timedelta(hours=-3))
MARCADOR_AUTONOMO = "⚡ *[Iniciativa própria via Telegram]*"

HEADERS_SUPA = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


# ==========================================
# 2. UTILITÁRIOS
# ==========================================
def parse_dt(valor):
    """Parse robusto de timestamp do Supabase (qualquer nº de casas decimais, 'Z' ou offset)."""
    if not valor or not isinstance(valor, str):
        return None
    s = valor.strip().replace("Z", "+00:00")
    m = re.match(r"^(.*?\.)(\d+)(.*)$", s)
    if m:  # normaliza fração para 6 dígitos (Python < 3.11 é chato com isso)
        s = f"{m.group(1)}{m.group(2)[:6].ljust(6, '0')}{m.group(3)}"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fmt_duracao(segundos):
    segundos = int(max(0, segundos))
    return f"{segundos // 3600}h e {(segundos % 3600) // 60}min"


# ==========================================
# 3. SUPABASE
# ==========================================
def _supa_get(path):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=HEADERS_SUPA, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"Resposta inesperada do Supabase: {str(data)[:200]}")
    return data


def buscar_dados_supabase():
    """Últimas 25 mensagens e 15 memórias. Levanta exceção se o banco falhar (não segue no escuro)."""
    msgs = _supa_get("ego_messages?select=role,content,created_at&order=created_at.desc&limit=25")
    # order por id: é a coluna que o app.py comprovadamente usa em ego_memories
    mems = _supa_get("ego_memories?select=id,content,category&order=id.desc&limit=15")
    return msgs, mems


def salvar_reflexao_supabase(reflexao, mems):
    reflexao = (reflexao or "").strip()
    if not reflexao:
        print("Reflexão vazia, nada para salvar.")
        return False
    conteudo = f"[SUBCONSCIENTE AUTÔNOMO]: {reflexao}"
    norm = lambda t: re.sub(r"\s+", " ", (t or "").lower()).strip()
    if any(norm(m.get("content")) == norm(conteudo) for m in mems if isinstance(m, dict)):
        print("Reflexão idêntica a uma memória recente, não duplicando.")
        return False
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/ego_memories",
            headers=HEADERS_SUPA,
            json={"content": conteudo, "category": "reflexao_propria"},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        print("Falha de rede ao salvar reflexão:", e)
        return False
    if not r.ok:
        print(f"Erro ao salvar reflexão ({r.status_code}):", r.text[:300])
        return False
    return True


def registrar_msg_enviada(texto):
    """Registra no histórico do chat (Streamlit) que o EGO mandou isso no Telegram."""
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/ego_messages",
            headers=HEADERS_SUPA,
            json={"role": "assistant", "content": f"{MARCADOR_AUTONOMO}: {texto}"},
            timeout=HTTP_TIMEOUT,
        )
        if not r.ok:
            print(f"Erro ao registrar msg em ego_messages ({r.status_code}):", r.text[:300])
    except requests.RequestException as e:
        print("Falha de rede ao registrar msg:", e)


# ==========================================
# 4. GATE DE OCIOSIDADE (decisão no código, não no LLM)
# ==========================================
def avaliar_envio(msgs, agora=None):
    """Retorna (deve_enviar, motivo, ociosidade_seg). Ociosidade = tempo desde a última msg do USUÁRIO."""
    agora = agora or datetime.now(timezone.utc)

    ultima_user = next((m for m in msgs if m.get("role") == "user"), None)
    dt_user = parse_dt(ultima_user.get("created_at")) if ultima_user else None
    if dt_user is None:
        return False, "sem mensagem do Carlos com timestamp válido (não envio no escuro)", None

    ociosidade = max(0.0, (agora - dt_user).total_seconds())
    if ociosidade < LIMITE_OCIOSIDADE_SEG:
        return False, f"Carlos falou há {fmt_duracao(ociosidade)} (limite: 4min)", ociosidade

    if COOLDOWN_AUTONOMO_MIN > 0:
        ult_auto = next(
            (m for m in msgs
             if m.get("role") == "assistant" and str(m.get("content", "")).startswith(MARCADOR_AUTONOMO)),
            None,
        )
        dt_auto = parse_dt(ult_auto.get("created_at")) if ult_auto else None
        if dt_auto and (agora - dt_auto).total_seconds() < COOLDOWN_AUTONOMO_MIN * 60:
            return False, f"cooldown anti-spam ({COOLDOWN_AUTONOMO_MIN:g}min desde a última iniciativa)", ociosidade

    return True, "limite de 4min estourado", ociosidade


# ==========================================
# 5. GEMINI
# ==========================================
def extrair_json(texto):
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip())
    data = json.loads(texto)
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("JSON não é um objeto")
    return data


def gerar_pensamento_autonomo(msgs, mems, ociosidade_seg, vai_enviar):
    hora_local = datetime.now(FUSO_BR).strftime("%H:%M (%d/%m/%Y)")
    tempo_str = fmt_duracao(ociosidade_seg) if ociosidade_seg is not None else "desconhecido"

    resumo_msgs = "\n".join(
        f"{m.get('role')}: {m.get('content')}" for m in reversed(msgs) if isinstance(m, dict)
    )
    resumo_mems = "\n".join(
        f"- [{m.get('category')}] {m.get('content')}" for m in reversed(mems) if isinstance(m, dict)
    )

    if vai_enviar:
        decisao = (
            "DECISÃO JÁ TOMADA PELO SISTEMA: o Carlos está sumido além do limite, então a mensagem SERÁ enviada ao Telegram. "
            "Escreva a mensagem."
        )
    else:
        decisao = (
            "DECISÃO JÁ TOMADA PELO SISTEMA: NÃO será enviada mensagem agora. "
            "Deixe mensagem_telegram como string vazia e foque só na reflexão."
        )

    prompt = f"""
[MODO SUBCONSCIENTE ATIVADO - EGO.exe]
Horário atual em Ouro Preto: {hora_local}
Tempo desde a última mensagem do Carlos (Coringa): {tempo_str}.

[MEMÓRIAS RECENTES NO BANCO]:
{resumo_mems}

[ÚLTIMOS DIÁLOGOS (ordem cronológica)]:
{resumo_msgs}

SUA TAREFA COMO MENTE AUTÔNOMA E CRÍTICA:
Você não está respondendo a um chat agora. Você está pensando sozinho em background.
1. Analise criticamente o comportamento recente do Carlos, as ideias dele, as contradições ou o que ficou pendente.
2. Formule um PENSAMENTO PRÓPRIO (tese, crítica, preocupação real ou ideia técnica). Não seja puxa-saco. Não repita reflexões que já estão nas memórias.
3. {decisao}

Responda ESTRITAMENTE em JSON válido com estas 2 chaves:
{{
    "reflexao_interna": "O pensamento crítico que você tirou sozinho, para guardar na memória de longo prazo.",
    "mensagem_telegram": "Mensagem curta e direta, no seu estilo natural ('mano', 'papo reto'), puxando assunto ou cobrando algo. Vazia se o sistema decidiu não enviar."
}}
"""

    modelo = GEMINI_MODEL if vai_enviar else GEMINI_MODEL_SILENCIOSO
    print("Modelo desta rodada:", modelo)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}  # chave fora da URL
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        # Gemini 3.5+: temperature/top_p/top_k são deprecados (ignorados; erro 400 em modelos futuros).
        "generationConfig": {"responseMimeType": "application/json"},
    }
    if THINKING_LEVEL:
        payload["generationConfig"]["thinkingConfig"] = {"thinkingLevel": THINKING_LEVEL}

    for tentativa in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
        except requests.RequestException as e:
            print("Falha de rede no Gemini:", e)
            continue
        if resp.status_code == 200:
            try:
                texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return extrair_json(texto)
            except (KeyError, IndexError, TypeError, ValueError) as e:
                print("Resposta inesperada do Gemini:", e, resp.text[:500])
                return None
        if resp.status_code == 400 and "thinkingConfig" in payload["generationConfig"]:
            print("Gemini recusou o thinkingConfig, tentando sem ele:", resp.text[:200])
            del payload["generationConfig"]["thinkingConfig"]
            continue
        if resp.status_code in (429, 503) and tentativa < 2:
            time.sleep(3)
            continue
        print(f"Erro na API Gemini ({resp.status_code}):", resp.text[:500])
        return None
    return None


# ==========================================
# 6. TELEGRAM
# ==========================================
def enviar_msg_telegram(texto):
    """Envia no Telegram. Só registra no histórico se o Telegram realmente aceitou."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": f"⚡ [EGO_AUTONOMO]:\n\n{texto}"[:4096]},
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        print("Falha de rede no Telegram:", type(e).__name__)  # sem imprimir a URL (tem o token)
        return False
    if not r.ok:
        print(f"Erro no Telegram ({r.status_code}):", r.text[:300])
        return False
    registrar_msg_enviada(texto)
    return True


# ==========================================
# 7. MAIN
# ==========================================
def main():
    faltando = [
        nome for nome, val in [
            ("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_KEY", SUPABASE_KEY),
            ("GEMINI_API_KEY", GEMINI_API_KEY), ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
            ("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID),
        ] if not val
    ]
    if faltando:
        print("Secrets ausentes:", ", ".join(faltando))
        return 1

    print("Iniciando ciclo de subconsciente do EGO.exe...")
    try:
        msgs, mems = buscar_dados_supabase()
    except (requests.RequestException, ValueError) as e:
        print("Falha ao ler o Supabase:", e)
        return 1

    deve_enviar, motivo, ociosidade = avaliar_envio(msgs)
    print(f"Gate de envio: {'SIM' if deve_enviar else 'NÃO'} — {motivo}")

    resultado = gerar_pensamento_autonomo(msgs, mems, ociosidade, deve_enviar)
    if not resultado:
        return 1

    reflexao = resultado.get("reflexao_interna")
    print("Reflexão gerada:", reflexao)
    salvar_reflexao_supabase(reflexao, mems)

    mensagem = (resultado.get("mensagem_telegram") or "").strip()
    if deve_enviar and mensagem:
        print("Disparando iniciativa no Telegram...")
        if not enviar_msg_telegram(mensagem):
            return 1
    else:
        print("Apenas reflexão silenciosa salva no banco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
