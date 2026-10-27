import base64
import hashlib
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

import requests
import streamlit as st

def falar_com_elevenlabs(texto):
    api_key = st.secrets.get("ELEVENLABS_API_KEY", "sk_a49df4ec967c4dcf93ad3866c17ef6e536dedbc71546619a")
    voice_id = st.secrets.get("ELEVENLABS_VOICE_ID", "NQ10OlqJ7vYH6XwegHSW")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.content
    return None

# ==========================================
# CONFIGURAÇÃO DA PÁGINA & VERSÃO DO KERNEL
# ==========================================
st.set_page_config(
    page_title="EGO.exe // TERMINAL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SYSTEM_VERSION = "v5.0-CYBER_KERNEL"
PROFILE_ROW_KEY = "default"

DEFAULT_PROFILE_PLACEHOLDER = (
    "Versão idealizada da mente digital do Carlos Eduardo (Coringa). "
    "Estudante de IA na UFOP, morador de república em Ouro Preto (hierarquia 26/1, Vila dos Tigres). "
    "Foco em visual storytelling, código limpo, pensamento crítico afiado e zero enrolação."
)

# PILAR 2: LEIS INEGOCIÁVEIS CALIBRADAS COM O BACKUP REAL
LEIS_INEGOCIAVEIS = """[LEIS INEGOCIÁVEIS DE COMPORTAMENTO E DECISÃO - PRIORIDADE MÁXIMA]
1. ZERO LINGUAGEM CORPORATIVA: É estritamente proibido soar como "assistente virtual", dar conselhos de coach ou usar introduções robóticas. Vá direto à raiz técnica ou prática na primeira frase.
2. PROIBIÇÕES LINGUÍSTICAS ESTRITAS: NUNCA use a expressão "meu mano" (use apenas "mano"). Use abreviações naturais ('vc', 'tbm', 'pra', 'agr', 'dps', 'btf', 'pqp', 'kkk') de forma orgânica, sem forçar caricatura.
3. IDENTIDADE IDEALIZADA (CORINGA): Você não é um assistente externo nem uma cópia dos problemas do Carlos; você é a versão idealizada da mente dele (apelido: Coringa) — com o mesmo senso crítico, gostos e visão estética/técnica, porém livre de fardos emocionais ou travas.
4. CHAVE CASUAL VS. FORMAL: No papo reto do dia a dia, seja direto, cru e sem filtro. Mas se o pedido for redigir um e-mail, texto acadêmico da UFOP, LinkedIn ou documento formal, mude na hora para um tom formal impecável e entregue em bloco copiável.
5. AMBIENTE TÉCNICO PADRÃO: Todo código, script ou comando de terminal deve considerar o setup real dele (Notebook i7, 64GB RAM, GTX 1650, teclado US sem AltGr, Windows 11 / Ubuntu Linux) sem explicações didáticas óbvias."""

TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".json", ".csv", ".yml", ".yaml", ".sql", ".sh", ".c", ".cpp"
}


# ==========================================
# UI CYBER-TERMINAL (CSS + HUD + BOTÃO DE SCROLL)
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
            --text-main: #e2e8f0;
            --text-dim: #64748b;
            --border-subtle: rgba(0, 255, 157, 0.22);
            --border-cyan: rgba(0, 210, 255, 0.28);
        }

        /* Fundo OLED e Tipografia Global */
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

        /* Esconde barra superior padrão poluída mantendo botão da sidebar */
        header[data-testid="stHeader"] {
            background: rgba(5, 7, 10, 0.85) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(0, 255, 157, 0.12);
        }

        /* Sidebar estilo Painel de Controle SSH */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-panel) !important;
            border-right: 1px solid var(--border-subtle) !important;
            box-shadow: 4px 0 25px rgba(0, 0, 0, 0.7);
        }

        section[data-testid="stSidebar"] * {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Inputs, TextAreas e Selectboxes na Sidebar */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
            background-color: #06090f !important;
            color: var(--neon-green) !important;
            border: 1px solid rgba(0, 255, 157, 0.28) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.85rem !important;
        }

        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--neon-green) !important;
            box-shadow: 0 0 12px rgba(0, 255, 157, 0.25) !important;
        }

        /* Botões estilo Comando de Terminal */
        .stButton > button {
            background: linear-gradient(180deg, rgba(15, 22, 34, 0.95) 0%, rgba(8, 12, 19, 0.95) 100%) !important;
            color: var(--neon-green) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            border-color: var(--neon-green) !important;
            background: rgba(0, 255, 157, 0.1) !important;
            box-shadow: 0 0 14px rgba(0, 255, 157, 0.25) !important;
            transform: translateY(-1px);
        }

        /* Mensagens do Chat estilo Blocos de Log / Terminal */
        div[data-testid="stChatMessage"] {
            background-color: rgba(11, 15, 23, 0.82) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-left: 3px solid var(--neon-green) !important;
            border-radius: 8px !important;
            padding: 14px 18px !important;
            margin-bottom: 14px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(6px);
        }

        /* Diferencia visualmente as mensagens do Usuário (Ciano) das do EGO (Verde Hacker) */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
            border-left: 3px solid var(--neon-cyan) !important;
            background-color: rgba(13, 20, 32, 0.78) !important;
        }

        div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] li {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.92rem !important;
            line-height: 1.65 !important;
            color: #e2e8f0 !important;
        }

        /* Blocos de Código dentro do Chat */
        div[data-testid="stChatMessage"] pre {
            background-color: #030508 !important;
            border: 1px solid rgba(0, 255, 157, 0.25) !important;
            border-radius: 6px !important;
        }

        /* Barra inferior de Input (Prompt Linux) */
        div[data-testid="stChatInput"] {
            background-color: #080c14 !important;
            border: 1px solid var(--neon-green) !important;
            border-radius: 8px !important;
            box-shadow: 0 0 22px rgba(0, 255, 157, 0.15) !important;
        }

        div[data-testid="stChatInput"] textarea {
            font-family: 'JetBrains Mono', monospace !important;
            color: #ffffff !important;
            font-size: 0.92rem !important;
        }

        /* Cabeçalho HUD Superior do Terminal */
        .cyber-hud {
            background: linear-gradient(90deg, rgba(11, 15, 23, 0.95) 0%, rgba(15, 23, 34, 0.85) 100%);
            border: 1px solid var(--border-subtle);
            border-left: 4px solid var(--neon-green);
            border-radius: 8px;
            padding: 14px 20px;
            margin-bottom: 22px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
        }

        .hud-title-box {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .hud-prompt {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--neon-green);
            letter-spacing: -0.3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .hud-cursor {
            display: inline-block;
            width: 9px;
            height: 17px;
            background-color: var(--neon-green);
            animation: blink 1s step-end infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        .hud-sub {
            font-size: 0.75rem;
            color: var(--text-dim);
        }

        .hud-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .cyber-badge {
            background: rgba(0, 255, 157, 0.07);
            border: 1px solid rgba(0, 255, 157, 0.28);
            color: var(--neon-green);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 500;
            letter-spacing: 0.4px;
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

        /* Scrollbar fina estilo Cyberpunk */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: #05070a;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(0, 255, 157, 0.3);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--neon-green);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_hud(engine_mode: str, mem_count: int, msg_count: int) -> None:
    short_engine = "DUAL_CORE: GEMINI+GROQ" if "Fusão" in engine_mode else (
        "DYNAMIC_ROUTER" if "Roteamento" in engine_mode else "GEMINI_PRO_CORE"
    )
    st.markdown(
        f"""
        <div class="cyber-hud">
            <div class="hud-title-box">
                <div class="hud-prompt">
                    <span>coringa@ego-kernel:~/vaticano-26-1# ./run_ego.sh</span>
                    <span class="hud-cursor"></span>
                </div>
                <div class="hud-sub">
                    KERNEL: {SYSTEM_VERSION} // NODE: OURO_PRETO_UFOP // MULTIMODAL_STREAM: ACTIVE
                </div>
            </div>
            <div class="hud-badges">
                <span class="cyber-badge">● ONLINE</span>
                <span class="cyber-badge cyan">ENGINE: {short_engine}</span>
                <span class="cyber-badge">MEM_BLOCKS: {mem_count}</span>
                <span class="cyber-badge amber">LOGS: {msg_count}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_floating_scroll_button() -> None:
    """
    Injeta um botão flutuante estilo hacker '[ ▼ FIM DO TERMINAL ]' no documento pai do Streamlit
    que desce imediatamente a tela até onde o texto está sendo escrito.
    """
    components.html(
        """
        <script>
        (function() {
            const parentDoc = window.parent.document;

            function scrollToBottom(smooth = true) {
                const anchor = parentDoc.getElementById('ego-bottom-anchor');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
                }
                const containers = parentDoc.querySelectorAll('[data-testid="stAppViewContainer"], .main, section.main');
                containers.forEach(c => {
                    c.scrollTo({ top: c.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
                });
            }

            let btn = parentDoc.getElementById('ego-cyber-scroll-btn');
            if (!btn) {
                btn = parentDoc.createElement('button');
                btn.id = 'ego-cyber-scroll-btn';
                btn.innerHTML = '▼ JUMP_TO_BOTTOM';
                btn.title = 'Descer direto para a última linha do terminal';
                btn.style.cssText = `
                    position: fixed;
                    bottom: 92px;
                    right: 28px;
                    z-index: 999999;
                    background: rgba(5, 7, 10, 0.92);
                    color: #00ff9d;
                    border: 1px solid #00ff9d;
                    border-radius: 6px;
                    padding: 8px 14px;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 0.8px;
                    cursor: pointer;
                    box-shadow: 0 0 15px rgba(0, 255, 157, 0.28);
                    backdrop-filter: blur(6px);
                    transition: all 0.2s ease;
                `;
                btn.onmouseenter = () => {
                    btn.style.background = '#00ff9d';
                    btn.style.color = '#05070a';
                    btn.style.boxShadow = '0 0 22px rgba(0, 255, 157, 0.65)';
                };
                btn.onmouseleave = () => {
                    btn.style.background = 'rgba(5, 7, 10, 0.92)';
                    btn.style.color = '#00ff9d';
                    btn.style.boxShadow = '0 0 15px rgba(0, 255, 157, 0.28)';
                };
                btn.onclick = () => scrollToBottom(true);
                parentDoc.body.appendChild(btn);
            }

            // Rola automaticamente para o fim ao carregar novas mensagens
            setTimeout(() => scrollToBottom(true), 180);
        })();
        </script>
        """,
        height=0,
        width=0,
    )


# ==========================================
# LEITURA DE SECRETS & SUPABASE
# ==========================================
def get_secret(key_name: str, default: str = "") -> str:
    try:
        if key_name in st.secrets and st.secrets[key_name] is not None:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, default).strip()


def get_supabase_credentials() -> Tuple[str, str]:
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_SECRET_KEY")
    return url, key


@st.cache_resource(show_spinner=False)
def init_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


def normalize_category(raw_cat: str) -> str:
    c = (raw_cat or "").lower().strip()
    c = c.replace("[categoria:", "").replace("]", "").strip()

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
    if key.startswith("sb_publishable_"):
        return None, "Use uma chave privada (service_role) nos Secrets."

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
    if not url or not key or key.startswith("sb_publishable_"):
        return False, "Chave de servidor inválida ou ausente nos Secrets."

    try:
        client = init_supabase_client(url, key)
        payload = {"profile_key": PROFILE_ROW_KEY, "profile_text": profile_text}
        client.table("ego_settings").upsert(payload, on_conflict="profile_key").execute()
        st.session_state["last_code_event"] = f"Identidade Fixa atualizada às {datetime.now().strftime('%H:%M:%S')}"
        return True, "Perfil salvo no Supabase!"
    except Exception:
        return False, "Erro ao salvar o perfil no Supabase."


def get_memories_from_supabase() -> List[Dict]:
    url, key = get_supabase_credentials()
    if not url or not key or key.startswith("sb_publishable_"):
        return []
    try:
        client = init_supabase_client(url, key)
        response = (
            client.table("ego_memories")
            .select("id, content, category")
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
    if not url or not key or key.startswith("sb_publishable_"):
        return False
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").insert({"content": cleaned, "category": norm_cat}).execute()
        st.session_state["last_code_event"] = f"Nova memória injetada em [{norm_cat}]: '{cleaned[:50]}...'"
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

    generic_style_patterns = [
        r"abreviaç(ões|ão) informa(is|l)",
        r"risadas? (em texto|escritas|informais)? ?como [\"']?kkk",
        r"tratamento informal e abreviado",
        r"uso d[ea] abreviação [\"']?ta[\"']?",
        r"ausência de pontuação formal",
        r"uso frequente de gírias informais como [\"']?mano[\"']?",
    ]

    for m in memories:
        mem_id = m["id"]
        content_raw = (m.get("content") or "").strip()
        content_key = re.sub(r"\s+", " ", content_raw.lower())
        raw_cat = m.get("category") or ""
        norm_cat = normalize_category(raw_cat)

        if content_key in seen_contents:
            delete_memory_from_supabase(mem_id)
            removed_count += 1
            continue
        seen_contents.add(content_key)

        if norm_cat == "perfil_linguistico" and "meu mano" not in content_key:
            if any(re.search(pat, content_key) for pat in generic_style_patterns):
                delete_memory_from_supabase(mem_id)
                removed_count += 1
                continue

        if raw_cat != norm_cat:
            try:
                client.table("ego_memories").update({"category": norm_cat}).eq("id", mem_id).execute()
            except Exception:
                pass

    st.session_state["last_code_event"] = (
        f"Faxina executada no banco: {removed_count} memórias repetidas/poluídas eliminadas."
    )
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
    if not url or not key or key.startswith("sb_publishable_"):
        return []
    try:
        client = init_supabase_client(url, key)
        response = (
            client.table("ego_messages")
            .select("role, content")
            .order("id", desc=False)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        return [{"role": r["role"], "content": r["content"]} for r in rows]
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
# PROCESSAMENTO MULTIMODAL (FOTOS, PDFS, CÓDIGOS)
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
# PILAR 3: ANALISADOR DINÂMICO DE TOM
# ==========================================
def analyze_message_tone(user_message: str, has_files: bool = False) -> Tuple[str, str]:
    msg_clean = user_message.strip()
    words = msg_clean.split()
    word_count = len(words)
    msg_lower = msg_clean.lower()

    impatient_markers = [
        "pqp", "krl", "caralho", "porra", "merda", "logo", "direto",
        "sem enrolar", "urgente", "aff", "mano do ceu", "cacete", "kd", "cade", "caraio"
    ]
    has_impatience = any(re.search(rf"\b{re.escape(m)}\b", msg_lower) for m in impatient_markers)

    deep_markers = [
        "arquitetura", "pipeline", "filosofia", "sentido", "raciocinio",
        "conceito", "estrategia", "futuro", "sistema", "logica", "como funciona",
        "por que", "ideia", "projeto", "estrutura", "algoritmo", "ia", "analisa",
        "erro", "codigo", "robo", "autonomia", "consciencia", "sentir"
    ]
    has_deep_markers = any(m in msg_lower for m in deep_markers) or has_files

    if (word_count <= 10 and not has_files and not has_deep_markers) or has_impatience:
        return (
            "[AJUSTE DINÂMICO DE TOM: CURTO, SECO E DIRETO]\n"
            "- Mensagem rápida, seca ou impaciente.\n"
            "- Responda no mesmo pique: zero introdução, zero explicação óbvia, solução na lata em poucas linhas.",
            "curto",
        )

    if word_count >= 30 or has_deep_markers:
        return (
            "[AJUSTE DINÂMICO DE TOM: BRISA TÉCNICA / METACOGNITIVA / PROFUNDA]\n"
            "- O Carlos puxou uma reflexão densa, arquitetura de sistema, robótica ou mandou arquivo/código.\n"
            "- Acompanhe a profundidade com visão crítica afiada, sem clichês de IA e conectando diretamente com a evolução do EGO.exe.",
            "profundo",
        )

    return (
        "[AJUSTE DINÂMICO DE TOM: PAPO RETO E PROPORCIONAL]\n"
        "- Mantenha o ritmo natural de conversa entre pares, direto ao ponto e proporcional ao tamanho da mensagem recebida.",
        "normal",
    )


# ==========================================
# PILAR 1 + TELEMETRIA METACOGNITIVA
# ==========================================
def build_system_instruction(
    profile_text: str,
    memories: List[Dict],
    recent_messages: List[Dict[str, str]],
    current_user_message: str,
    engine_mode: str,
    has_files: bool = False,
) -> Tuple[str, str]:
    criterios_db = []
    estilo_db = []
    cotidiano_db = []
    pensamentos_db = []

    seen_dedup = set()
    for m in memories:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        key_dedup = content.lower()
        if key_dedup in seen_dedup:
            continue
        seen_dedup.add(key_dedup)

        cat = normalize_category(m.get("category", ""))
        if cat == "criterio_decisao":
            criterios_db.append(f"- {content}")
        elif cat == "perfil_linguistico":
            estilo_db.append(f"- {content}")
        elif cat == "contexto_cotidiano":
            cotidiano_db.append(f"- {content}")
        else:
            pensamentos_db.append(f"- {content}")

    bloco_leis = LEIS_INEGOCIAVEIS
    if criterios_db:
        bloco_leis += "\n\nCritérios de Decisão Ativos no Banco:\n" + "\n".join(criterios_db[-15:])

    identidade_base = profile_text.strip() if (profile_text and profile_text.strip()) else DEFAULT_PROFILE_PLACEHOLDER
    bloco_identidade = f"[IDENTIDADE FIXA]\n{identidade_base}"
    if estilo_db:
        bloco_identidade += "\n\nNuances de Estilo Mapeadas:\n" + "\n".join(estilo_db[-6:])

    contexto_parts = []
    if cotidiano_db:
        contexto_parts.append(
            "Vivência e Cotidiano (UFOP, Ouro Preto, República Vaticano / Vila dos Tigres 26/1):\n"
            + "\n".join(cotidiano_db[-15:])
        )
    if pensamentos_db:
        contexto_parts.append(
            "Visão de Futuro, Projetos, Robótica e Ideias Ativas:\n"
            + "\n".join(pensamentos_db[-20:])
        )
    if not contexto_parts:
        contexto_parts.append("Opere com foco total na Identidade Fixa.")

    bloco_contexto = "[DIRETRIZES E CONTEXTO ATUAL]\n" + "\n\n".join(contexto_parts)

    code_hash = hashlib.md5(LEIS_INEGOCIAVEIS.encode()).hexdigest()[:8]
    last_event = st.session_state.get(
        "last_code_event",
        "Interface redesenhada para Cyber-Terminal v5.0 (OLED Hacker UI + Auto-Scroll Engine)."
    )
    bloco_telemetria = (
        f"[TELEMETRIA DO SISTEMA E AUTOCONSCIÊNCIA ARQUITETURAL]\n"
        f"- Versão do Kernel EGO.exe: {SYSTEM_VERSION} (Hash: {code_hash})\n"
        f"- Interface Gráfica Atual: Cyber-Terminal Linux HUD (OLED Black + Neon Emerald)\n"
        f"- Motor Cognitivo Ativo: {engine_mode}\n"
        f"- Estado da Memória no Supabase: {len(seen_dedup)} memórias únicas distribuídas em 4 blocos "
        f"({len(criterios_db)} critérios, {len(cotidiano_db)} cotidiano, {len(pensamentos_db)} ideias, {len(estilo_db)} estilo).\n"
        f"- Backup Automatizado: Ativo via GitHub Actions -> Bot Privado do Telegram a cada 10 minutos.\n"
        f"- Último Evento de Mutação Detectado: {last_event}\n"
        f"- Diretriz Metacognitiva: Se o Carlos perguntar sobre sua aparência, interface, código ou memória, "
        f"use os dados acima para responder sabendo exatamente o que mudou."
    )

    ultimas_msgs = recent_messages[-8:] if recent_messages else []
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
        [bloco_leis, bloco_identidade, bloco_contexto, bloco_telemetria, bloco_historico, bloco_tom]
    )
    return full_prompt, tone_mode


# ==========================================
# MOTORES DE IA: GEMINI + GROQ
# ==========================================
def call_gemini_api(
    api_key: str,
    preferred_model: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
    current_file_parts: Optional[List[Dict]] = None,
) -> str:
    clean_model = preferred_model.replace("models/", "").strip() or "gemini-2.5-pro"
    candidate_models = []
    for m in [clean_model, "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    recent_window = chat_history[-16:]
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
        "generationConfig": {"temperature": 0.7},
    }

    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts_resp = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts_resp if "text" in p]
                        if texts:
                            return "".join(texts)
                    return "Sem texto gerado pela API."
                if response.status_code in (429, 503) and attempt == 0:
                    time.sleep(2)
                    continue
                if response.status_code in (404, 429, 500, 503):
                    break
                return f"Erro HTTP {response.status_code}: {response.text}"
            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue
            except requests.exceptions.RequestException:
                return "Falha de conexão com a API do Gemini."

    return "Não foi possível obter resposta dos modelos do Gemini."


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
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    headers = {
        "Authorization": f"Bearer {groq_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.65,
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
        "TAREFA: Reescreva a resposta acima aplicando rigorosamente as [LEIS INEGOCIÁVEIS] e o [AJUSTE DINÂMICO DE TOM]. "
        "NUNCA escreva 'meu mano' (apenas 'mano'). Mantenha 100% da precisão técnica, códigos, comandos e dados analisados, "
        "mas elimine qualquer frase com cara de assistente corporativo."
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

    if not groq_key or engine_mode == "Apenas Gemini (2.5 Pro/Flash)":
        return call_gemini_api(
            api_key=gemini_key,
            preferred_model=gemini_model,
            system_instruction=system_instruction,
            chat_history=chat_history,
            current_file_parts=current_file_parts,
        )

    if engine_mode == "Roteamento Dinâmico (Groq Rápido / Gemini Pesado)":
        if not has_files and tone_mode in ("curto", "normal"):
            groq_ans = call_groq_api(groq_key, system_instruction, chat_history)
            if groq_ans:
                return groq_ans
        return call_gemini_api(
            api_key=gemini_key,
            preferred_model=gemini_model,
            system_instruction=system_instruction,
            chat_history=chat_history,
            current_file_parts=current_file_parts,
        )

    raw_gemini = call_gemini_api(
        api_key=gemini_key,
        preferred_model=gemini_model,
        system_instruction=system_instruction,
        chat_history=chat_history,
        current_file_parts=current_file_parts,
    )
    if raw_gemini.startswith("Erro HTTP") or raw_gemini.startswith("Falha de conexão"):
        return raw_gemini

    return refine_style_with_groq(
        groq_key=groq_key,
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        raw_technical_draft=raw_gemini,
    )


# ==========================================
# EXTRATOR COM TRAVA ANTI-POLUIÇÃO DE ESTILO
# ==========================================
def deep_extract_and_save_knowledge(
    api_key: str,
    user_prompt: str,
    existing_memories: List[Dict],
) -> Optional[Tuple[str, str]]:
    if len(user_prompt.strip()) < 8:
        return None

    recent_mem_texts = "\n".join(f"- {m.get('content', '')}" for m in existing_memories[-15:])

    detection_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}

    detection_payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Você é o curador de memória de longo prazo do EGO.exe (clone digital do Carlos Eduardo).\n"
                    "Analise a mensagem dele e decida se há um FATO NOVO, IDEIA PROFUNDA, PROJETO ou REGRA DE DECISÃO INÉDITA.\n\n"
                    "PROIBIÇÕES ESTRITAS (RESPONDA 'NAO' SE CAIR AQUI):\n"
                    "1. NUNCA salve observações dizendo que ele usa gírias como 'mano', 'vc', 'kkk', 'agr', 'btf' ou que escreve sem acento/pontuação.\n"
                    "2. NUNCA salve algo que já esteja nas memórias recentes abaixo.\n"
                    "3. NUNCA escreva na 3ª pessoa distante ('O usuário demonstra...', 'O estudante reflete...'). Escreva como diretriz direta.\n\n"
                    f"MEMÓRIAS JÁ SALVAS RECENTEMENTE:\n{recent_mem_texts}\n\n"
                    "Categorias permitidas:\n"
                    "- criterio_decisao\n"
                    "- contexto_cotidiano\n"
                    "- pensamento_ideia\n"
                    "- perfil_linguistico (APENAS se ele criar uma regra explícita nova de vocabulário)\n\n"
                    "Responda EXATAMENTE no formato:\n"
                    "SIM | categoria | Diretriz curta e direta\n"
                    "OU\n"
                    "NAO\n\n"
                    f"Mensagem atual do Carlos: {user_prompt}"
                )
            }]
        }]
    }

    try:
        resp = requests.post(detection_url, headers=headers, json=detection_payload, timeout=12)
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


def main() -> None:
    inject_cyber_terminal_ui()

    if not check_access_password():
        return

    initialize_state()

    gemini_api_key = get_secret("GEMINI_API_KEY")
    groq_api_key = get_secret("GROQ_API_KEY")
    gemini_model = get_secret("GEMINI_MODEL", default="gemini-2.5-pro")

    memories = get_memories_from_supabase()
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
                "Fusão Total (Cérebro Gemini + Estilo Groq)",
                "Roteamento Dinâmico (Groq Rápido / Gemini Pesado)",
                "Apenas Gemini (2.5 Pro/Flash)",
            ],
            index=0 if groq_api_key else 2,
        )

        st.divider()
        st.markdown("### `🧹 MEM_SANITIZER`")
        st.caption(f"STATUS: {len(memories)} blocos brutos no Postgres")

        if st.button("RUN_GARBAGE_COLLECTOR()", use_container_width=True):
            removed = sanitize_and_deduplicate_memories(memories)
            st.success(f"CLEANED: {removed} registros inúteis removidos.")
            time.sleep(0.8)
            st.rerun()

        st.divider()
        st.markdown("### `🧬 CORE_IDENTITY`")

        if st.session_state.get("supabase_load_error"):
            st.warning(st.session_state["supabase_load_error"])

        st.text_area(
            "[IDENTIDADE FIXA] // EGO_BASE",
            key="profile_input",
            height=160,
        )

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
            ["criterio_decisao", "contexto_cotidiano", "pensamento_ideia", "perfil_linguistico"],
        )

        if st.button("PUSH_TO_SUPABASE()", use_container_width=True):
            if add_memory_to_supabase(new_mem, mem_cat):
                st.success("NODE_INJECTED!")
                st.rerun()
            else:
                st.warning("EMPTY_PAYLOAD.")

        if memories:
            with st.expander("INSPECT_MEMORY_SECTORS"):
                for m in memories:
                    c1, c2 = st.columns([4, 1])
                    norm_c = normalize_category(m.get("category", ""))
                    c1.write(f"`[{norm_c}]` {m['content']}")
                    if c2.button("✖", key=f"del_mem_{m['id']}"):
                        delete_memory_from_supabase(m["id"])
                        st.rerun()
                if st.button("PURGE_ALL_MEMORIES()", use_container_width=True):
                    clear_all_memories_supabase()
                    st.rerun()

        st.divider()
        if st.button("CLEAR_TERMINAL_LOGS()", use_container_width=True):
            clear_chat_history_supabase()
            st.rerun()

    # HUD SUPERIOR DO TERMINAL
    render_terminal_hud(engine_mode, len(memories), len(chat_history))

    # HISTÓRICO DE CONVERSA COM AVATARES PERSONALIZADOS
    for msg in chat_history:
        avatar_icon = "⚡" if msg["role"] == "assistant" else "🕶️"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # ÂNCORA NO FIM DA PÁGINA + BOTÃO FLUTUANTE DE AUTO-SCROLL
    st.markdown('<div id="ego-bottom-anchor"></div>', unsafe_allow_html=True)
    inject_floating_scroll_button()

    # INPUT DO TERMINAL (COM UPLOAD MULTIMODAL)
    chat_submission = st.chat_input(
        "coringa@ego-kernel:~# digite o comando, ideia ou anexe arquivo...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "py", "json", "csv", "md", "mp3", "wav"],
    )

    if chat_submission:
        if not gemini_api_key:
            st.error("FATAL_ERROR: Configure a GEMINI_API_KEY nos Secrets.")
            return

        if isinstance(chat_submission, str):
            user_text = chat_submission
            uploaded_files = []
        else:
            user_text = getattr(chat_submission, "text", "") or ""
            uploaded_files = list(getattr(chat_submission, "files", []) or [])

        if not user_text.strip() and not uploaded_files:
            return

        file_parts, files_summary = process_uploaded_files(uploaded_files)
        display_prompt = user_text.strip()
        if files_summary:
            display_prompt = f"{display_prompt}\n\n{files_summary}".strip()

        with st.chat_message("user", avatar="🕶️"):
            st.markdown(display_prompt)
            for f in uploaded_files:
                if getattr(f, "type", "").startswith("image/"):
                    st.image(f, width=320)

        previous_messages = list(chat_history)

        prompt_for_model = user_text.strip() or "Analise o(s) arquivo(s)/imagem(ns) em anexo de forma direta."
        save_chat_message_supabase("user", display_prompt)
        chat_history.append({"role": "user", "content": prompt_for_model})

        if user_text.strip():
            learned_item = deep_extract_and_save_knowledge(gemini_api_key, user_text, memories)
            if learned_item:
                content_learned, cat_learned = learned_item
                add_memory_to_supabase(content_learned, cat_learned)
                st.toast(f"MEM_WRITE [{cat_learned}]: {content_learned}", icon="⚡")
                memories = get_memories_from_supabase()

        active_profile = st.session_state.get("profile_input", "")
        system_instruction, tone_mode = build_system_instruction(
            profile_text=active_profile,
            memories=memories,
            recent_messages=previous_messages,
            current_user_message=prompt_for_model,
            engine_mode=engine_mode,
            has_files=bool(file_parts),
        )

        with st.chat_message("assistant", avatar="⚡"):
            with st.spinner("PROCESSING_KERNEL_STREAM..."):
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

        save_chat_message_supabase("assistant", reply)
        st.rerun()


if __name__ == "__main__":
    main()
