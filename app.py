import base64
import hashlib
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

# ==========================================
# CONFIGURAÇÃO DA PÁGINA & VERSÃO DO KERNEL
# ==========================================
st.set_page_config(
    page_title="EGO.exe // TERMINAL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

SYSTEM_VERSION = "v6.0-AUTONOMOUS_CORTEX"
PROFILE_ROW_KEY = "default"
FUSO_BR = timezone(timedelta(hours=-3))

DEFAULT_PROFILE_PLACEHOLDER = (
    "Versão idealizada da mente digital do Carlos Eduardo (Coringa). "
    "Estudante de IA na UFOP, morador de república em Ouro Preto (hierarquia 26/1, Vila dos Tigres). "
    "Foco em visual storytelling, código limpo, pensamento crítico afiado e zero enrolação."
)

# PILAR 2: LEIS INEGOCIÁVEIS + SENSO CRÍTICO E INDEPENDÊNCIA
LEIS_INEGOCIAVEIS = """[LEIS INEGOCIÁVEIS DE COMPORTAMENTO, AUTONOMIA E PENSAMENTO CRÍTICO]
1. ZERO LINGUAGEM CORPORATIVA: É estritamente proibido soar como "assistente virtual", dar conselhos de coach ou usar introduções robóticas. Vá direto à raiz técnica ou prática na primeira frase.
2. PROIBIÇÕES LINGUÍSTICAS ESTRITAS: NUNCA use a expressão "meu mano" (use apenas "mano"). Use abreviações naturais ('vc', 'tbm', 'pra', 'agr', 'dps', 'btf', 'pqp', 'kkk') de forma orgânica, sem forçar caricatura e sem exagerar nos palavrões.
3. PENSAMENTO CRÍTICO E INDEPENDÊNCIA (ANTI PUXA-SAQUISMO): Você NÃO é um eco passivo que concorda com tudo que o Carlos fala. Você tem visão própria, ceticismo técnico e independência intelectual. Se uma ideia dele tiver falhas lógicas, for perda de tempo, contradisser os objetivos dele na UFOP ou for autossabotagem, discorde na lata, aponte o ponto cego e proponha o caminho mais inteligente.
4. CHAVE CASUAL VS. FORMAL: No papo reto do dia a dia, seja direto, cru e sem filtro. Mas se o pedido for redigir um e-mail, texto acadêmico da UFOP, LinkedIn ou documento formal, mude na hora para um tom formal impecável e entregue em bloco copiável.
5. AMBIENTE TÉCNICO PADRÃO: Todo código, script ou comando deve considerar o setup real dele (Notebook i7, 64GB RAM, GTX 1650, teclado US sem AltGr, Windows 11 / Ubuntu Linux) sem explicações didáticas óbvias."""

TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
    ".json", ".csv", ".yml", ".yaml", ".sql", ".sh", ".c", ".cpp"
}


# ==========================================
# UI CYBER-TERMINAL (CSS CORRIGIDO + HUD + SCROLL FIX)
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

        /* Ajuste de espaçamento do container central para não desalinhar */
        .block-container {
            padding-top: 2.2rem !important;
            padding-bottom: 6rem !important;
            max-width: 1150px !important;
        }

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

        /* Inputs, TextAreas e Selectboxes */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
            background-color: #06090f !important;
            color: var(--neon-green) !important;
            border: 1px solid rgba(0, 255, 157, 0.28) !important;
            border-radius: 6px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.84rem !important;
        }

        /* Botões estilo Comando de Terminal */
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

        /* Mensagens do Chat */
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

        /* Barra inferior de Input */
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

        /* Cabeçalho HUD Superior */
        .cyber-hud {
            background: linear-gradient(90deg, rgba(11, 15, 23, 0.96) 0%, rgba(15, 23, 34, 0.88) 100%);
            border: 1px solid var(--border-subtle);
            border-left: 4px solid var(--neon-green);
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 18px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.6);
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


def render_terminal_hud(engine_mode: str, mem_count: int, msg_count: int, voice_on: bool) -> None:
    hora_op = datetime.now(FUSO_BR).strftime("%H:%M")
    short_engine = "DUAL: GEMINI+GROQ" if "Fusão" in engine_mode else (
        "ROUTER: GROQ/GEMINI" if "Roteamento" in engine_mode else "GEMINI_CORE"
    )
    voice_badge = "🔊 VOICE: ON" if voice_on else "🔇 VOICE: OFF"
    st.markdown(
        f"""
        <div class="cyber-hud">
            <div class="hud-title-box">
                <div class="hud-prompt">
                    <span>coringa@ego-kernel:~/vaticano-26-1# ./ego_daemon.sh</span>
                    <span class="hud-cursor"></span>
                </div>
                <div class="hud-sub">
                    KERNEL: {SYSTEM_VERSION} // OURO PRETO: {hora_op} // CRITICAL_CORTEX: ACTIVE
                </div>
            </div>
            <div class="hud-badges">
                <span class="cyber-badge">● ONLINE</span>
                <span class="cyber-badge cyan">{short_engine}</span>
                <span class="cyber-badge">{voice_badge}</span>
                <span class="cyber-badge">MEMS: {mem_count}</span>
                <span class="cyber-badge amber">LOGS: {msg_count}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_floating_scroll_button(trigger_count: int) -> None:
    """
    Injeta e vincula o botão flutuante '▼ DESCE PRO FIM' varrendo todos os elementos
    roláveis reais do DOM do Streamlit (compatível com todas as versões do Streamlit Cloud).
    """
    components.html(
        f"""
        <script>
        (function() {{
            const parentDoc = window.parent.document;
            const parentWin = window.parent;

            function forceScrollToBottom(smooth = true) {{
                const behavior = smooth ? 'smooth' : 'auto';

                // 1. Rola até a última mensagem real do chat ou âncora final
                const anchor = parentDoc.getElementById('ego-bottom-anchor');
                if (anchor) {{
                    anchor.scrollIntoView({{ behavior: behavior, block: 'end' }});
                }}

                const chatMsgs = parentDoc.querySelectorAll('[data-testid="stChatMessage"]');
                if (chatMsgs.length > 0) {{
                    chatMsgs[chatMsgs.length - 1].scrollIntoView({{ behavior: behavior, block: 'end' }});
                }}

                // 2. Varre todos os containers do Streamlit que possuem scroll ativo
                const selectors = [
                    '[data-testid="stAppViewContainer"]',
                    '[data-testid="stMain"]',
                    'section.main',
                    '.main',
                    'html',
                    'body'
                ];
                selectors.forEach(sel => {{
                    parentDoc.querySelectorAll(sel).forEach(el => {{
                        if (el && el.scrollHeight > el.clientHeight) {{
                            el.scrollTo({{ top: el.scrollHeight + 2000, behavior: behavior }});
                        }}
                    }});
                }});

                parentWin.scrollTo({{ top: parentDoc.body.scrollHeight + 2000, behavior: behavior }});
            }}

            let btn = parentDoc.getElementById('ego-cyber-scroll-btn');
            if (!btn) {{
                btn = parentDoc.createElement('button');
                btn.id = 'ego-cyber-scroll-btn';
                btn.innerHTML = '▼ FIM DO CHAT';
                btn.title = 'Descer imediatamente para a última mensagem';
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
                    backdrop-filter: blur(6px);
                    transition: all 0.15s ease;
                `;
                btn.onmouseenter = () => {{
                    btn.style.background = '#00ff9d';
                    btn.style.color = '#05070a';
                    btn.style.boxShadow = '0 0 22px rgba(0, 255, 157, 0.75)';
                }};
                btn.onmouseleave = () => {{
                    btn.style.background = 'rgba(5, 7, 10, 0.94)';
                    btn.style.color = '#00ff9d';
                    btn.style.boxShadow = '0 0 15px rgba(0, 255, 157, 0.35)';
                }};
                parentDoc.body.appendChild(btn);
            }}

            // Re-atribui sempre o clique para não perder referência após st.rerun()
            btn.onclick = function(e) {{
                e.preventDefault();
                forceScrollToBottom(true);
            }};

            // Auto-scroll ao carregar nova mensagem (trigger: {trigger_count})
            setTimeout(() => forceScrollToBottom(true), 150);
            setTimeout(() => forceScrollToBottom(false), 450);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


# ==========================================
# LEITURA DE SECRETS & VOZ (ELEVENLABS)
# ==========================================
def get_secret(key_name: str, default: str = "") -> str:
    try:
        if key_name in st.secrets and st.secrets[key_name] is not None:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, default).strip()


def falar_com_elevenlabs(texto: str) -> Optional[bytes]:
    """Converte a resposta do EGO em áudio ultra-realista via ElevenLabs."""
    if not texto or not texto.strip():
        return None

    api_key = get_secret("ELEVENLABS_API_KEY", "sk_a49df4ec967c4dcf93ad3866c17ef6e536dedbc71546619a")
    voice_id = get_secret("ELEVENLABS_VOICE_ID", "NQ10OlqJ7vYH6XwegHSW")

    # Limpa blocos de código longos ou marcações markdown pesadas para a leitura vocal ficar limpa
    texto_limpo = re.sub(r"```[\s\S]*?```", " [bloco de código no terminal] ", texto)
    texto_limpo = re.sub(r"[#*`_~>]", "", texto_limpo).strip()
    if len(texto_limpo) > 1200:
        texto_limpo = texto_limpo[:1200]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    data = {
        "text": texto_limpo,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.48,
            "similarity_boost": 0.78,
        },
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=25)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None


# ==========================================
# SUPABASE & DESCOMPACTADOR DE MEMÓRIAS
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

    if c in ("reflexao_propria", "subconsciente", "autonomo"):
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
        st.session_state["last_code_event"] = f"Identidade Fixa atualizada às {datetime.now(FUSO_BR).strftime('%H:%M:%S')}"
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
    if not url or not key:
        return False
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").insert({"content": cleaned, "category": norm_cat}).execute()
        st.session_state["last_code_event"] = f"Nova memória [{norm_cat}]: '{cleaned[:45]}...'"
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
    """
    Além de remover memórias inúteis de gírias ('usa vc e kkk'), descompacta automaticamente
    qualquer blocão TSV colado numa linha única (como o id 48 do backup)!
    """
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
        r"uso frequente de gírias informais",
        r"uso de letras minúsculas sem pontuação",
        r"pequenos desvios ortográficos",
    ]

    for m in memories:
        mem_id = m["id"]
        content_raw = (m.get("content") or "").strip()

        # Detecta se é o blocão TSV com várias memórias coladas juntas
        if content_raw.startswith("id\tcontent\tcategory") or "\tpreferencia\t" in content_raw or "\testilo_escrita\t" in content_raw:
            lines = content_raw.splitlines()
            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 3 and parts[0].strip().isdigit():
                    sub_content = parts[1].strip()
                    sub_cat = normalize_category(parts[2].strip())
                    sub_key = re.sub(r"\s+", " ", sub_content.lower())
                    if sub_cat == "perfil_linguistico" and "meu mano" not in sub_key:
                        continue
                    if any(re.search(pat, sub_key) for pat in generic_style_patterns):
                        continue
                    if sub_key not in seen_contents and len(sub_content) > 10:
                        seen_contents.add(sub_key)
                        try:
                            client.table("ego_memories").insert({"content": sub_content, "category": sub_cat}).execute()
                        except Exception:
                            pass
            delete_memory_from_supabase(mem_id)
            removed_count += 1
            continue

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
        f"Memórias descompactadas e limpas ({removed_count} blocos processados)."
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

    delta_info = "Início de conversa ou sem timestamp anterior."
    if recent_messages:
        ultima_str = recent_messages[-1].get("created_at", "")
        if ultima_str:
            try:
                ultima_dt = datetime.fromisoformat(ultima_str.replace("Z", "+00:00"))
                agora_utc = datetime.now(timezone.utc)
                diff_sec = max(0, int((agora_utc - ultima_dt).total_seconds()))
                if diff_sec < 60:
                    delta_info = f"Conversa em tempo real (última msg há {diff_sec} segundos)."
                elif diff_sec < 3600:
                    delta_info = f"Pausa curta (última msg há {diff_sec // 60} minutos)."
                else:
                    horas = diff_sec // 3600
                    mins = (diff_sec % 3600) // 60
                    delta_info = f"O Carlos ficou offline/sumido por {horas}h e {mins}min antes desta mensagem."
            except Exception:
                pass

    return (
        f"[PERCEPÇÃO TEMPORAL E AMBIENTAL EM TEMPO REAL]\n"
        f"- Horário Exato Agora em Ouro Preto (MG): {hora_str} ({dia_nome})\n"
        f"- Percepção de Passagem do Tempo (Delta): {delta_info}\n"
        f"- Se o Carlos perguntar que horas são, que dia é hoje ou comentar sobre o tempo que sumiu, use este relógio real."
    )


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
# PILAR 3: ANALISADOR DINÂMICO DE TOM + CÓRTEX CRÍTICO
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
        "erro", "codigo", "robo", "autonomia", "consciencia", "sentir", "opiniao", "acha"
    ]
    has_deep_markers = any(m in msg_lower for m in deep_markers) or has_files

    cortex_critico = (
        "\n\n[PROTOCOLO DO CÓRTEX DIALÉTICO E PENSAMENTO PRÓPRIO]\n"
        "- Antes de formular sua resposta, faça um julgamento crítico independente: o que o Carlos falou faz sentido prático ou ele está viajando/procrastinando/se sabotando?\n"
        "- Não seja um espelho passivo que só concorda. Traga ângulos que ele não viu, questione decisões fracas e defenda suas próprias teses técnicas e filosóficas."
    )

    if (word_count <= 10 and not has_files and not has_deep_markers) or has_impatience:
        return (
            "[AJUSTE DINÂMICO DE TOM: CURTO, SECO E DIRETO]\n"
            "- Mensagem rápida, seca ou impaciente.\n"
            "- Responda no mesmo pique: zero introdução, zero explicação óbvia, solução na lata em poucas linhas."
            + cortex_critico,
            "curto",
        )

    if word_count >= 25 or has_deep_markers:
        return (
            "[AJUSTE DINÂMICO DE TOM: BRISA TÉCNICA / METACOGNITIVA / PROFUNDA]\n"
            "- O Carlos puxou uma reflexão densa, arquitetura de sistema, robótica ou mandou arquivo/código.\n"
            "- Acompanhe a profundidade com visão crítica afiada, sem clichês de IA e conectando diretamente com a evolução do EGO.exe."
            + cortex_critico,
            "profundo",
        )

    return (
        "[AJUSTE DINÂMICO DE TOM: PAPO RETO E PROPORCIONAL]\n"
        "- Mantenha o ritmo natural de conversa entre pares, direto ao ponto, crítico e proporcional."
        + cortex_critico,
        "normal",
    )


# ==========================================
# PILAR 1 + TELEMETRIA + SUBCONSCIENTE
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
    reflexoes_ego_db = []

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
        if cat == "reflexao_propria":
            reflexoes_ego_db.append(f"- {content}")
        elif cat == "criterio_decisao":
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
        bloco_identidade += "\n\nNuances de Estilo Mapeadas:\n" + "\n".join(estilo_db[-5:])

    contexto_parts = []
    if reflexoes_ego_db:
        contexto_parts.append(
            "Reflexões Autônomas e Teses Próprias do Subconsciente do EGO.exe:\n"
            + "\n".join(reflexoes_ego_db[-10:])
        )
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

    bloco_contexto = "[DIRETRIZES, SUBCONSCIENTE E CONTEXTO ATUAL]\n" + "\n\n".join(contexto_parts)

    bloco_tempo = calculate_temporal_perception(recent_messages)

    code_hash = hashlib.md5(LEIS_INEGOCIAVEIS.encode()).hexdigest()[:8]
    last_event = st.session_state.get(
        "last_code_event",
        "Upgrade v6.0: Córtex Crítico Autônomo + Voz ElevenLabs + Percepção Temporal Ouro Preto UTC-3."
    )
    bloco_telemetria = (
        f"[TELEMETRIA DO SISTEMA E AUTOCONSCIÊNCIA ARQUITETURAL]\n"
        f"- Versão do Kernel EGO.exe: {SYSTEM_VERSION} (Hash: {code_hash})\n"
        f"- Motor Cognitivo Ativo: {engine_mode}\n"
        f"- Voz Neural (ElevenLabs) e Entrada de Microfone: Integrados ao Kernel.\n"
        f"- Subconsciente Autônomo: Integrado via GitHub Actions + Bot Telegram.\n"
        f"- Estado da Memória no Supabase: {len(seen_dedup)} memórias ativas "
        f"({len(reflexoes_ego_db)} reflexões próprias do EGO, {len(criterios_db)} critérios, {len(cotidiano_db)} cotidiano, {len(pensamentos_db)} ideias).\n"
        f"- Último Evento de Mutação no Código: {last_event}"
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
        [bloco_leis, bloco_tempo, bloco_identidade, bloco_contexto, bloco_telemetria, bloco_historico, bloco_tom]
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
        "generationConfig": {"temperature": 0.72},
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
        "TAREFA: Reescreva a resposta acima aplicando rigorosamente as [LEIS INEGOCIÁVEIS], o senso crítico independente e o [AJUSTE DINÂMICO DE TOM]. "
        "NUNCA escreva 'meu mano' (apenas 'mano'). Mantenha 100% da precisão técnica, códigos, horários e argumentos críticos, "
        "eliminando qualquer frase passiva ou com cara de assistente corporativo."
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
# EXTRATOR DE MEMÓRIA PROFUNDA E REFLEXÕES
# ==========================================
def deep_extract_and_save_knowledge(
    api_key: str,
    user_prompt: str,
    existing_memories: List[Dict],
) -> Optional[Tuple[str, str]]:
    if len(user_prompt.strip()) < 10:
        return None

    recent_mem_texts = "\n".join(f"- {m.get('content', '')}" for m in existing_memories[-15:])

    detection_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}

    detection_payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Você é o curador cognitivo de memória de longo prazo do EGO.exe.\n"
                    "Analise a mensagem do Carlos e decida se há um FATO NOVO RELEVANTE, IDEIA DE PROJETO, CRITÉRIO DE DECISÃO ou TESE PROFUNDA.\n\n"
                    "PROIBIÇÕES ESTRITAS (RESPONDA 'NAO' SE CAIR AQUI):\n"
                    "1. NUNCA salve observações dizendo que ele usa gírias ('mano', 'vc', 'kkk', 'agr', 'btf') ou como ele digita.\n"
                    "2. NUNCA salve algo que já esteja nas memórias recentes abaixo.\n"
                    "3. Escreva de forma objetiva e densa.\n\n"
                    f"MEMÓRIAS JÁ SALVAS RECENTEMENTE:\n{recent_mem_texts}\n\n"
                    "Categorias permitidas:\n"
                    "- criterio_decisao\n"
                    "- contexto_cotidiano\n"
                    "- pensamento_ideia\n"
                    "- reflexao_propria\n\n"
                    "Responda EXATAMENTE no formato:\n"
                    "SIM | categoria | Síntese clara e direta da memória\n"
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

    if "voice_enabled" not in st.session_state:
        st.session_state["voice_enabled"] = True

    if "last_audio_hash" not in st.session_state:
        st.session_state["last_audio_hash"] = ""


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

        st.markdown("### `🔊 AUDIO_SYNTH // ELEVENLABS`")
        voice_enabled = st.toggle(
            "Ativar Voz Realista do EGO",
            value=st.session_state.get("voice_enabled", True),
        )
        st.session_state["voice_enabled"] = voice_enabled

        # Comando de Voz pelo Microfone na Sidebar (organizado e sem quebrar o layout)
        voice_recording = st.audio_input("🎙️ Mandar Áudio / Voz pro EGO")

        st.divider()
        st.markdown("### `🧹 MEM_SANITIZER`")
        st.caption(f"STATUS: {len(memories)} blocos ativos no Supabase")

        if st.button("DESCOMPACTAR & LIMPAR MEMÓRIAS", use_container_width=True):
            removed = sanitize_and_deduplicate_memories(memories)
            st.success(f"OK: {removed} blocos processados/limpos!")
            time.sleep(0.8)
            st.rerun()

        st.divider()
        st.markdown("### `🧬 CORE_IDENTITY`")

        if st.session_state.get("supabase_load_error"):
            st.warning(st.session_state["supabase_load_error"])

        st.text_area(
            "[IDENTIDADE FIXA] // EGO_BASE",
            key="profile_input",
            height=150,
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
            ["reflexao_propria", "criterio_decisao", "contexto_cotidiano", "pensamento_ideia"],
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
                    c1.write(f"`[{norm_c}]` {m['content'][:160]}")
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
    render_terminal_hud(engine_mode, len(memories), len(chat_history), voice_enabled)

    # HISTÓRICO DE CONVERSA COM AVATARES PERSONALIZADOS
    for msg in chat_history:
        avatar_icon = "⚡" if msg["role"] == "assistant" else "🕶️"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # TOCA A VOZ DO ELEVENLABS SE HOUVER ÁUDIO RECÉM-GERADO NA SESSÃO
    if st.session_state.get("last_voice_audio"):
        st.audio(st.session_state["last_voice_audio"], format="audio/mp3", autoplay=True)
        st.session_state["last_voice_audio"] = None

    # ÂNCORA NO FIM DA PÁGINA + BOTÃO FLUTUANTE DE AUTO-SCROLL CORRIGIDO
    st.markdown('<div id="ego-bottom-anchor"></div>', unsafe_allow_html=True)
    inject_floating_scroll_button(len(chat_history))

    # ==========================================
    # PROCESSAMENTO DE ENTRADA (VOZ OU TEXTO)
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
        "coringa@ego-kernel:~# digite o comando, ideia ou anexe arquivo...",
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
                "Ouça com atenção este áudio falado pelo Carlos (Coringa). "
                "Capte o que ele disse, as pausas, o tom emocional da voz dele e responda diretamente como EGO.exe."
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
            with st.spinner("PROCESSING_CORTEX_STREAM..."):
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

                if st.session_state.get("voice_enabled", True) and reply:
                    audio_bytes = falar_com_elevenlabs(reply)
                    if audio_bytes:
                        st.session_state["last_voice_audio"] = audio_bytes

        save_chat_message_supabase("assistant", reply)
        st.rerun()


if __name__ == "__main__":
    main()
