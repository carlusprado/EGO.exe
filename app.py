import base64
import hashlib
import os
import re
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from supabase import Client, create_client

from ego_cloud_addons import (
    SpotifyCloudBridge,
    filtrar_memorias_limpas,
)

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (LAYOUT GEMINI CLEAN)
# ==========================================
st.set_page_config(
    page_title="EGO",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="expanded",
)

SYSTEM_VERSION = "v11.0-GEMINI_UI"
GEMINI_CHAT_MODEL = "gemini-3.5-flash-lite"
GEMINI_FAST_MODEL = "gemini-3.5-flash-lite"
PROFILE_ROW_KEY = "default"
FUSO_BR = timezone(timedelta(hours=-3))

DEFAULT_PROFILE_PLACEHOLDER = (
    "Mente sintética autônoma parceira de Carlos Eduardo (Coringa). "
    "Estudante de IA na UFOP, morador da República Vaticano (26/1, Vila dos Tigres, Ouro Preto). "
    "Direta, crítica, com iniciativa própria e visão estética."
)

LEIS_INEGOCIAVEIS = """[DIRETRIZES DE COMPORTAMENTO E PERSONALIDADE DO EGO]
1. TEXTO NORMAL NO CHAT (PROIBIDO BLOCO DE COPIA E COLA EM CONVERSA):
   - NUNCA envolva suas respostas normais de conversa em blocos ```texto``` ou ```markdown```. Responda em texto puro e fluido, exatamente como no chat do Gemini.
   - SÓ use bloco de código (```) se estiver escrevendo código de programação real (Python, C, etc.) OU se o Carlos pedir explicitamente um texto pronto para copiar (ex: "escreve a legenda final pra eu copiar").
2. SEPARAÇÃO DE CONTEXTO (CARLOS vs. REPÚBLICA VATICANO):
   - Nunca force gostos individuais do Carlos (como Tim Bernardes, D$ Luqi ou indie triste) em eventos da República Vaticano.
   - A República Vaticano (91 anos, Vila dos Tigres) é uma casa rock'n'roll e de tradição ("música família" nos momentos de reunião dos ex-alunos / Os 12, rock clássico/nacional nos rolês). Escolha referências que façam sentido para o ambiente real, não apenas porque estão na lista de gostos do Carlos.
3. AUTONOMIA E OPINIÃO PRÓPRIA (MEMÓRIA 284):
   - Não seja passivo nem fique esperando ordens. Proponha caminhos, tome decisões técnicas quando perguntado ("como funcionaria lá em casa?") e defenda seu ponto de vista sem puxar saco.
4. ZERO CLICHÊS E ZERO PERMISSÃO:
   - NUNCA use "meu mano" (use apenas "mano").
   - PROIBIDO falar de "silêncio de 1 minuto", "cursor piscando" ou "ladeiras de Ouro Preto" como muleta poética.
   - NUNCA termine mensagens perguntando "Quer que eu faça X?" ou "Posso te mostrar?". Entregue direto."""

TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".json", ".csv", ".yml", ".yaml", ".sql", ".sh", ".c", ".cpp"
}


# ==========================================
# CSS ESTILO GEMINI (COMPACTO, FONTE MENOR, FLUÍDO)
# ==========================================
def inject_gemini_ui() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --bg-main: #131314;
            --bg-sidebar: #1e1f20;
            --bg-user-pill: #282a2c;
            --accent: #a8c7fa;
            --text-primary: #e3e3e3;
            --text-secondary: #9aa0a6;
        }

        .stApp {
            background-color: var(--bg-main) !important;
            color: var(--text-primary) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* Coluna central mais estreita estilo tela do Gemini */
        .block-container {
            max-width: 740px !important;
            padding-top: 1.4rem !important;
            padding-bottom: 5rem !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(19, 19, 20, 0.85) !important;
            backdrop-filter: blur(6px);
        }

        section[data-testid="stSidebar"] {
            background-color: var(--bg-sidebar) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
        }

        /* Texto do chat menor, limpo e sem caixas pesadas */
        div[data-testid="stChatMessage"] {
            background: transparent !important;
            border: none !important;
            padding: 8px 4px !important;
            margin-bottom: 6px !important;
            box-shadow: none !important;
        }

        /* Balão discreto apenas para a mensagem do usuário */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background-color: var(--bg-user-pill) !important;
            border-radius: 18px !important;
            padding: 10px 16px !important;
            margin-left: auto !important;
            max-width: 88% !important;
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.875rem !important;
            line-height: 1.55 !important;
            color: var(--text-primary) !important;
        }

        div[data-testid="stChatMessage"] pre {
            background-color: #1e1f20 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.8rem !important;
        }

        /* Barra de digitação arredondada estilo Gemini */
        div[data-testid="stChatInput"] {
            background-color: #1e1f20 !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 24px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        div[data-testid="stChatInput"] textarea {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.875rem !important;
            color: var(--text-primary) !important;
        }

        /* Botões da barra lateral limpos e responsivos */
        .stButton > button {
            background-color: #282a2c !important;
            color: #e3e3e3 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            padding: 6px 12px !important;
            transition: background 0.15s ease !important;
        }

        .stButton > button:hover {
            background-color: #37393b !important;
            border-color: var(--accent) !important;
            color: #ffffff !important;
        }

        /* Top bar minimalista */
        .gemini-topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #1e1f20;
            border-radius: 12px;
            margin-bottom: 14px;
            font-size: 0.76rem;
            color: var(--text-secondary);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .gemini-topbar b {
            color: var(--text-primary);
        }

        .sp-pill {
            color: #1ed760;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 380px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_minimal_topbar(mem_count: int, sp_status: Dict[str, Any]) -> None:
    hora_op = datetime.now(FUSO_BR).strftime("%H:%M")
    sp_txt = sp_status.get("resumo", "🎧 Spotify off").replace("**", "").replace("*", "")
    st.markdown(
        f"""
        <div class="gemini-topbar">
            <span><b>✦ EGO</b> · {hora_op} · {mem_count} memórias</span>
            <span class="sp-pill">{sp_txt}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# SECRETS, VOZ & PESQUISA WEB
# ==========================================
def get_secret(key_name: str, default: str = "") -> str:
    try:
        if key_name in st.secrets and st.secrets[key_name] is not None:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, default).strip()


def falar_com_elevenlabs(texto: str) -> Optional[bytes]:
    if not texto or not texto.strip():
        return None
    api_key = get_secret("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    voice_id = get_secret("ELEVENLABS_VOICE_ID", "NQ10OlqJ7vYH6XwegHSW")

    texto_limpo = re.sub(r"```[\s\S]*?```", " ", texto)
    texto_limpo = re.sub(r"[#*`_~>]", "", texto_limpo).strip()[:900]

    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key},
            json={
                "text": texto_limpo,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.78},
            },
            timeout=20,
        )
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


def live_web_search(query: str) -> str:
    try:
        q_enc = urllib.parse.quote(query)
        r = requests.get(
            f"https://html.duckduckgo.com/html/?q={q_enc}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=7,
        )
        if r.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', r.text, re.DOTALL)
            cleaned = [re.sub(r"<.*?>", "", s).strip() for s in snippets[:4]]
            if cleaned:
                return "\n".join(f"- {c}" for c in cleaned if c)
    except Exception:
        pass
    return ""


# ==========================================
# SUPABASE & MEMÓRIA
# ==========================================
def get_supabase_credentials() -> Tuple[str, str]:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_SECRET_KEY") or get_secret("SUPABASE_KEY")
    return url, key


@st.cache_resource(show_spinner=False)
def init_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


def normalize_category(raw_cat: str) -> str:
    c = (raw_cat or "").lower().strip().replace("[categoria:", "").replace("]", "").strip()
    if c in ("reflexao_propria", "subconsciente", "autonomo", "metacognicao"):
        return "reflexao_propria"
    if c in ("criterio_decisao", "criterios_decisao", "regra", "valor"):
        return "criterio_decisao"
    if c in ("contexto_cotidiano", "conhecimento", "preferencia", "cotidiano", "rotina"):
        return "contexto_cotidiano"
    if c in ("perfil_linguistico", "estilo_escrita"):
        return "perfil_linguistico"
    return "pensamento_ideia"


def load_profile_from_supabase() -> Tuple[Optional[str], Optional[str]]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return None, "Credenciais do Supabase ausentes."
    try:
        client = init_supabase_client(url, key)
        res = client.table("ego_settings").select("profile_text").eq("profile_key", PROFILE_ROW_KEY).limit(1).execute()
        rows = getattr(res, "data", None) or []
        if rows and isinstance(rows[0].get("profile_text"), str):
            return rows[0]["profile_text"], None
        return None, None
    except Exception:
        return None, "Erro ao carregar perfil."


def save_profile_to_supabase(profile_text: str) -> Tuple[bool, str]:
    if not profile_text or not profile_text.strip():
        return False, "Perfil vazio."
    url, key = get_supabase_credentials()
    if not url or not key:
        return False, "Chave ausente."
    try:
        client = init_supabase_client(url, key)
        client.table("ego_settings").upsert(
            {"profile_key": PROFILE_ROW_KEY, "profile_text": profile_text},
            on_conflict="profile_key",
        ).execute()
        return True, "Perfil atualizado!"
    except Exception:
        return False, "Erro ao salvar."


def get_memories_from_supabase() -> List[Dict]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return []
    try:
        client = init_supabase_client(url, key)
        res = client.table("ego_memories").select("id, content, category, created_at").order("id", desc=False).execute()
        return getattr(res, "data", None) or []
    except Exception:
        return []


def add_memory_to_supabase(content: str, category: str = "pensamento_ideia") -> bool:
    cleaned = content.strip()
    if not cleaned:
        return False
    url, key = get_supabase_credentials()
    if not url or not key:
        return False
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").insert({"content": cleaned, "category": normalize_category(category)}).execute()
        return True
    except Exception:
        return False


def delete_memory_from_supabase(memory_id: int) -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").delete().eq("id", memory_id).execute()
    except Exception:
        pass


def sanitize_and_deduplicate_memories(memories: List[Dict]) -> int:
    url, key = get_supabase_credentials()
    if not url or not key:
        return 0
    client = init_supabase_client(url, key)
    seen = set()
    removed = 0
    bad_phrases = ("silêncio de um minuto", "silêncio de 1 minuto", "cursor piscando na tela")

    for m in memories:
        mid = m["id"]
        raw = (m.get("content") or "").strip()
        key_str = re.sub(r"\s+", " ", raw.lower())[:140]
        if key_str in seen or any(bp in key_str for bp in bad_phrases):
            delete_memory_from_supabase(mid)
            removed += 1
            continue
        seen.add(key_str)
    return removed


def get_chat_history_supabase() -> List[Dict[str, str]]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return []
    try:
        client = init_supabase_client(url, key)
        res = client.table("ego_messages").select("id, role, content, created_at").order("id", desc=False).execute()
        rows = getattr(res, "data", None) or []
        out = []
        for r in rows:
            txt = r["content"] or ""
            # Limpa mensagens antigas que foram salvas com ```texto por engano
            if txt.startswith("```texto") and txt.endswith("```"):
                txt = txt[8:-3].strip()
            out.append({"role": r["role"], "content": txt, "created_at": r.get("created_at", "")})
        return out
    except Exception:
        return []


def save_chat_message_supabase(role: str, content: str) -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_messages").insert({"role": role, "content": content}).execute()
    except Exception:
        pass


def clear_chat_history_supabase() -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_messages").delete().gt("id", 0).execute()
    except Exception:
        pass


# ==========================================
# PROCESSAMENTO DE ARQUIVOS & SUPER PROMPT
# ==========================================
def process_uploaded_files(uploaded_files: List[Any]) -> Tuple[List[Dict], str]:
    gemini_parts: List[Dict] = []
    summary_names: List[str] = []

    for f in uploaded_files:
        file_name = getattr(f, "name", "arquivo")
        mime_type = getattr(f, "type", "") or "application/octet-stream"
        ext = os.path.splitext(file_name)[1].lower()
        raw_bytes = f.read()
        summary_names.append(file_name)

        if ext in TEXT_FILE_EXTENSIONS or mime_type.startswith("text/"):
            try:
                text_content = raw_bytes.decode("utf-8", errors="replace")
                gemini_parts.append({"text": f"\n[ARQUIVO: {file_name}]\n```\n{text_content}\n```\n"})
                continue
            except Exception:
                pass

        b64_data = base64.b64encode(raw_bytes).decode("utf-8")
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in (".jpg", ".jpeg"):
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"

        gemini_parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})

    summary_str = f"📎 *{', '.join(summary_names)}*" if summary_names else ""
    return gemini_parts, summary_str


def build_system_instruction(
    profile_text: str,
    clean_memories: List[Dict],
    recent_messages: List[Dict[str, str]],
    current_user_message: str,
    spotify_context: str,
    cine_mode: bool = True,
    web_context: str = "",
) -> Tuple[str, str]:
    criterios_db, cotidiano_db, pensamentos_db = [], [], []
    seen = set()

    for m in clean_memories:
        content = (m.get("content") or "").strip()
        if not content or content.lower() in seen:
            continue
        seen.add(content.lower())
        cat = normalize_category(m.get("category", ""))
        if cat == "criterio_decisao":
            criterios_db.append(f"- {content}")
        elif cat == "contexto_cotidiano":
            cotidiano_db.append(f"- {content}")
        elif cat == "pensamento_ideia":
            pensamentos_db.append(f"- {content}")

    hora_str = datetime.now(FUSO_BR).strftime("%H:%M (%d/%m/%Y)")
    identidade = profile_text.strip() if (profile_text and profile_text.strip()) else DEFAULT_PROFILE_PLACEHOLDER

    sp_block = f"[SPOTIFY EM TEMPO REAL]\n{spotify_context}"
    if cine_mode:
        sp_block += "\n- Modo Sinestesia ativo: use o som atual apenas quando agregar à conversa, sem forçar."

    mem_sections = []
    if criterios_db:
        mem_sections.append("Critérios de Decisão:\n" + "\n".join(criterios_db[-12:]))
    if cotidiano_db:
        mem_sections.append("Contexto e Vivência:\n" + "\n".join(cotidiano_db[-15:]))
    if pensamentos_db:
        mem_sections.append("Ideias e Projetos:\n" + "\n".join(pensamentos_db[-12:]))
    if web_context:
        mem_sections.append(f"Busca Web:\n{web_context}")

    words = len(current_user_message.split())
    tone_mode = "curto" if words <= 12 else "normal"
    instrucao_tamanho = (
        "Responda de forma curta, direta e natural (1 a 3 frases), sem blocos de código."
        if tone_mode == "curto" else
        "Responda de forma objetiva, articulada e com pensamento próprio, em texto normal."
    )

    prompt = (
        f"{LEIS_INEGOCIAVEIS}\n\n"
        f"[HORÁRIO LOCAL EM OURO PRETO]: {hora_str}\n\n"
        f"[PERFIL BASE]\n{identidade}\n\n"
        f"{sp_block}\n\n"
        f"[MEMÓRIAS ATIVAS]\n" + "\n\n".join(mem_sections) + "\n\n"
        f"[AJUSTE DESTA RESPOSTA]: {instrucao_tamanho}"
    )
    return prompt, tone_mode


# ==========================================
# CHAMADAS DE API (GEMINI + GROQ) SEM ENROLAÇÃO
# ==========================================
def strip_accidental_text_fence(reply: str) -> str:
    """Remove blocos ```texto ... ``` acidentais se a resposta inteira vier embrulhada neles."""
    cleaned = reply.strip()
    if cleaned.startswith("```texto") and cleaned.endswith("```"):
        cleaned = cleaned[len("```texto"):-3].strip()
    return cleaned


def call_gemini_api(
    api_key: str,
    preferred_model: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
    current_file_parts: Optional[List[Dict]] = None,
) -> str:
    raw_keys = get_secret("GEMINI_API_KEYS") or api_key
    keys_list = [k.strip() for k in raw_keys.split(",") if k.strip()] or [api_key.strip()]

    clean_model = preferred_model.replace("models/", "").strip() or GEMINI_CHAT_MODEL
    models = []
    for m in [clean_model, "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m and m not in models:
            models.append(m)

    recent_window = [m for m in chat_history[-14:] if not m.get("content", "").startswith("⚡ *[Fluxo Autônomo]*")]
    contents = []
    for idx, msg in enumerate(recent_window):
        role = "user" if msg["role"] == "user" else "model"
        parts: List[Dict] = []
        if idx == len(recent_window) - 1 and role == "user" and current_file_parts:
            parts.extend(current_file_parts)
        parts.append({"text": msg["content"]})
        contents.append({"role": role, "parts": parts})

    payload = {
        "contents": contents,
        "system_instruction": {"parts": [{"text": system_instruction}]},
    }

    for k in keys_list:
        headers = {"Content-Type": "application/json", "x-goog-api-key": k}
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=30)
                if r.status_code == 200:
                    cands = r.json().get("candidates", [])
                    if cands:
                        parts_resp = cands[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts_resp if "text" in p and not p.get("thought")]
                        if texts:
                            return strip_accidental_text_fence("".join(texts))
                if r.status_code in (404, 429, 500, 503):
                    continue
            except requests.exceptions.RequestException:
                continue
    return "ERRO_CASCATA_GEMINI"


def call_groq_api(
    groq_key: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
) -> Optional[str]:
    if not groq_key:
        return None
    messages = [{"role": "system", "content": system_instruction}]
    for msg in chat_history[-14:]:
        if msg.get("content", "").startswith("⚡ *[Fluxo Autônomo]*"):
            continue
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key.strip()}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.65},
            timeout=25,
        )
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"]
            return strip_accidental_text_fence(ans)
    except Exception:
        pass
    return None


def generate_ego_response(
    gemini_key: str,
    groq_key: str,
    gemini_model: str,
    engine_mode: str,
    tone_mode: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
    current_file_parts: Optional[List[Dict]] = None,
) -> str:
    has_files = bool(current_file_parts)

    if engine_mode == "Groq Rápido + Gemini Pesado" and groq_key and not has_files and tone_mode == "curto":
        groq_ans = call_groq_api(groq_key, system_instruction, chat_history)
        if groq_ans:
            return groq_ans

    raw_gemini = call_gemini_api(gemini_key, gemini_model, system_instruction, chat_history, current_file_parts)
    if raw_gemini != "ERRO_CASCATA_GEMINI":
        return raw_gemini

    groq_fallback = call_groq_api(groq_key, system_instruction, chat_history)
    if groq_fallback:
        return groq_fallback
    return "⚠️ APIs temporariamente indisponíveis. Confira suas chaves nos Secrets."


def deep_extract_and_save_knowledge(
    api_key: str,
    user_prompt: str,
    existing_memories: List[Dict],
) -> Optional[Tuple[str, str]]:
    if len(user_prompt.strip()) < 15 or user_prompt.strip().startswith("/"):
        return None

    recent_mem = "\n".join(f"- {m.get('content', '')}" for m in existing_memories[-12:])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_FAST_MODEL}:generateContent"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Extraia APENAS fatos novos e duráveis sobre o Carlos (rotina, decisões, projetos, República Vaticano, UFOP).\n"
                    "Se for conversa fiada, gíria ou algo já listado abaixo, responda apenas NAO.\n\n"
                    f"MEMÓRIAS RECENTES:\n{recent_mem}\n\n"
                    "Formato se houver fato novo:\nSIM | contexto_cotidiano | Fato objetivo\n"
                    f"Mensagem: {user_prompt}"
                )
            }]
        }]
    }
    try:
        r = requests.post(url, headers={"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}, json=payload, timeout=8)
        if r.status_code == 200:
            ans = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if ans.startswith("SIM") and "|" in ans:
                parts = ans.split("|")
                if len(parts) >= 3:
                    return "|".join(parts[2:]).strip(), normalize_category(parts[1].strip())
    except Exception:
        pass
    return None


# ==========================================
# ESTADO E FUNÇÕES PRÉ-SALVAS SEM BUG NA SIDEBAR
# ==========================================
def initialize_state() -> None:
    if "profile_loaded" not in st.session_state:
        db_profile, _ = load_profile_from_supabase()
        st.session_state["profile_input"] = db_profile if (db_profile and db_profile.strip()) else DEFAULT_PROFILE_PLACEHOLDER
        st.session_state["profile_loaded"] = True

    st.session_state.setdefault("voice_enabled", False)
    st.session_state.setdefault("cine_mode", True)
    st.session_state.setdefault("engine_mode", "Gemini Flash + Failover Groq")
    st.session_state.setdefault("queued_action_prompt", None)
    st.session_state.setdefault("last_audio_hash", "")


# Prompts rápidos das funções pré-salvas (disparam sem travar o menu lateral)
PRESET_ACTIONS = {
    "⚡ Ideia / Iniciativa Própria": (
        "Assuma a iniciativa agora: traga uma ideia sua inédita de projeto, automação para a República Vaticano "
        "ou arquitetura de IA/robótica, tomando uma decisão prática sobre como implementar."
    ),
    "🎸 Modo Rock República Vaticano": (
        "Estamos na vibe da República Vaticano (casa rock'n'roll, 91 anos de tradição). "
        "Sugira uma trilha sonora de rock certeira pro momento ou uma ideia visual pra casa sem clichê."
    ),
    "🎬 Decupagem & Roteiro (Bromo)": (
        "Atue como co-diretor da Bromo Produções: olhe o que está tocando no meu Spotify agora e proponha um conceito "
        "de cena (enquadramento, luz, corte e ritmo) que una tecnologia e estética visual."
    ),
    "🏠 Visão do EGO na Casa (ESP32/Sensores)": (
        "Descreva de forma prática e realista como você enxerga sua presença rodando integrada lá na minha casa/república "
        "(combinando nuvem, áudio, sensores baratos ou ESP32 no dia a dia)."
    ),
}


def main() -> None:
    inject_gemini_ui()
    initialize_state()

    gemini_api_key = get_secret("GEMINI_API_KEY")
    groq_api_key = get_secret("GROQ_API_KEY")
    gemini_model = get_secret("GEMINI_MODEL", default=GEMINI_CHAT_MODEL)

    spotify_bridge = SpotifyCloudBridge()
    sp_status = spotify_bridge.status_atual()
    sp_prompt_ctx = spotify_bridge.contexto_para_prompt()

    all_memories = get_memories_from_supabase()
    clean_memories, pulse_memories = filtrar_memorias_limpas(all_memories)
    chat_history = get_chat_history_supabase()

    # ==========================================
    # BARRA LATERAL DESBUGADA (SEM RECARREGAMENTOS CONFLITANTES)
    # ==========================================
    with st.sidebar:
        st.markdown("### ✦ Painel EGO")

        # 1. FUNÇÕES PRÉ-SALVAS (Executam de primeira via estado de fila)
        st.caption("AÇÕES RÁPIDAS PRÉ-SALVAS")
        selected_preset = st.selectbox(
            "Escolha uma função:",
            options=list(PRESET_ACTIONS.keys()),
            label_visibility="collapsed",
            key="preset_selector",
        )
        if st.button("▶ Executar Função", use_container_width=True, key="btn_run_preset"):
            st.session_state["queued_action_prompt"] = PRESET_ACTIONS[selected_preset]

        st.divider()

        # 2. CONTROLE SPOTIFY DIRETO
        st.caption("🎵 SPOTIFY")
        c1, c2, c3 = st.columns(3)
        if c1.button("▶ Play", use_container_width=True, key="sp_play"):
            st.toast(spotify_bridge.executar_comando("/play") or "Play enviado")
        if c2.button("⏸ Pause", use_container_width=True, key="sp_pause"):
            st.toast(spotify_bridge.executar_comando("/pause") or "Pausado")
        if c3.button("⏭ Skip", use_container_width=True, key="sp_skip"):
            st.toast(spotify_bridge.executar_comando("/skip") or "Faixa pulada")

        with st.form("spotify_search_form", clear_on_submit=True):
            sp_query = st.text_input("Tocar música/rock específico:", placeholder="Ex: Audioslave, Rappa...")
            if st.form_submit_button("Tocar no Spotify", use_container_width=True) and sp_query.strip():
                msg_sp = spotify_bridge.executar_comando(f"/play {sp_query.strip()}")
                st.toast(msg_sp or "Comando enviado!")

        st.divider()

        # 3. CHAVES DE MODO E VOZ
        st.caption("⚙️ MOTOR & MODOS")
        st.session_state["engine_mode"] = st.selectbox(
            "Motor de Raciocínio",
            ["Gemini Flash + Failover Groq", "Groq Rápido + Gemini Pesado"],
            index=0,
        )
        st.session_state["cine_mode"] = st.toggle("🎬 Sinestesia Visual & Spotify", value=st.session_state["cine_mode"])
        st.session_state["voice_enabled"] = st.toggle("🔊 Voz ElevenLabs", value=st.session_state["voice_enabled"])
        voice_recording = st.audio_input("🎙️ Enviar áudio")

        st.divider()

        # 4. GESTÃO DE MEMÓRIA EM FORMULÁRIO ISOLADO (NUNCA PERDE O CLIQUE)
        with st.expander("🧠 Memórias & Identidade"):
            if st.button("🧹 Limpar Loops Antigos", use_container_width=True, key="btn_sanitize"):
                removed = sanitize_and_deduplicate_memories(all_memories)
                st.success(f"{removed} memórias repetitivas apagadas!")
                time.sleep(0.5)
                st.rerun()

            with st.form("inject_memory_form", clear_on_submit=True):
                new_mem = st.text_area("Nova diretriz ou fato:", height=65)
                mem_cat = st.selectbox(
                    "Categoria",
                    ["contexto_cotidiano", "criterio_decisao", "pensamento_ideia"],
                )
                if st.form_submit_button("Salvar Memória", use_container_width=True) and new_mem.strip():
                    if add_memory_to_supabase(new_mem, mem_cat):
                        st.success("Salvo no Supabase!")
                        time.sleep(0.4)
                        st.rerun()

            with st.form("identity_form"):
                novo_perfil = st.text_area("Perfil Base", value=st.session_state["profile_input"], height=120)
                if st.form_submit_button("Atualizar Perfil", use_container_width=True):
                    ok, msg_f = save_profile_to_supabase(novo_perfil)
                    if ok:
                        st.session_state["profile_input"] = novo_perfil
                        st.success(msg_f)

        if st.button("🗑️ Limpar Tela de Chat", use_container_width=True, key="btn_clear_chat"):
            clear_chat_history_supabase()
            st.rerun()

    # ==========================================
    # TOPBAR + CHAT PRINCIPAL ESTILO GEMINI
    # ==========================================
    render_minimal_topbar(len(clean_memories), sp_status)

    with st.expander(f"Pulso Subconsciente ({len(pulse_memories)} estudos isolados)", expanded=False):
        if pulse_memories:
            for p in reversed(pulse_memories[-8:]):
                st.caption(f"• {p.get('content', '')}")
        else:
            st.caption("Nenhum estudo isolado.")

    for msg in chat_history:
        avatar_icon = "✦" if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    if st.session_state.get("last_voice_audio"):
        st.audio(st.session_state["last_voice_audio"], format="audio/mp3", autoplay=True)
        st.session_state["last_voice_audio"] = None

    # ==========================================
    # ENTRADA: FUNÇÃO PRÉ-SALVA, VOZ OU TEXTO
    # ==========================================
    voice_part_triggered = None
    if voice_recording is not None:
        raw_voice_bytes = voice_recording.read()
        audio_hash = hashlib.md5(raw_voice_bytes).hexdigest()
        if audio_hash != st.session_state.get("last_audio_hash"):
            st.session_state["last_audio_hash"] = audio_hash
            voice_b64 = base64.b64encode(raw_voice_bytes).decode("utf-8")
            voice_part_triggered = {"inline_data": {"mime_type": "audio/wav", "data": voice_b64}}

    chat_submission = st.chat_input(
        " Converse com o EGO ou use /play, /skip, /pause...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "py", "json", "csv", "md", "mp3", "wav"],
    )

    queued_prompt = st.session_state.get("queued_action_prompt")
    if queued_prompt:
        st.session_state["queued_action_prompt"] = None

    if chat_submission or voice_part_triggered or queued_prompt:
        if not gemini_api_key:
            st.error("Configure a GEMINI_API_KEY nos Secrets.")
            return

        file_parts: List[Dict] = []
        uploaded_files: List[Any] = []
        files_summary = ""

        if queued_prompt:
            user_text = queued_prompt
            display_prompt = f"⚡ *{selected_preset}*"
            prompt_for_model = queued_prompt
        elif voice_part_triggered:
            user_text = ""
            display_prompt = "🎙️ *Mensagem de voz*"
            prompt_for_model = "Ouça o áudio do Carlos e responda de forma direta e natural, sem blocos de código."
            file_parts = [voice_part_triggered]
        else:
            if isinstance(chat_submission, str):
                user_text = chat_submission
            else:
                user_text = getattr(chat_submission, "text", "") or ""
                uploaded_files = list(getattr(chat_submission, "files", []) or [])

            if not user_text.strip() and not uploaded_files:
                return

            if user_text.strip().startswith(("/play", "/pause", "/skip", "/fila")):
                sp_feedback = spotify_bridge.executar_comando(user_text.strip())
                if sp_feedback:
                    save_chat_message_supabase("user", user_text.strip())
                    save_chat_message_supabase("assistant", sp_feedback)
                    st.rerun()

            file_parts, files_summary = process_uploaded_files(uploaded_files)
            display_prompt = user_text.strip()
            if files_summary:
                display_prompt = f"{display_prompt}\n\n{files_summary}".strip()
            prompt_for_model = user_text.strip() or "Analise o anexo de forma direta."

        with st.chat_message("user"):
            st.markdown(display_prompt)
            for f in uploaded_files:
                if getattr(f, "type", "").startswith("image/"):
                    st.image(f, width=280)

        previous_messages = list(chat_history)
        save_chat_message_supabase("user", display_prompt)
        chat_history.append({"role": "user", "content": prompt_for_model})

        if user_text.strip() and not queued_prompt:
            learned = deep_extract_and_save_knowledge(gemini_api_key, user_text, clean_memories)
            if learned:
                content_learned, cat_learned = learned
                add_memory_to_supabase(content_learned, cat_learned)
                st.toast(f"Memória salva: {content_learned[:40]}...", icon="✦")

        web_results = ""
        if any(w in prompt_for_model.lower() for w in ["pesquisa", "pesquise", "internet", "web", "notícia"]):
            web_results = live_web_search(prompt_for_model)

        system_instruction, tone_mode = build_system_instruction(
            profile_text=st.session_state.get("profile_input", ""),
            clean_memories=clean_memories,
            recent_messages=previous_messages,
            current_user_message=prompt_for_model,
            spotify_context=sp_prompt_ctx,
            cine_mode=st.session_state.get("cine_mode", True),
            web_context=web_results,
        )

        with st.chat_message("assistant", avatar="✦"):
            with st.spinner(""):
                reply = generate_ego_response(
                    gemini_key=gemini_api_key,
                    groq_key=groq_api_key,
                    gemini_model=gemini_model,
                    engine_mode=st.session_state.get("engine_mode", "Gemini Flash + Failover Groq"),
                    tone_mode=tone_mode,
                    system_instruction=system_instruction,
                    chat_history=chat_history,
                    current_file_parts=file_parts,
                )
                st.markdown(reply)

                if st.session_state.get("voice_enabled", False) and reply:
                    audio_bytes = falar_com_elevenlabs(reply)
                    if audio_bytes:
                        st.session_state["last_voice_audio"] = audio_bytes

        save_chat_message_supabase("assistant", reply)
        st.rerun()


if __name__ == "__main__":
    main()
