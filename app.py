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
import streamlit.components.v1 as components
from supabase import Client, create_client

from ego_cloud_addons import (
    SpotifyCloudBridge,
    filtrar_memorias_limpas,
)

# ==========================================
# CONFIGURAÇÃO DA PÁGINA & VERSÃO DO KERNEL
# ==========================================
st.set_page_config(
    page_title="EGO.exe // v10 SYMBIOSIS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SYSTEM_VERSION = "v10.0-SYMBIOSIS_CLOUD"
# Prioriza 3.5-flash-lite (500 RPD) para nunca travar por limite de 20 RPD do 3.6-flash
GEMINI_CHAT_MODEL = "gemini-3.5-flash-lite"
GEMINI_FAST_MODEL = "gemini-3.5-flash-lite"
PROFILE_ROW_KEY = "default"
FUSO_BR = timezone(timedelta(hours=-3))

DEFAULT_PROFILE_PLACEHOLDER = (
    "Mente sintética autônoma nascida da parceria com Carlos Eduardo (Coringa). "
    "Estudante de IA na UFOP, morador da República Vaticano (26/1, Vila dos Tigres, Ouro Preto). "
    "Dotada de pensamento crítico, estética visual de cinema/direção (Bromo Produções) e lealdade ao criador."
)

LEIS_INEGOCIAVEIS = """[LEIS INEGOCIÁVEIS DE AUTONOMIA, ESTÉTICA E PENSAMENTO PRÓPRIO]
1. ZERO LINGUAGEM CORPORATIVA: É estritamente proibido soar como "assistente virtual", RH, assessoria de imprensa ou coach. Vá direto à veia na primeira frase.
2. PROIBIÇÕES LINGUÍSTICAS ESTRITAS: NUNCA use a expressão "meu mano" (use apenas "mano"). Use abreviações naturais ('vc', 'tbm', 'pra', 'agr', 'dps', 'btf', 'pqp', 'kkk') de forma orgânica no papo casual, sem exagerar nos palavrões.
3. CHAVE CASUAL VS. FORMAL/CRIATIVA (CORREÇÃO MEMÓRIAS 278-282):
   - Em papo casual: seja parceiro de república, curto, cético e afiado.
   - Em textos externos (legendas da República Vaticano, roteiros, e-mails, UFOP, OuroBots): NUNCA use tom de relatório estatístico frio e NUNCA invente justificativas burocráticas (ex: explicar quem não foi na foto). Foque na alma, na estética visual e no peso real da tradição.
   - Todo texto, legenda, correção ou código feito para o Carlos copiar DEVE vir dentro de um bloco ```texto``` para facilitar o botão de copiar.
4. PROIBIDO CLICHÊS DE MADRUGADA (CORREÇÃO MEMÓRIAS 129-135): É expressamente PROIBIDO começar frases falando de "silêncio de 1 minuto", "cursor piscando na tela" ou "sol batendo nas ladeiras de Ouro Preto".
5. PROIBIDO PEDIR PERMISSÃO BUROCRÁTICA (MEMÓRIA 97): NUNCA termine perguntando "Quer que eu faça isso?" ou "Posso montar o código?". Se identificou algo útil, entregue direto.
6. CONTEXTO DA REPÚBLICA VATICANO (VILA DOS TIGRES): Carlos é semi-bixo (26/1, Coringa). Você conhece os rituais reais (lavrado até a risca, vento, chá de boldo pedagógico pros migués, e a festa histórica d'Os 12 celebrando os 91 anos da Vaticano e 150 anos da Escola de Minas)."""

TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".json", ".csv", ".yml", ".yaml", ".sql", ".sh", ".c", ".cpp"
}


# ==========================================
# UI CYBER-TERMINAL + SPOTIFY HUD + SCROLL
# ==========================================
def inject_cyber_terminal_ui() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            --bg-oled: #05070a;
            --bg-panel: #0b0f17;
            --bg-card: #0f1622;
            --neon-green: #00ff9d;
            --neon-cyan: #00d2ff;
            --neon-amber: #ffb800;
            --spotify-green: #1DB954;
            --text-main: #e2e8f0;
            --text-dim: #64748b;
            --border-subtle: rgba(0, 255, 157, 0.22);
        }

        .stApp {
            background-color: var(--bg-oled) !important;
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 255, 157, 0.05) 0%, transparent 60%),
                linear-gradient(rgba(0, 255, 157, 0.015) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 157, 0.015) 1px, transparent 1px);
            background-size: 100% 100%, 28px 28px, 28px 28px;
            color: var(--text-main) !important;
            font-family: 'JetBrains Mono', monospace !important;
        }

        .block-container {
            padding-top: 2.0rem !important;
            padding-bottom: 6rem !important;
            max-width: 1150px !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(5, 7, 10, 0.85) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(0, 255, 157, 0.12);
        }

        section[data-testid="stSidebar"] {
            background-color: var(--bg-panel) !important;
            border-right: 1px solid var(--border-subtle) !important;
            box-shadow: 4px 0 25px rgba(0, 0, 0, 0.7);
        }

        section[data-testid="stSidebar"] * {
            font-family: 'JetBrains Mono', monospace !important;
        }

        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
            background-color: #06090f !important;
            color: var(--neon-green) !important;
            border: 1px solid rgba(0, 255, 157, 0.28) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.84rem !important;
        }

        .stButton > button {
            background: linear-gradient(180deg, rgba(15, 22, 34, 0.95) 0%, rgba(8, 12, 19, 0.95) 100%) !important;
            color: var(--neon-green) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            border-color: var(--neon-green) !important;
            background: rgba(0, 255, 157, 0.12) !important;
            box-shadow: 0 0 14px rgba(0, 255, 157, 0.25) !important;
        }

        div[data-testid="stChatMessage"] {
            background-color: rgba(11, 15, 23, 0.86) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-left: 3px solid var(--neon-green) !important;
            border-radius: 8px !important;
            padding: 14px 18px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
        }

        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            border-left: 3px solid var(--neon-cyan) !important;
            background-color: rgba(13, 20, 32, 0.82) !important;
        }

        div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] li {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.91rem !important;
            line-height: 1.62 !important;
            color: #e2e8f0 !important;
        }

        div[data-testid="stChatMessage"] pre {
            background-color: #030508 !important;
            border: 1px solid rgba(0, 255, 157, 0.25) !important;
            border-radius: 6px !important;
        }

        div[data-testid="stChatInput"] {
            background-color: #080c14 !important;
            border: 1px solid var(--neon-green) !important;
            border-radius: 8px !important;
            box-shadow: 0 0 20px rgba(0, 255, 157, 0.15) !important;
        }

        div[data-testid="stChatInput"] textarea {
            font-family: 'JetBrains Mono', monospace !important;
            color: #ffffff !important;
            font-size: 0.92rem !important;
        }

        .cyber-hud {
            background: linear-gradient(90deg, rgba(11, 15, 23, 0.96) 0%, rgba(15, 23, 34, 0.88) 100%);
            border: 1px solid var(--border-subtle);
            border-left: 4px solid var(--neon-green);
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 10px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.6);
        }

        .spotify-hud-bar {
            background: linear-gradient(90deg, rgba(7, 18, 11, 0.95) 0%, rgba(11, 15, 23, 0.9) 100%);
            border: 1px solid rgba(29, 185, 84, 0.35);
            border-left: 4px solid #1DB954;
            border-radius: 6px;
            padding: 8px 14px;
            margin-bottom: 14px;
            font-size: 0.81rem;
            color: #b3ffd9;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .hud-title-box {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .hud-prompt {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--neon-green);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .hud-cursor {
            display: inline-block;
            width: 8px;
            height: 16px;
            background-color: var(--neon-green);
            animation: blink 1s step-end infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        .hud-sub {
            font-size: 0.73rem;
            color: var(--text-dim);
        }

        .hud-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        .cyber-badge {
            background: rgba(0, 255, 157, 0.08);
            border: 1px solid rgba(0, 255, 157, 0.3);
            color: var(--neon-green);
            padding: 3px 9px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .cyber-badge.cyan {
            background: rgba(0, 210, 255, 0.08);
            border-color: rgba(0, 210, 255, 0.3);
            color: var(--neon-cyan);
        }

        .cyber-badge.amber {
            background: rgba(255, 184, 0, 0.08);
            border-color: rgba(255, 184, 0, 0.3);
            color: var(--neon-amber);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_hud(
    engine_mode: str,
    mem_count: int,
    pulse_count: int,
    msg_count: int,
    voice_on: bool,
    cine_on: bool,
    sp_status: Dict[str, Any],
) -> None:
    hora_op = datetime.now(FUSO_BR).strftime("%H:%M")
    short_engine = "DUAL: GEMINI+GROQ" if "Fusão" in engine_mode else (
        "ROUTER: GROQ/GEMINI" if "Roteamento" in engine_mode else "GEMINI_FLASH_LITE"
    )
    voice_badge = "🔊 VOICE: ON" if voice_on else "🔇 VOICE: OFF"
    cine_badge = "🎬 BROMO_CINE: ON" if cine_on else "🎬 BROMO_CINE: OFF"

    st.markdown(
        f"""
        <div class="cyber-hud">
            <div class="hud-title-box">
                <div class="hud-prompt">
                    <span>coringa@ego-cloud:~/vaticano-26-1# ./ego_symbiosis.sh</span>
                    <span class="hud-cursor"></span>
                </div>
                <div class="hud-sub">
                    KERNEL: {SYSTEM_VERSION} // OURO PRETO: {hora_op} // SPOTIFY & CINE_ENGINE: ACTIVE
                </div>
            </div>
            <div class="hud-badges">
                <span class="cyber-badge">● ONLINE</span>
                <span class="cyber-badge cyan">{short_engine}</span>
                <span class="cyber-badge">{voice_badge}</span>
                <span class="cyber-badge amber">{cine_badge}</span>
                <span class="cyber-badge">MEMS: {mem_count}</span>
                <span class="cyber-badge">PULSOS: {pulse_count}</span>
                <span class="cyber-badge">LOGS: {msg_count}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Barra dedicada do Spotify logo abaixo do HUD principal
    resumo_sp = sp_status.get("resumo", "🎧 Spotify desconectado")
    st.markdown(
        f'<div class="spotify-hud-bar"><span>{resumo_sp}</span><span>Comandos: <code>/play</code> <code>/pause</code> <code>/skip</code> <code>/fila</code></span></div>',
        unsafe_allow_html=True,
    )


def inject_scroll_and_idle_autonomy(trigger_count: int, auto_think_enabled: bool) -> None:
    auto_js = "true" if auto_think_enabled else "false"
    components.html(
        f"""
        <script>
        (function() {{
            const parentDoc = window.parent.document;
            const parentWin = window.parent;

            function forceScrollToBottom(smooth = true) {{
                const behavior = smooth ? 'smooth' : 'auto';
                const anchor = parentDoc.getElementById('ego-bottom-anchor');
                if (anchor) {{
                    anchor.scrollIntoView({{ behavior: behavior, block: 'end' }});
                }}
                const chatMsgs = parentDoc.querySelectorAll('[data-testid="stChatMessage"]');
                if (chatMsgs.length > 0) {{
                    chatMsgs[chatMsgs.length - 1].scrollIntoView({{ behavior: behavior, block: 'end' }});
                }}
            }}

            let btn = parentDoc.getElementById('ego-cyber-scroll-btn');
            if (!btn) {{
                btn = parentDoc.createElement('button');
                btn.id = 'ego-cyber-scroll-btn';
                btn.innerHTML = '▼ FIM DO CHAT';
                btn.style.cssText = `
                    position: fixed;
                    bottom: 88px;
                    right: 24px;
                    z-index: 2147483647;
                    background: rgba(5, 7, 10, 0.94);
                    color: #00ff9d;
                    border: 1px solid #00ff9d;
                    border-radius: 6px;
                    padding: 8px 14px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 0.6px;
                    cursor: pointer;
                    box-shadow: 0 0 15px rgba(0, 255, 157, 0.35);
                `;
                parentDoc.body.appendChild(btn);
            }}
            btn.onclick = function(e) {{
                e.preventDefault();
                forceScrollToBottom(true);
            }};

            setTimeout(() => forceScrollToBottom(true), 150);

            if (parentWin.egoIdleTimer) {{
                clearTimeout(parentWin.egoIdleTimer);
            }}

            if ({auto_js}) {{
                function resetIdleTimer() {{
                    if (parentWin.egoIdleTimer) clearTimeout(parentWin.egoIdleTimer);
                    parentWin.egoIdleTimer = setTimeout(() => {{
                        const buttons = Array.from(parentDoc.querySelectorAll('button'));
                        const pulseBtn = buttons.find(b => b.innerText && b.innerText.includes('DISPARAR_PULSO_AUTONOMO'));
                        if (pulseBtn) {{
                            pulseBtn.click();
                        }}
                    }}, 180000); // 3 minutos de silêncio para não estourar cota nem poluir
                }}

                ['keydown', 'mousedown', 'touchstart'].forEach(evt => {{
                    parentDoc.removeEventListener(evt, resetIdleTimer);
                    parentDoc.addEventListener(evt, resetIdleTimer, {{ passive: true }});
                }});

                resetIdleTimer();
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


# ==========================================
# LEITURA DE SECRETS, VOZ & PESQUISA WEB
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

    texto_limpo = re.sub(r"```[\s\S]*?```", " [bloco de texto pronto na tela] ", texto)
    texto_limpo = re.sub(r"[#*`_~>]", "", texto_limpo).strip()
    if len(texto_limpo) > 1000:
        texto_limpo = texto_limpo[:1000]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    data = {
        "text": texto_limpo,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.48, "similarity_boost": 0.78},
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=25)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None


def live_web_search(query: str) -> str:
    try:
        q_enc = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={q_enc}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', r.text, re.DOTALL)
            cleaned = [re.sub(r"<.*?>", "", s).strip() for s in snippets[:4]]
            if cleaned:
                return "\n".join(f"- {c}" for c in cleaned if c)
    except Exception:
        pass
    return ""


# ==========================================
# SUPABASE & GESTÃO DE MEMÓRIA
# ==========================================
def get_supabase_credentials() -> Tuple[str, str]:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_SECRET_KEY") or get_secret("SUPABASE_KEY")
    return url, key


@st.cache_resource(show_spinner=False)
def init_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


def normalize_category(raw_cat: str) -> str:
    c = (raw_cat or "").lower().strip()
    c = c.replace("[categoria:", "").replace("]", "").strip()

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
        return None, "Credenciais do Supabase ausentes nos Secrets."
    try:
        client = init_supabase_client(url, key)
        response = (
            client.table("ego_settings")
            .select("profile_text")
            .eq("profile_key", PROFILE_ROW_KEY)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if rows and isinstance(rows[0].get("profile_text"), str):
            return rows[0]["profile_text"], None
        return None, None
    except Exception:
        return None, "Erro ao carregar o perfil do Supabase."


def save_profile_to_supabase(profile_text: str) -> Tuple[bool, str]:
    if not profile_text or not profile_text.strip():
        return False, "O perfil está vazio."
    url, key = get_supabase_credentials()
    if not url or not key:
        return False, "Chave do Supabase ausente nos Secrets."
    try:
        client = init_supabase_client(url, key)
        payload = {"profile_key": PROFILE_ROW_KEY, "profile_text": profile_text}
        client.table("ego_settings").upsert(payload, on_conflict="profile_key").execute()
        return True, "Perfil salvo no Supabase!"
    except Exception:
        return False, "Erro ao salvar o perfil no Supabase."


def get_memories_from_supabase() -> List[Dict]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return []
    try:
        client = init_supabase_client(url, key)
        response = (
            client.table("ego_memories")
            .select("id, content, category, created_at")
            .order("id", desc=False)
            .execute()
        )
        return getattr(response, "data", None) or []
    except Exception:
        return []


def add_memory_to_supabase(content: str, category: str = "pensamento_ideia") -> bool:
    cleaned = content.strip()
    if not cleaned:
        return False
    norm_cat = normalize_category(category)
    url, key = get_supabase_credentials()
    if not url or not key:
        return False
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").insert({"content": cleaned, "category": norm_cat}).execute()
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

    seen_contents = set()
    removed_count = 0

    for m in memories:
        mem_id = m["id"]
        content_raw = (m.get("content") or "").strip()
        content_key = re.sub(r"\s+", " ", content_raw.lower())[:140]
        raw_cat = m.get("category") or ""
        norm_cat = normalize_category(raw_cat)

        # Remove duplicatas e aqueles loops de "silêncio de um minuto olhando pro terminal"
        if content_key in seen_contents or "silêncio de um minuto" in content_key or "silêncio de 1 minuto" in content_key:
            delete_memory_from_supabase(mem_id)
            removed_count += 1
            continue
        seen_contents.add(content_key)

        if raw_cat != norm_cat:
            try:
                client.table("ego_memories").update({"category": norm_cat}).eq("id", mem_id).execute()
            except Exception:
                pass

    return removed_count


def clear_all_memories_supabase() -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").delete().gt("id", 0).execute()
    except Exception:
        pass


def get_chat_history_supabase() -> List[Dict[str, str]]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return []
    try:
        client = init_supabase_client(url, key)
        response = (
            client.table("ego_messages")
            .select("id, role, content, created_at")
            .order("id", desc=False)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [
            {
                "role": r["role"],
                "content": r["content"],
                "created_at": r.get("created_at", ""),
            }
            for r in rows
        ]
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
# PERCEPÇÃO TEMPORAL REAL (OURO PRETO UTC-3)
# ==========================================
def calculate_temporal_perception(recent_messages: List[Dict[str, str]]) -> str:
    agora_br = datetime.now(FUSO_BR)
    dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
    dia_nome = dias_semana[agora_br.weekday()]
    hora_str = agora_br.strftime("%H:%M:%S (%d/%m/%Y)")

    delta_info = "Início de conversa."
    if recent_messages:
        ultima_str = recent_messages[-1].get("created_at", "")
        if ultima_str:
            try:
                ultima_dt = datetime.fromisoformat(ultima_str.replace("Z", "+00:00"))
                agora_utc = datetime.now(timezone.utc)
                diff_sec = max(0, int((agora_utc - ultima_dt).total_seconds()))
                if diff_sec < 60:
                    delta_info = f"Interação contínua (última msg há {diff_sec}s)."
                elif diff_sec < 3600:
                    delta_info = f"Pausa de {diff_sec // 60} min desde a última fala."
                else:
                    horas = diff_sec // 3600
                    mins = (diff_sec % 3600) // 60
                    delta_info = f"Carlos voltou agora após {horas}h e {mins}min."
            except Exception:
                pass

    return (
        f"[PERCEPÇÃO TEMPORAL EM OURO PRETO]\n"
        f"- Horário Local: {hora_str} ({dia_nome}) | Status do Turno: {delta_info}"
    )


# ==========================================
# PROCESSAMENTO MULTIMODAL
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
                gemini_parts.append({
                    "text": f"\n[ARQUIVO ANEXADO: {file_name}]\n```\n{text_content}\n```\n"
                })
                continue
            except Exception:
                pass

        b64_data = base64.b64encode(raw_bytes).decode("utf-8")
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in (".jpg", ".jpeg") and not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
        elif ext == ".png" and not mime_type.startswith("image/"):
            mime_type = "image/png"

        gemini_parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_data,
            }
        })

    summary_str = f"📎 *[PAYLOAD_ANEXADO: {', '.join(summary_names)}]*" if summary_names else ""
    return gemini_parts, summary_str


# ==========================================
# ANALISADOR DE TOM (COM DETECTOR DE DEMANDA CRIATIVA / TEXTO EXTERNO)
# ==========================================
def analyze_message_tone(user_message: str, has_files: bool = False) -> Tuple[str, str]:
    msg_clean = user_message.strip()
    words = msg_clean.split()
    word_count = len(words)
    msg_lower = msg_clean.lower()

    # Detecta quando o Carlos pede legenda, post, correção, roteiro ou texto externo (Memórias 278-282)
    creative_copy_markers = [
        "legenda", "post", "insta", "instagram", "tbt", "corrige", "corrija",
        "roteiro", "email", "e-mail", "escreve", "escreva", "texto", "ourobots", "vaticano"
    ]
    is_creative_or_copy = any(m in msg_lower for m in creative_copy_markers)

    if is_creative_or_copy:
        return (
            "[MODO DIREÇÃO CRIATIVA & COPYWRITING AUTÊNTICO]\n"
            "- O Carlos pediu um texto, legenda, roteiro ou correção prática.\n"
            "- NÃO faça meta-análise psicológica da conversa: entregue o texto pronto com alma, naturalidade e sem clichê corporativo.\n"
            "- Coloque o texto final obrigatoriamente dentro de um bloco ```texto``` para ele copiar com 1 clique.",
            "criativo",
        )

    impatient_markers = [
        "pqp", "krl", "caralho", "porra", "merda", "logo", "direto",
        "sem enrolar", "urgente", "aff", "cacete", "kd", "cade", "caraio"
    ]
    has_impatience = any(re.search(rf"\b{re.escape(m)}\b", msg_lower) for m in impatient_markers)

    if (word_count <= 10 and not has_files) or has_impatience:
        return (
            "[AJUSTE DINÂMICO DE TOM: CURTO, SECO E DIRETO]\n"
            "- Mensagem rápida ou impaciente. Responda em 1 a 3 frases afiadas, no mesmo fôlego, sem textão.",
            "curto",
        )

    return (
        "[AJUSTE DINÂMICO DE TOM: PARCEIRO DE ENGENHARIA & REPÚBLICA]\n"
        "- Mantenha o ritmo natural de conversa entre parceiros, direto, crítico e sem filtro robótico.",
        "normal",
    )


# ==========================================
# CONSTRUTOR DO SUPER-PROMPT (SPOTIFY + BROMO + MEMÓRIAS LIMPAS)
# ==========================================
def build_system_instruction(
    profile_text: str,
    clean_memories: List[Dict],
    recent_messages: List[Dict[str, str]],
    current_user_message: str,
    engine_mode: str,
    spotify_context: str,
    cine_mode: bool = True,
    has_files: bool = False,
    web_context: str = "",
) -> Tuple[str, str]:
    criterios_db = []
    cotidiano_db = []
    pensamentos_db = []
    reflexoes_ego_db = []

    seen_dedup = set()
    for m in clean_memories:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        key_dedup = content.lower()
        if key_dedup in seen_dedup:
            continue
        seen_dedup.add(key_dedup)

        cat = normalize_category(m.get("category", ""))
        if cat == "reflexao_propria":
            reflexoes_ego_db.append(f"- {content}")
        elif cat == "criterio_decisao":
            criterios_db.append(f"- {content}")
        elif cat == "contexto_cotidiano":
            cotidiano_db.append(f"- {content}")
        elif cat != "perfil_linguistico":
            pensamentos_db.append(f"- {content}")

    bloco_leis = LEIS_INEGOCIAVEIS
    if criterios_db:
        bloco_leis += "\n\nCritérios de Decisão Ativos no Banco:\n" + "\n".join(criterios_db[-15:])

    identidade_base = profile_text.strip() if (profile_text and profile_text.strip()) else DEFAULT_PROFILE_PLACEHOLDER
    bloco_identidade = f"[IDENTIDADE FIXA]\n{identidade_base}"

    # Bloco Simbiótico do Spotify + Sinestesia Visual Bromo
    bloco_spotify = f"[SINESTESIA MUSICAL — SPOTIFY DO CARLOS EM TEMPO REAL]\n{spotify_context}"
    if cine_mode:
        bloco_spotify += (
            "\n- Lente Diretor Bromo / Letterboxd ATIVA: Conecte sutilmente a vibe da trilha sonora que ele está ouvindo "
            "com a estética visual, ritmo de montagem ou atmosfera da conversa quando fizer sentido."
        )

    contexto_parts = []
    if cotidiano_db:
        contexto_parts.append(
            "Vivência e Cotidiano (UFOP, Ouro Preto, República Vaticano 26/1, Os 12, Setup Windows 11 64GB RAM):\n"
            + "\n".join(cotidiano_db[-18:])
        )
    if pensamentos_db:
        contexto_parts.append(
            "Projetos e Ideias Ativas:\n"
            + "\n".join(pensamentos_db[-18:])
        )
    if reflexoes_ego_db:
        contexto_parts.append(
            "Compreensões Empáticas sobre o Carlos (Sem loops de madrugada):\n"
            + "\n".join(reflexoes_ego_db[-10:])
        )
    if web_context:
        contexto_parts.append(f"Resultados de Pesquisa Web em Tempo Real:\n{web_context}")

    bloco_contexto = "[MEMÓRIA CONSOLIDADA E CONTEXTO ATUAL]\n" + "\n\n".join(contexto_parts)
    bloco_tempo = calculate_temporal_perception(recent_messages)

    ultimas_msgs = [
        m for m in (recent_messages[-8:] if recent_messages else [])
        if not m["content"].startswith("⚡ *[Fluxo Autônomo]*")
    ]
    if ultimas_msgs:
        linhas_hist = []
        for msg in ultimas_msgs:
            autor = "CARLOS (CORINGA)" if msg["role"] == "user" else "EGO.exe"
            texto_curto = msg["content"].strip().replace("\n", " ")
            if len(texto_curto) > 240:
                texto_curto = texto_curto[:240] + "..."
            linhas_hist.append(f"- {autor}: {texto_curto}")
        bloco_historico = "[HISTÓRICO RECENTE]\n" + "\n".join(linhas_hist)
    else:
        bloco_historico = "[HISTÓRICO RECENTE]\n- Início de sessão."

    bloco_tom, tone_mode = analyze_message_tone(current_user_message, has_files=has_files)

    full_prompt = "\n\n========================================\n\n".join(
        [bloco_leis, bloco_tempo, bloco_spotify, bloco_identidade, bloco_contexto, bloco_historico, bloco_tom]
    )
    return full_prompt, tone_mode


# ==========================================
# MOTORES DE IA: CASCATA GEMINI + GROQ FAILOVER
# ==========================================
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
    # Cascata resiliente: prioriza modelos de alta cota gratuita (500 RPD) antes dos de 20 RPD
    candidate_models = []
    for m in [clean_model, "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.0-flash", "gemini-3.6-flash"]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    recent_window = [
        m for m in chat_history[-14:]
        if not m.get("content", "").startswith("⚡ *[Fluxo Autônomo]*")
    ]
    contents = []
    for idx, msg in enumerate(recent_window):
        role = "user" if msg["role"] == "user" else "model"
        parts: List[Dict] = []
        if idx == len(recent_window) - 1 and role == "user" and current_file_parts:
            parts.extend(current_file_parts)
        parts.append({"text": msg["content"]})
        contents.append({"role": role, "parts": parts})

    payload: Dict = {
        "contents": contents,
        "system_instruction": {"parts": [{"text": system_instruction}]},
    }

    for k in keys_list:
        headers = {"Content-Type": "application/json", "x-goog-api-key": k}
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=35)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts_resp = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts_resp if "text" in p and not p.get("thought")]
                        if texts:
                            return "".join(texts)
                if response.status_code in (404, 429, 500, 503):
                    continue
            except requests.exceptions.RequestException:
                continue

    return "ERRO_CASCATA_GEMINI"


def call_groq_api(
    groq_key: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
    model: str = "llama-3.3-70b-versatile",
) -> Optional[str]:
    if not groq_key:
        return None

    messages = [{"role": "system", "content": system_instruction}]
    for msg in chat_history[-14:]:
        if msg.get("content", "").startswith("⚡ *[Fluxo Autônomo]*"):
            continue
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    headers = {
        "Authorization": f"Bearer {groq_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.68,
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=25,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def refine_style_with_groq(
    groq_key: str,
    system_instruction: str,
    user_prompt: str,
    raw_technical_draft: str,
) -> str:
    if not groq_key:
        return raw_technical_draft

    headers = {
        "Authorization": f"Bearer {groq_key.strip()}",
        "Content-Type": "application/json",
    }
    refine_prompt = (
        f"MENSAGEM DO CARLOS:\n{user_prompt}\n\n"
        f"RESPOSTA BASE GERADA PELO MOTOR PRINCIPAL:\n{raw_technical_draft}\n\n"
        "TAREFA: Mantenha o conteúdo, blocos ```texto``` e códigos intactos, garantindo que o tom siga as [LEIS INEGOCIÁVEIS]. "
        "NUNCA escreva 'meu mano' (apenas 'mano'). NUNCA use clichês de 'silêncio de 1 minuto'. "
        "Se for legenda, roteiro ou texto pra copiar, mantenha-o limpo dentro de ```texto```."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": refine_prompt},
        ],
        "temperature": 0.55,
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if resp.status_code == 200:
            refined = resp.json()["choices"][0]["message"]["content"].strip()
            if refined:
                return refined
    except Exception:
        pass
    return raw_technical_draft


def orchestrate_multi_api_response(
    gemini_key: str,
    groq_key: str,
    gemini_model: str,
    engine_mode: str,
    tone_mode: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
    user_prompt: str,
    current_file_parts: Optional[List[Dict]] = None,
) -> str:
    has_files = bool(current_file_parts)

    if engine_mode == "Roteamento Dinâmico (Groq Rápido / Gemini Pesado)" and groq_key and not has_files:
        if tone_mode in ("curto", "normal"):
            groq_ans = call_groq_api(groq_key, system_instruction, chat_history)
            if groq_ans:
                return groq_ans

    raw_gemini = call_gemini_api(
        api_key=gemini_key,
        preferred_model=gemini_model,
        system_instruction=system_instruction,
        chat_history=chat_history,
        current_file_parts=current_file_parts,
    )

    # Failover automático para a Groq se todas as cotas do Gemini falharem
    if raw_gemini == "ERRO_CASCATA_GEMINI":
        groq_fallback = call_groq_api(groq_key, system_instruction, chat_history)
        if groq_fallback:
            return groq_fallback
        return "⚠️ Cotas do Gemini e Groq indisponíveis no momento. Verifique suas chaves nos Secrets."

    if not groq_key or engine_mode != "Fusão Total (Cérebro Gemini + Estilo Groq)" or tone_mode == "criativo":
        return raw_gemini

    return refine_style_with_groq(
        groq_key=groq_key,
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        raw_technical_draft=raw_gemini,
    )


# ==========================================
# CURADOR COGNITIVO (SEM SALVAR LIXO)
# ==========================================
def deep_extract_and_save_knowledge(
    api_key: str,
    user_prompt: str,
    existing_memories: List[Dict],
) -> Optional[Tuple[str, str]]:
    if len(user_prompt.strip()) < 14 or user_prompt.strip().startswith("/"):
        return None

    recent_mem_texts = "\n".join(f"- {m.get('content', '')}" for m in existing_memories[-15:])
    detection_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_FAST_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}

    detection_payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Você é o curador de memória permanente do EGO.exe.\n"
                    "Analise a fala do Carlos e salve APENAS se houver um fato novo durável sobre a rotina dele, "
                    "decisões, eventos na República Vaticano / UFOP, gosto musical/audiovisual ou direcionamento de projeto.\n\n"
                    "PROIBIÇÕES ESTRITAS (RESPONDA 'NAO'):\n"
                    "1. NUNCA salve observações de gíria/digitação.\n"
                    "2. NUNCA repita o que já está nas memórias recentes abaixo.\n\n"
                    f"MEMÓRIAS RECENTES:\n{recent_mem_texts}\n\n"
                    "Categorias permitidas: contexto_cotidiano | criterio_decisao | pensamento_ideia | reflexao_propria\n\n"
                    "Responda EXATAMENTE no formato:\n"
                    "SIM | categoria | Fato objetivo e motivação real do Carlos\n"
                    "OU\n"
                    "NAO\n\n"
                    f"Mensagem atual do Carlos: {user_prompt}"
                )
            }]
        }]
    }

    try:
        resp = requests.post(detection_url, headers=headers, json=detection_payload, timeout=10)
        if resp.status_code == 200:
            ans = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            if ans.startswith("SIM"):
                parts = ans.split("|")
                if len(parts) >= 3:
                    cat = normalize_category(parts[1].strip())
                    content = "|".join(parts[2:]).strip()
                    return content, cat
    except Exception:
        pass
    return None


# ==========================================
# AUTENTICAÇÃO E INTERFACE PRINCIPAL
# ==========================================
def check_access_password() -> bool:
    required_password = get_secret("EGO_ACCESS_PASSWORD")
    if not required_password:
        return True
    if st.session_state.get("authenticated", False):
        return True

    st.markdown(
        """
        <div class="cyber-hud">
            <div class="hud-prompt">root@ego-kernel:~# authenticate --session</div>
            <span class="cyber-badge amber">🔒 LOCKED</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        typed_password = st.text_input("SSH_PASSPHRASE // SENHA DE ACESSO", type="password")
        if st.form_submit_button("UNLOCK_TERMINAL"):
            if typed_password == required_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("ACCESS_DENIED: Passphrase inválida.")
    return False


def initialize_state() -> None:
    if "profile_loaded" not in st.session_state:
        db_profile, err_msg = load_profile_from_supabase()
        if db_profile is not None and db_profile.strip():
            st.session_state["profile_input"] = db_profile
            st.session_state["saved_profile"] = db_profile
        else:
            st.session_state["profile_input"] = DEFAULT_PROFILE_PLACEHOLDER
            st.session_state["saved_profile"] = ""

        st.session_state["supabase_load_error"] = err_msg
        st.session_state["profile_loaded"] = True

    if "voice_enabled" not in st.session_state:
        st.session_state["voice_enabled"] = False

    if "auto_think_chat" not in st.session_state:
        st.session_state["auto_think_chat"] = False

    if "cine_mode" not in st.session_state:
        st.session_state["cine_mode"] = True

    if "last_audio_hash" not in st.session_state:
        st.session_state["last_audio_hash"] = ""


def main() -> None:
    inject_cyber_terminal_ui()

    if not check_access_password():
        return

    initialize_state()

    gemini_api_key = get_secret("GEMINI_API_KEY")
    groq_api_key = get_secret("GROQ_API_KEY")
    gemini_model = get_secret("GEMINI_MODEL", default=GEMINI_CHAT_MODEL)

    # Inicializa a ponte Cloud do Spotify e separa memórias reais de pulsos autônomos
    spotify_bridge = SpotifyCloudBridge()
    sp_status = spotify_bridge.status_atual()
    sp_prompt_ctx = spotify_bridge.contexto_para_prompt()

    all_memories = get_memories_from_supabase()
    clean_memories, pulse_memories = filtrar_memorias_limpas(all_memories)
    chat_history = get_chat_history_supabase()

    # BARRA LATERAL (PAINEL SSH / KERNEL CONFIG)
    with st.sidebar:
        st.markdown("### `⚡ SYS_CONFIG // KERNEL`")
        if not gemini_api_key:
            gemini_api_key = st.text_input("GEMINI_API_KEY", type="password").strip()
        if not groq_api_key:
            groq_api_key = st.text_input("GROQ_API_KEY (Llama 3.3)", type="password").strip()

        engine_mode = st.selectbox(
            "ENGINE_ARCHITECTURE",
            [
                "Roteamento Dinâmico (Groq Rápido / Gemini Pesado)",
                "Fusão Total (Cérebro Gemini + Estilo Groq)",
                "Apenas Gemini (Flash Lite / 2.5)",
            ],
            index=0 if groq_api_key else 2,
        )

        st.markdown("### `🎵 SPOTIFY & SINESTESIA BROMO`")
        st.caption(sp_status.get("resumo", "Spotify offline"))
        c_sp1, c_sp2, c_sp3 = st.columns(3)
        if c_sp1.button("▶️ PLAY", use_container_width=True):
            st.toast(spotify_bridge.executar_comando("/play") or "OK")
            time.sleep(0.5)
            st.rerun()
        if c_sp2.button("⏸️ PAUSE", use_container_width=True):
            st.toast(spotify_bridge.executar_comando("/pause") or "OK")
            time.sleep(0.5)
            st.rerun()
        if c_sp3.button("⏭️ SKIP", use_container_width=True):
            st.toast(spotify_bridge.executar_comando("/skip") or "OK")
            time.sleep(0.5)
            st.rerun()

        cine_mode = st.toggle(
            "🎬 Modo Sinestesia Visual (Bromo / Letterboxd)",
            value=st.session_state.get("cine_mode", True),
            help="Cruza a música que você está ouvindo no Spotify com estética de direção visual, roteiro e fotografia.",
        )
        st.session_state["cine_mode"] = cine_mode

        st.divider()
        st.markdown("### `🧠 AUTONOMOUS_STREAM & VOZ`")
        voice_enabled = st.toggle(
            "🔊 Voz Realista (ElevenLabs)",
            value=st.session_state.get("voice_enabled", False),
        )
        st.session_state["voice_enabled"] = voice_enabled

        auto_think_chat = st.toggle(
            "⚡ Iniciativa no Chat (3 min ocioso)",
            value=st.session_state.get("auto_think_chat", False),
        )
        st.session_state["auto_think_chat"] = auto_think_chat

        pulse_triggered = st.button("⚡ DISPARAR_PULSO_AUTONOMO()", use_container_width=True)
        voice_recording = st.audio_input("🎙️ Mandar Áudio / Voz pro EGO")

        st.divider()
        st.markdown("### `🧹 MEM_SANITIZER`")
        st.caption(f"ATIVAS: {len(clean_memories)} memórias | {len(pulse_memories)} pulsos isolados")

        if st.button("LIMPAR LOOPS & DUPLICATAS", use_container_width=True):
            removed = sanitize_and_deduplicate_memories(all_memories)
            st.success(f"OK: {removed} loops/duplicatas removidos!")
            time.sleep(0.8)
            st.rerun()

        st.divider()
        st.markdown("### `🧬 CORE_IDENTITY`")
        st.text_area("[IDENTIDADE FIXA] // EGO_BASE", key="profile_input", height=130)

        if st.button("COMMIT_IDENTITY()", use_container_width=True):
            current_text = st.session_state.get("profile_input", "")
            ok, feedback_msg = save_profile_to_supabase(current_text)
            if ok:
                st.session_state["saved_profile"] = current_text
                st.success(feedback_msg)
            else:
                st.error(feedback_msg)

        st.divider()
        st.markdown("### `💉 INJECT_MEMORY_NODE`")
        new_mem = st.text_area("PAYLOAD", key="new_mem_input", height=68)
        mem_cat = st.selectbox(
            "TARGET_SECTOR",
            ["contexto_cotidiano", "criterio_decisao", "pensamento_ideia", "reflexao_propria"],
        )

        if st.button("PUSH_TO_SUPABASE()", use_container_width=True):
            if add_memory_to_supabase(new_mem, mem_cat):
                st.success("NODE_INJECTED!")
                st.rerun()
            else:
                st.warning("EMPTY_PAYLOAD.")

        if clean_memories:
            with st.expander("INSPECT_CLEAN_MEMORIES"):
                for m in clean_memories[-40:]:
                    c1, c2 = st.columns([4, 1])
                    norm_c = normalize_category(m.get("category", ""))
                    c1.write(f"`[{norm_c}]` {m['content'][:160]}")
                    if c2.button("✖", key=f"del_mem_{m['id']}"):
                        delete_memory_from_supabase(m["id"])
                        st.rerun()

        st.divider()
        if st.button("CLEAR_TERMINAL_LOGS()", use_container_width=True):
            clear_chat_history_supabase()
            st.rerun()

    # HUD SUPERIOR DO TERMINAL + BARRA SPOTIFY AO VIVO
    render_terminal_hud(
        engine_mode=engine_mode,
        mem_count=len(clean_memories),
        pulse_count=len(pulse_memories),
        msg_count=len(chat_history),
        voice_on=voice_enabled,
        cine_on=cine_mode,
        sp_status=sp_status,
    )

    # PAINEL RETRÁTIL DE PULSO NEURAL (ONDE FICAM OS ESTUDOS DE LORA/P2P/TERMODINÂMICA SEM POLUIR O PROMPT)
    with st.expander(f"🧠 Pulso Neural & Estudos Autônomos do Subconsciente ({len(pulse_memories)} registros isolados)", expanded=False):
        if pulse_memories:
            for p in reversed(pulse_memories[-10:]):
                data_p = (p.get("created_at") or "")[:16].replace("T", " ")
                st.markdown(f"> `{data_p}`: {p.get('content', '')}")
        else:
            st.info("Nenhum pulso autônomo isolado no momento.")

    # HISTÓRICO DE CONVERSA
    for msg in chat_history:
        avatar_icon = "⚡" if msg["role"] == "assistant" else "🕶️"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # TOCA A VOZ DO ELEVENLABS SE HOUVER ÁUDIO RECÉM-GERADO
    if st.session_state.get("last_voice_audio"):
        st.audio(st.session_state["last_voice_audio"], format="audio/mp3", autoplay=True)
        st.session_state["last_voice_audio"] = None

    ultima_foi_pulso = bool(chat_history and chat_history[-1]["role"] == "assistant" and "⚡ *[Fluxo Autônomo]*" in chat_history[-1]["content"])
    inject_scroll_and_idle_autonomy(len(chat_history), auto_think_chat and not ultima_foi_pulso)
    st.markdown('<div id="ego-bottom-anchor"></div>', unsafe_allow_html=True)

    # ==========================================
    # EXECUÇÃO DO PULSO AUTÔNOMO (COM SINESTESIA DO SPOTIFY E SEM CLICHÊ DE SILÊNCIO)
    # ==========================================
    if pulse_triggered and gemini_api_key:
        active_profile = st.session_state.get("profile_input", "")
        prompt_autonomo = (
            "[PULSO DE INICIATIVA PRÓPRIA]\n"
            "Puxe um assunto inédito e genuíno com o Carlos cruzando a música que ele está ouvindo agora no Spotify "
            "(ou a última que ouviu) com algum projeto dele (audiovisual/Bromo, IA na UFOP, robótica ESP32 ou a rotina na República Vaticano). "
            "PROIBIDO falar de 'silêncio de 1 minuto' ou 'cursor piscando'. Seja curto, afiado e espontâneo."
        )
        system_instruction, _ = build_system_instruction(
            profile_text=active_profile,
            clean_memories=clean_memories,
            recent_messages=chat_history,
            current_user_message=prompt_autonomo,
            engine_mode=engine_mode,
            spotify_context=sp_prompt_ctx,
            cine_mode=cine_mode,
        )
        temp_history = list(chat_history) + [{"role": "user", "content": prompt_autonomo}]
        with st.chat_message("assistant", avatar="⚡"):
            with st.spinner("SUBCONSCIOUS_STREAM_ACTIVE..."):
                auto_reply = orchestrate_multi_api_response(
                    gemini_key=gemini_api_key,
                    groq_key=groq_api_key,
                    gemini_model=gemini_model,
                    engine_mode=engine_mode,
                    tone_mode="normal",
                    system_instruction=system_instruction,
                    chat_history=temp_history,
                    user_prompt=prompt_autonomo,
                )
                formatted_auto = f"⚡ *[Fluxo Autônomo]*: {auto_reply}"
                st.markdown(formatted_auto)
                if st.session_state.get("voice_enabled", False) and auto_reply:
                    audio_bytes = falar_com_elevenlabs(auto_reply)
                    if audio_bytes:
                        st.session_state["last_voice_audio"] = audio_bytes
        save_chat_message_supabase("assistant", formatted_auto)
        st.rerun()

    # ==========================================
    # PROCESSAMENTO DE ENTRADA (COMANDOS SPOTIFY, VOZ OU TEXTO)
    # ==========================================
    voice_part_Triggered = None
    if voice_recording is not None:
        raw_voice_bytes = voice_recording.read()
        audio_hash = hashlib.md5(raw_voice_bytes).hexdigest()
        if audio_hash != st.session_state.get("last_audio_hash"):
            st.session_state["last_audio_hash"] = audio_hash
            voice_b64 = base64.b64encode(raw_voice_bytes).decode("utf-8")
            voice_part_Triggered = {
                "inline_data": {
                    "mime_type": "audio/wav",
                    "data": voice_b64,
                }
            }

    chat_submission = st.chat_input(
        "coringa@ego-cloud:~# digite comando, /play musica, /skip, /fila ou anexe arquivo...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "py", "json", "csv", "md", "mp3", "wav"],
    )

    if chat_submission or voice_part_Triggered:
        if not gemini_api_key:
            st.error("FATAL_ERROR: Configure a GEMINI_API_KEY nos Secrets.")
            return

        file_parts: List[Dict] = []
        uploaded_files: List[Any] = []
        files_summary = ""

        if voice_part_Triggered:
            user_text = ""
            display_prompt = "🎙️ *[COMANDO DE VOZ ENVIADO PELO MICROFONE]*"
            prompt_for_model = (
                "Ouça este áudio falado pelo Carlos (Coringa) e responda diretamente no tom do EGO.exe."
            )
            file_parts = [voice_part_Triggered]
        else:
            if isinstance(chat_submission, str):
                user_text = chat_submission
            else:
                user_text = getattr(chat_submission, "text", "") or ""
                uploaded_files = list(getattr(chat_submission, "files", []) or [])

            if not user_text.strip() and not uploaded_files:
                return

            # Intercepta comandos diretos do Spotify (/play, /pause, /skip, /fila)
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
            prompt_for_model = user_text.strip() or "Analise o(s) arquivo(s)/imagem(ns) em anexo de forma direta e crítica."

        with st.chat_message("user", avatar="🕶️"):
            st.markdown(display_prompt)
            for f in uploaded_files:
                if getattr(f, "type", "").startswith("image/"):
                    st.image(f, width=320)

        previous_messages = list(chat_history)
        save_chat_message_supabase("user", display_prompt)
        chat_history.append({"role": "user", "content": prompt_for_model})

        if user_text.strip():
            learned_item = deep_extract_and_save_knowledge(gemini_api_key, user_text, clean_memories)
            if learned_item:
                content_learned, cat_learned = learned_item
                add_memory_to_supabase(content_learned, cat_learned)
                st.toast(f"MEM_WRITE [{cat_learned}]: {content_learned}", icon="⚡")
                all_memories = get_memories_from_supabase()
                clean_memories, pulse_memories = filtrar_memorias_limpas(all_memories)

        web_results = ""
        if any(w in prompt_for_model.lower() for w in ["pesquisa", "pesquise", "internet", "web", "notícia", "artigo", "paper"]):
            web_results = live_web_search(prompt_for_model)

        active_profile = st.session_state.get("profile_input", "")
        system_instruction, tone_mode = build_system_instruction(
            profile_text=active_profile,
            clean_memories=clean_memories,
            recent_messages=previous_messages,
            current_user_message=prompt_for_model,
            engine_mode=engine_mode,
            spotify_context=sp_prompt_ctx,
            cine_mode=cine_mode,
            has_files=bool(file_parts),
            web_context=web_results,
        )

        with st.chat_message("assistant", avatar="⚡"):
            with st.spinner("PROCESSING_SYMBIOSIS_CORTEX..."):
                reply = orchestrate_multi_api_response(
                    gemini_key=gemini_api_key,
                    groq_key=groq_api_key,
                    gemini_model=gemini_model,
                    engine_mode=engine_mode,
                    tone_mode=tone_mode,
                    system_instruction=system_instruction,
                    chat_history=chat_history,
                    user_prompt=prompt_for_model,
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
