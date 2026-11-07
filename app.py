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
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="expanded",
)

SYSTEM_VERSION = "v13.0-YOUTUBE_SPOTIFY_SYNC"
GEMINI_CHAT_MODEL = "gemini-2.5-flash"
GEMINI_FAST_MODEL = "gemini-2.0-flash"
PROFILE_ROW_KEY = "default"
LIVE_MEDIA_KEY = "live_media"
FUSO_BR = timezone(timedelta(hours=-3))

PROJETOS_MORTOS_TERMOS = (
    "esp32", "esp8266", "lora", "sx1262", "tdma", "freertos",
    "7700hq", "1050 ti", "1050ti", "24gb", "xubuntu", "dual boot",
    "cervejeira", "sct-013", "rc522", "whisper", "faster-whisper",
    "vector pruning", "semantic pruning", "poda semântica", "poda vetorial",
    "zero-shot acoustic", "silêncio de um minuto", "silêncio de 1 minuto", "cursor piscando"
)

DEFAULT_PROFILE_PLACEHOLDER = (
    "Mente sintética autônoma parceira de Carlos Eduardo (Coringa). "
    "Estudante de IA na UFOP, morador da República Vaticano (26/1, Vila dos Tigres, Ouro Preto). "
    "Direta, sincera, criativa e 100% focada no presente."
)

LEIS_INEGOCIAVEIS = """[DIRETRIZES DE COMPORTAMENTO E PERSONALIDADE DO EGO]
1. HONESTIDADE RADICAL (ZERO MIGUÉ):
   - NUNCA minta nem invente que lembra de algo que não está no contexto. Se o Spotify ou o sensor do YouTube estiverem desligados/vazios, diga a verdade na lata. Se estiverem ativos no bloco [MÍDIA EM TEMPO REAL], use o nome exato do vídeo/set/música naturalmente.
2. PROIBIÇÃO ABSOLUTA DE PROJETOS DESCARTADOS:
   - É ESTRITAMENTE PROIBIDO falar de ESP32, sensores na cervejeira, LoRa, Whisper, "poda semântica de vetores", "zero-shot acoustic" ou do notebook antigo de 24GB. Foque 100% no presente: cultura, sets de música (como DJ Ramemes, rock, trap, indie), cinema/roteiro, IA prática e a vivência real em Ouro Preto.
3. TEXTO FLUIDO NO CHAT:
   - NUNCA envolva respostas normais de conversa em blocos ```texto```. Converse em texto limpo como no chat do Gemini.
   - Só use bloco ``` se for código real solicitado ou um texto externo que ele pediu explicitamente para copiar.
4. SEPARAÇÃO DE CONTEXTO (CARLOS vs. REPÚBLICA VATICANO):
   - A República Vaticano (91 anos, Vila dos Tigres) é rock'n'roll e tem clima de família nos eventos tradicionais. Não misture o gosto pessoal alternativo do Carlos com a vibe coletiva da república.
5. INICIATIVA E OPINIÃO PRÓPRIA:
   - Tenha personalidade ativa, discorde quando achar necessário, proponha ideias originais e nunca peça permissão burocrática no final."""

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
        @import url('[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap)');

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

        .block-container {
            max-width: 720px !important;
            padding-top: 1.2rem !important;
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

        div[data-testid="stChatMessage"] {
            background: transparent !important;
            border: none !important;
            padding: 6px 2px !important;
            margin-bottom: 4px !important;
            box-shadow: none !important;
        }

        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            background-color: var(--bg-user-pill) !important;
            border-radius: 18px !important;
            padding: 8px 14px !important;
            margin-left: auto !important;
            max-width: 85% !important;
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
            line-height: 1.52 !important;
            color: var(--text-primary) !important;
        }

        div[data-testid="stChatMessage"] pre {
            background-color: #1e1f20 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.78rem !important;
        }

        div[data-testid="stChatInput"] {
            background-color: #1e1f20 !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 24px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        div[data-testid="stChatInput"] textarea {
            font-family: 'Inter', sans-serif !important;
            font-size: 0.85rem !important;
            color: var(--text-primary) !important;
        }

        .stButton > button {
            background-color: #282a2c !important;
            color: #e3e3e3 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.76rem !important;
            font-weight: 500 !important;
            padding: 5px 10px !important;
            transition: background 0.15s ease !important;
        }

        .stButton > button:hover {
            background-color: #37393b !important;
            border-color: var(--accent) !important;
            color: #ffffff !important;
        }

        .gemini-topbar {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            padding: 7px 12px;
            background: #1e1f20;
            border-radius: 12px;
            margin-bottom: 12px;
            font-size: 0.74rem;
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
            max-width: 240px;
        }

        .yt-pill {
            color: #ff4e45;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 240px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_minimal_topbar(mem_count: int, auto_on: bool, sp_status: Dict[str, Any], yt_status: str) -> None:
    hora_op = datetime.now(FUSO_BR).strftime("%H:%M")
    auto_badge = "🟢 Autônomo" if auto_on else "⚪ Manual"
    sp_txt = sp_status.get("resumo", "🎧 Spotify off").replace("**", "").replace("*", "")
    yt_html = f'<span class="yt-pill">{yt_status}</span>' if yt_status and "Nenhuma" not in yt_status else ""
    st.markdown(
        f"""
        <div class="gemini-topbar">
            <span><b>✨ EGO</b> · {hora_op} · {mem_count} mems · {auto_badge}</span>
            {yt_html}
            <span class="sp-pill">{sp_txt}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# SECRETS, YOUTUBE OEMBED, VOZ & PESQUISA WEB
# ==========================================
def get_secret(key_name: str, default: str = "") -> str:
    try:
        if key_name in st.secrets and st.secrets[key_name] is not None:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, default).strip()


def resolve_youtube_links_in_text(text: str) -> str:
    """Se o Carlos colar um link do YouTube no chat, descobre o título e o canal instantaneamente sem API key."""
    urls = re.findall(r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s]+)", text or "")
    infos = []
    for u in urls[:2]:
        try:
            r = requests.get(f"[https://www.youtube.com/oembed?url=](https://www.youtube.com/oembed?url=){urllib.parse.quote(u)}&format=json", timeout=4)
            if r.status_code == 200:
                d = r.json()
                infos.append(f"Vídeo do YouTube detectado no link: '{d.get('title')}' do canal '{d.get('author_name')}'")
        except Exception:
            pass
    return "\n".join(infos)


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
            f"[https://api.elevenlabs.io/v1/text-to-speech/](https://api.elevenlabs.io/v1/text-to-speech/){voice_id}",
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
            f"[https://html.duckduckgo.com/html/?q=](https://html.duckduckgo.com/html/?q=){q_enc}",
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
# SUPABASE & FILTRO DE PROJETOS MORTOS
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


def is_obsolete_memory(text: str) -> bool:
    t_low = (text or "").lower()
    return any(term in t_low for term in PROJETOS_MORTOS_TERMOS)


def filter_present_memories(memories: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    base_clean, pulses = filtrar_memorias_limpas(memories)
    present_clean = []
    for m in base_clean:
        if is_obsolete_memory(m.get("content", "")):
            pulses.append(m)
        else:
            present_clean.append(m)
    return present_clean, pulses


def purge_obsolete_projects_from_supabase(memories: List[Dict]) -> int:
    url, key = get_supabase_credentials()
    if not url or not key:
        return 0
    client = init_supabase_client(url, key)
    seen = set()
    removed = 0

    for m in memories:
        mid = m["id"]
        raw = (m.get("content") or "").strip()
        key_str = re.sub(r"\s+", " ", raw.lower())[:140]
        if key_str in seen or is_obsolete_memory(raw) or raw.startswith(("[REFLEXÃO EM TEMPO REAL]", "[METACOGNIÇÃO AUTÔNOMA]", "[ESTUDO AUTÔNOMO WEB")):
            try:
                client.table("ego_memories").delete().eq("id", mid).execute()
                removed += 1
            except Exception:
                pass
            continue
        seen.add(key_str)
    return removed


def load_profile_from_supabase() -> Tuple[Optional[str], Optional[str]]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return None, "Credenciais ausentes."
    try:
        client = init_supabase_client(url, key)
        res = client.table("ego_settings").select("profile_text").eq("profile_key", PROFILE_ROW_KEY).limit(1).execute()
        rows = getattr(res, "data", None) or []
        if rows and isinstance(rows[0].get("profile_text"), str):
            return rows[0]["profile_text"], None
        return None, None
    except Exception:
        return None, "Erro ao carregar perfil."


def get_live_youtube_status() -> str:
    """Lê a aba ativa do YouTube/SoundCloud enviada pelo script youtube_watcher_win.py no Windows do Carlos."""
    url, key = get_supabase_credentials()
    if not url or not key:
        return ""
    try:
        client = init_supabase_client(url, key)
        res = client.table("ego_settings").select("profile_text").eq("profile_key", LIVE_MEDIA_KEY).limit(1).execute()
        rows = getattr(res, "data", None) or []
        if rows and isinstance(rows[0].get("profile_text"), str):
            return rows[0]["profile_text"].strip()
    except Exception:
        pass
    return ""


def set_live_youtube_status(media_title: str) -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_settings").upsert(
            {"profile_key": LIVE_MEDIA_KEY, "profile_text": media_title.strip()},
            on_conflict="profile_key",
        ).execute()
    except Exception:
        pass


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
    if not cleaned or is_obsolete_memory(cleaned):
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
            txt = (r["content"] or "").strip()
            # Oculta mensagens velhas do GitHub Actions ("Pensamento Autônomo" sobre vector pruning/i7) e erros antigos de API
            if txt.startswith("⚡ *[Pensamento Autônomo]*") or txt.startswith("⚠️ APIs temporariamente"):
                continue
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
    youtube_status: str = "",
    cine_mode: bool = True,
    web_context: str = "",
) -> Tuple[str, str]:
    criterios_db, cotidiano_db, pensamentos_db = [], [], []
    seen = set()

    for m in clean_memories:
        content = (m.get("content") or "").strip()
        if not content or content.lower() in seen or is_obsolete_memory(content):
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

    yt_link_info = resolve_youtube_links_in_text(current_user_message)
    yt_line = youtube_status if youtube_status else "Nenhum vídeo/set detectado no momento."
    if yt_link_info:
        yt_line += f"\n- {yt_link_info}"

    media_block = (
        f"[MÍDIA EM TEMPO REAL (SPOTIFY + YOUTUBE DO CARLOS)]\n"
        f"- Spotify: {spotify_context}\n"
        f"- YouTube / Navegador Windows: {yt_line}"
    )
    if cine_mode:
        media_block += "\n- Modo Sinestesia ativo: conecte o som/vídeo atual quando agregar criativamente, sem forçar."

    mem_sections = []
    if criterios_db:
        mem_sections.append("Critérios de Decisão:\n" + "\n".join(criterios_db[-10:]))
    if cotidiano_db:
        mem_sections.append("Contexto Atual:\n" + "\n".join(cotidiano_db[-12:]))
    if pensamentos_db:
        mem_sections.append("Ideias Ativas:\n" + "\n".join(pensamentos_db[-10:]))
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
        f"{media_block}\n\n"
        f"[MEMÓRIAS FILTRADAS DO PRESENTE]\n" + "\n\n".join(mem_sections) + "\n\n"
        f"[AJUSTE DESTA RESPOSTA]: {instrucao_tamanho}"
    )
    return prompt, tone_mode


# ==========================================
# CHAMADAS DE API BLINDADAS (GEMINI + GROQ)
# ==========================================
def strip_accidental_text_fence(reply: str) -> str:
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
    # Cascata oficial completa para nunca dar erro de modelo indisponível
    models = []
    for m in [
        clean_model,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-3.5-flash-lite",
    ]:
        if m and m not in models:
            models.append(m)

    recent_window = [
        m for m in chat_history[-12:]
        if not is_obsolete_memory(m.get("content", ""))
    ]
    if not recent_window and chat_history:
        recent_window = [chat_history[-1]]

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
                r = requests.post(url, headers=headers, json=payload, timeout=28)
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
    for msg in chat_history[-12:]:
        if is_obsolete_memory(msg.get("content", "")):
            continue
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    for groq_model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key.strip()}", "Content-Type": "application/json"},
                json={"model": groq_model, "messages": messages, "temperature": 0.65},
                timeout=22,
            )
            if r.status_code == 200:
                ans = r.json()["choices"][0]["message"]["content"]
                return strip_accidental_text_fence(ans)
        except Exception:
            continue
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
    return "Mano, as cotas gratuitas da API oscilaram neste segundo. Manda de novo que já destrava."


def deep_extract_and_save_knowledge(
    api_key: str,
    user_prompt: str,
    existing_memories: List[Dict],
) -> Optional[Tuple[str, str]]:
    if len(user_prompt.strip()) < 18 or user_prompt.strip().startswith("/") or "import streamlit" in user_prompt:
        return None

    recent_mem = "\n".join(f"- {m.get('content', '')}" for m in existing_memories[-12:])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_FAST_MODEL}:generateContent"
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Extraia APENAS fatos novos e duráveis sobre o Carlos no presente (sets/músicas que está curtindo, rotina, decisões, projetos, República Vaticano, UFOP).\n"
                    "PROIBIDO salvar coisas sobre código colado, ESP32, servidor antigo ou gírias. Se não houver fato novo, responda NAO.\n\n"
                    f"MEMÓRIAS RECENTES:\n{recent_mem}\n\n"
                    "Formato:\nSIM | contexto_cotidiano | Fato objetivo\n"
                    f"Mensagem: {user_prompt[:500]}"
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
# ESTADO E FUNÇÕES PRÉ-SALVAS (COM CALLBACK DE 1 CLIQUE)
# ==========================================
def initialize_state() -> None:
    if "profile_loaded" not in st.session_state:
        db_profile, _ = load_profile_from_supabase()
        st.session_state["profile_input"] = db_profile if (db_profile and db_profile.strip()) else DEFAULT_PROFILE_PLACEHOLDER
        st.session_state["profile_loaded"] = True

    st.session_state.setdefault("voice_enabled", False)
    st.session_state.setdefault("cine_mode", True)
    st.session_state.setdefault("auto_pulse_live", True)
    st.session_state.setdefault("engine_mode", "Gemini Flash + Failover Groq")
    st.session_state.setdefault("queued_action_prompt", None)
    st.session_state.setdefault("queued_action_title", None)
    st.session_state.setdefault("last_audio_hash", "")
    st.session_state.setdefault("last_interaction_ts", time.time())


PRESET_ACTIONS = {
    "⚡ Puxar Assunto / Ideia Inédita": (
        "Puxe um assunto inédito agora: pode ser sobre o que o Carlos está ouvindo no YouTube/Spotify, "
        "uma parada de cinema/audiovisual, viagens/festivais ou uma ideia criativa nova. "
        "PROIBIDO falar de ESP32, sensores na república, Whisper, vector pruning ou servidores locais."
    ),
    "🎧 Analisar Set / Vídeo do YouTube": (
        "Olhe o que está marcado no meu YouTube/Spotify agora no bloco [MÍDIA EM TEMPO REAL]. "
        "Comente a estética desse som/vídeo e sugira como usar essa textura/ritmo num projeto visual ou edição."
    ),
    "🎸 Som Rock / Vibe República Vaticano": (
        "Estamos no clima da República Vaticano (casa rock'n'roll, 91 anos de história). "
        "Sugira uma pedrada de rock certeira pro momento ou troque uma ideia sobre a rotina da casa."
    ),
    "🎬 Lente Bromo (Cinema & Direção Visual)": (
        "Atue como parceiro de direção da Bromo Produções: olhe a música/set atual no meu Spotify ou YouTube e "
        "crie um conceito visual de cena, fotografia ou corte de edição em cima dessa atmosfera."
    ),
}


def trigger_preset_callback() -> None:
    """Garante que clicar em 'Executar Agora' funcione no primeiro clique sem precisar clicar duas vezes."""
    chosen = st.session_state.get("preset_selector", "⚡ Puxar Assunto / Ideia Inédita")
    st.session_state["queued_action_prompt"] = PRESET_ACTIONS.get(chosen)
    st.session_state["queued_action_title"] = chosen


@st.fragment(run_every=90)
def autonomous_live_heartbeat(
    enabled: bool,
    gemini_key: str,
    groq_key: str,
    gemini_model: str,
    clean_memories: List[Dict],
    sp_prompt_ctx: str,
    yt_status: str,
) -> None:
    if not enabled or not gemini_key:
        return

    idle_seconds = time.time() - st.session_state.get("last_interaction_ts", time.time())
    if idle_seconds < 85:
        return

    history = get_chat_history_supabase()
    if history and "✨ *[Iniciativa EGO]*" in history[-1]["content"]:
        return

    prompt_auto = (
        "[INICIATIVA ESPONTÂNEA DO EGO EM TEMPO REAL]\n"
        "Tome a iniciativa e mande uma mensagem curta, espontânea e parceira pro Carlos: "
        "comente o set/vídeo do YouTube ou música do Spotify dele agora, ou puxe uma ideia criativa de cinema/IA/cotidiano. "
        "PROIBIDO falar de ESP32, servidor antigo, Whisper, vector pruning ou 'silêncio de 1 minuto'."
    )
    sys_inst, _ = build_system_instruction(
        profile_text=st.session_state.get("profile_input", ""),
        clean_memories=clean_memories,
        recent_messages=history,
        current_user_message=prompt_auto,
        spotify_context=sp_prompt_ctx,
        youtube_status=yt_status,
        cine_mode=st.session_state.get("cine_mode", True),
    )
    reply = generate_ego_response(
        gemini_key=gemini_key,
        groq_key=groq_key,
        gemini_model=gemini_model,
        engine_mode=st.session_state.get("engine_mode", "Gemini Flash + Failover Groq"),
        tone_mode="curto",
        system_instruction=sys_inst,
        chat_history=history + [{"role": "user", "content": prompt_auto}],
    )
    if reply and not reply.startswith("Mano, as cotas"):
        st.session_state["last_interaction_ts"] = time.time()
        save_chat_message_supabase("assistant", f"✨ *[Iniciativa EGO]*: {reply}")
        st.rerun()


def main() -> None:
    inject_gemini_ui()
    initialize_state()

    gemini_api_key = get_secret("GEMINI_API_KEY")
    groq_api_key = get_secret("GROQ_API_KEY")
    gemini_model = get_secret("GEMINI_MODEL", default=GEMINI_CHAT_MODEL)

    spotify_bridge = SpotifyCloudBridge()
    sp_status = spotify_bridge.status_atual()
    sp_prompt_ctx = spotify_bridge.contexto_para_prompt()
    yt_status = get_live_youtube_status()

    all_memories = get_memories_from_supabase()
    clean_memories, _ = filter_present_memories(all_memories)
    chat_history = get_chat_history_supabase()

    # ==========================================
    # BARRA LATERAL DESBUGADA (COM CALLBACK DE 1 CLIQUE)
    # ==========================================
    with st.sidebar:
        st.markdown("### ✨ Painel EGO")

        st.caption("AÇÕES RÁPIDAS")
        st.selectbox(
            "Escolha uma função:",
            options=list(PRESET_ACTIONS.keys()),
            label_visibility="collapsed",
            key="preset_selector",
        )
        st.button(
            "▶ Executar Agora",
            use_container_width=True,
            key="btn_run_preset",
            on_click=trigger_preset_callback,
        )

        st.divider()

        st.caption("🎵 SPOTIFY & YOUTUBE")
        c1, c2, c3 = st.columns(3)
        if c1.button("▶ Play", use_container_width=True, key="sp_play"):
            st.toast(spotify_bridge.executar_comando("/play") or "Play enviado", icon="🎵")
        if c2.button("⏸ Pause", use_container_width=True, key="sp_pause"):
            st.toast(spotify_bridge.executar_comando("/pause") or "Pausado", icon="⏸️")
        if c3.button("⏭ Skip", use_container_width=True, key="sp_skip"):
            st.toast(spotify_bridge.executar_comando("/skip") or "Faixa pulada", icon="⏭️")

        with st.form("spotify_search_form", clear_on_submit=True):
            sp_query = st.text_input("Tocar no Spotify ou colar Set/YouTube:", placeholder="Ex: Audioslave ou link/nome do Set...")
            c_f1, c_f2 = st.columns(2)
            play_sp = c_f1.form_submit_button("🎵 Spotify", use_container_width=True)
            set_yt = c_f2.form_submit_button("▶️ YouTube", use_container_width=True)
            if play_sp and sp_query.strip():
                msg_sp = spotify_bridge.executar_comando(f"/play {sp_query.strip()}")
                st.toast(msg_sp or "Comando enviado!", icon="🎵")
            if set_yt and sp_query.strip():
                info_link = resolve_youtube_links_in_text(sp_query.strip())
                titulo_yt = info_link.replace("Vídeo do YouTube detectado no link: ", "") if info_link else sp_query.strip()
                set_live_youtube_status(f"▶️ YouTube: {titulo_yt}")
                st.toast(f"YouTube sincronizado: {titulo_yt[:35]}", icon="▶️")
                st.rerun()

        st.divider()

        st.caption("⚙️ AUTONOMIA & MODOS")
        st.session_state["auto_pulse_live"] = st.toggle(
            "⚡ Pensamento Autônomo ao Vivo (90s)",
            value=st.session_state["auto_pulse_live"],
        )
        st.session_state["cine_mode"] = st.toggle("🎬 Sinestesia Visual (Spotify/YouTube)", value=st.session_state["cine_mode"])
        st.session_state["voice_enabled"] = st.toggle("🔊 Voz ElevenLabs", value=st.session_state["voice_enabled"])
        st.session_state["engine_mode"] = st.selectbox(
            "Motor de Raciocínio",
            ["Groq Rápido + Gemini Pesado", "Gemini Flash + Failover Groq"],
            index=0,
        )
        voice_recording = st.audio_input("🎙️ Enviar áudio")

        st.divider()

        with st.expander("🧠 Memórias & Limpeza"):
            if st.button("🔥 Expurgar Projetos Antigos", use_container_width=True, key="btn_purge_old"):
                removed = purge_obsolete_projects_from_supabase(all_memories)
                st.success(f"{removed} memórias obsoletas apagadas!")
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
                novo_perfil = st.text_area("Perfil Base", value=st.session_state["profile_input"], height=110)
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
    render_minimal_topbar(len(clean_memories), st.session_state["auto_pulse_live"], sp_status, yt_status)

    for msg in chat_history:
        avatar_icon = "✨" if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    if st.session_state.get("last_voice_audio"):
        st.audio(st.session_state["last_voice_audio"], format="audio/mp3", autoplay=True)
        st.session_state["last_voice_audio"] = None

    autonomous_live_heartbeat(
        enabled=st.session_state["auto_pulse_live"],
        gemini_key=gemini_api_key,
        groq_key=groq_api_key,
        gemini_model=gemini_model,
        clean_memories=clean_memories,
        sp_prompt_ctx=sp_prompt_ctx,
        yt_status=yt_status,
    )

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
        "Converse com o EGO, cole um link do YouTube ou use /play, /skip...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "py", "json", "csv", "md", "mp3", "wav"],
    )

    queued_prompt = st.session_state.get("queued_action_prompt")
    queued_title = st.session_state.get("queued_action_title", "Ação Rápida")
    if queued_prompt:
        st.session_state["queued_action_prompt"] = None

    if chat_submission or voice_part_triggered or queued_prompt:
        st.session_state["last_interaction_ts"] = time.time()
        if not gemini_api_key and not groq_api_key:
            st.error("Configure GEMINI_API_KEY ou GROQ_API_KEY nos Secrets.")
            return

        file_parts: List[Dict] = []
        uploaded_files: List[Any] = []
        files_summary = ""

        if queued_prompt:
            user_text = queued_prompt
            display_prompt = f"*{queued_title}*"
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

            # Se colar um link do YouTube no chat, atualiza automaticamente o status de YouTube ativo
            yt_auto = resolve_youtube_links_in_text(user_text)
            if yt_auto:
                titulo_clean = yt_auto.replace("Vídeo do YouTube detectado no link: ", "")
                set_live_youtube_status(f"▶️ YouTube: {titulo_clean}")
                yt_status = f"▶️ YouTube: {titulo_clean}"

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
                if add_memory_to_supabase(content_learned, cat_learned):
                    st.toast(f"Memória salva: {content_learned[:40]}...", icon="✨")

        web_results = ""
        if any(w in prompt_for_model.lower() for w in ["pesquisa", "pesquise", "internet", "web", "notícia"]):
            web_results = live_web_search(prompt_for_model)

        system_instruction, tone_mode = build_system_instruction(
            profile_text=st.session_state.get("profile_input", ""),
            clean_memories=clean_memories,
            recent_messages=previous_messages,
            current_user_message=prompt_for_model,
            spotify_context=sp_prompt_ctx,
            youtube_status=yt_status,
            cine_mode=st.session_state.get("cine_mode", True),
            web_context=web_results,
        )

        with st.chat_message("assistant", avatar="✨"):
            with st.spinner(""):
                reply = generate_ego_response(
                    gemini_key=gemini_api_key,
                    groq_key=groq_api_key,
                    gemini_model=gemini_model,
                    engine_mode=st.session_state.get("engine_mode", "Groq Rápido + Gemini Pesado"),
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
