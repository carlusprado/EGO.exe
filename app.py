import os
import time
from typing import Dict, List, Optional, Tuple

import requests
import streamlit as st
from supabase import Client, create_client

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="EGO.exe - Streamlit",
    page_icon="🧠",
    layout="wide",
)

PROFILE_ROW_KEY = "default"
DEFAULT_PROFILE_PLACEHOLDER = (
    "# Perfil do EGO\n\n"
    "Cole aqui suas instruções completas de perfil e clique em 'Salvar perfil'."
)


# ==========================================
# LEITURA DE SECRETS
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


# ==========================================
# CLIENTE SUPABASE
# ==========================================
@st.cache_resource(show_spinner=False)
def init_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    return create_client(supabase_url, supabase_key)


# --- PERFIL ---
def load_profile_from_supabase() -> Tuple[Optional[str], Optional[str]]:
    url, key = get_supabase_credentials()
    if not url or not key:
        return None, "Credenciais do Supabase ausentes nos Secrets."
    if key.startswith("sb_publishable_"):
        return None, "Use uma chave privada de servidor nos Secrets."

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
        return True, "Perfil salvo com sucesso no Supabase!"
    except Exception:
        return False, "Erro ao salvar o perfil no Supabase."


# --- MEMÓRIAS E ESTILO DE ESCRITA (SUPABASE) ---
def get_memories_from_supabase() -> List[Dict]:
    url, key = get_supabase_credentials()
    if not url or not key or key.startswith("sb_publishable_"):
        return []
    try:
        client = init_supabase_client(url, key)
        response = client.table("ego_memories").select("id, content, category").order("id", desc=False).execute()
        return getattr(response, "data", None) or []
    except Exception:
        return []


def add_memory_to_supabase(content: str, category: str = "geral") -> bool:
    cleaned = content.strip()
    if not cleaned:
        return False
    url, key = get_supabase_credentials()
    if not url or not key or key.startswith("sb_publishable_"):
        return False
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").insert({"content": cleaned, "category": category}).execute()
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


def clear_all_memories_supabase() -> None:
    url, key = get_supabase_credentials()
    if not url or not key:
        return
    try:
        client = init_supabase_client(url, key)
        client.table("ego_memories").delete().gt("id", 0).execute()
    except Exception:
        pass


# --- HISTÓRICO DE CHAT (SUPABASE) ---
def get_chat_history_supabase() -> List[Dict[str, str]]:
    url, key = get_supabase_credentials()
    if not url or not key or key.startswith("sb_publishable_"):
        return []
    try:
        client = init_supabase_client(url, key)
        response = client.table("ego_messages").select("role, content").order("id", desc=False).execute()
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
# INTEGRAÇÃO COM GOOGLE GEMINI API
# ==========================================
def build_system_instruction(profile_text: str, memories: List[Dict]) -> str:
    parts = []
    if profile_text and profile_text.strip():
        parts.append(profile_text.strip())

    style_rules = [
        "DIRETRIZ DE ESTILO DE ESCRITA OBRIGATÓRIA:",
        "- Imite rigorosamente o estilo de escrita natural, informal e direto do criador.",
        "- Utilize as abreviações, gírias e a forma descontraída de encurtar palavras que ele usa (como 'vc', 'tbm', etc.).",
        "- Não utilize formalidades robóticas ou excesso de rigidez gramatical quando o tom for casual."
    ]
    parts.append("\n".join(style_rules))

    if memories:
        mem_lines = "\n".join(f"- [{m.get('category', 'geral').upper()}] {m['content']}" for m in memories)
        parts.append(
            f"## Memórias, Ideias e Padrões de Estilo Acumulados\n"
            f"Estes são conhecimentos, gírias e formas de escrita capturadas anteriormente:\n{mem_lines}"
        )

    return "\n\n".join(parts)


def call_gemini_api(
    api_key: str,
    preferred_model: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
) -> str:
    clean_model = preferred_model.replace("models/", "").strip() or "gemini-3.5-flash-lite"
    candidate_models = []
    for m in [clean_model, "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash"]:
        if m and m not in candidate_models:
            candidate_models.append(m)

    contents = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload: Dict = {"contents": contents}
    if system_instruction.strip():
        payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts if "text" in p]
                        if texts:
                            return "".join(texts)
                    return "O modelo respondeu sem texto gerado."
                if response.status_code in (429, 503) and attempt == 0:
                    time.sleep(2)
                    continue
                if response.status_code in (404, 429, 500, 503):
                    break
                return f"Erro HTTP {response.status_code} ao comunicar com o Gemini."
            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue
            except requests.exceptions.RequestException:
                return "Falha de rede ao comunicar com a API."

    return "Erro temporário nos servidores do Gemini."


def auto_detect_and_save_knowledge(api_key: str, user_prompt: str) -> Optional[Tuple[str, str]]:
    """
    Analisa a mensagem do usuário para extrair ideias, pensamentos críticos OU
    padrões de escrita/gírias/abreviações utilizadas (ex: 'vc', 'tbm', gírias).
    """
    detection_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}
    
    detection_payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Analise a frase enviada pelo criador. Verifique se ela contém:\n"
                    "1. Uma abreviação específica, gíria ou padrão de escrita próprio dele (ex: uso de 'vc', 'tbm', maneirismos).\n"
                    "2. Uma ideia, pensamento crítico ou conceito relevante.\n\n"
                    "Se houver algo útil para gravar no estilo ou nas memórias, responda EXATAMENTE no formato:\n"
                    "SIM | [categoria: estilo_escrita, ideia, pensamento_critico ou conhecimento] | [Descrição clara do padrão ou ideia em 1 frase]\n"
                    "OU\n"
                    "NAO\n\n"
                    f"Frase: {user_prompt}"
                )
            }]
        }]
    }

    try:
        resp = requests.post(detection_url, headers=headers, json=detection_payload, timeout=15)
        if resp.status_code == 200:
            ans = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if ans.startswith("SIM"):
                parts = ans.split("|")
                if len(parts) >= 3:
                    cat = parts[1].strip()
                    content = parts[2].strip()
                    return content, cat
    except Exception:
        pass
    return None


# ==========================================
# AUTENTICAÇÃO E ESTADO
# ==========================================
def check_access_password() -> bool:
    required_password = get_secret("EGO_ACCESS_PASSWORD")
    if not required_password:
        return True
    if st.session_state.get("authenticated", False):
        return True

    st.title("🔒 Acesso Restrito — EGO.exe")
    with st.form("login_form"):
        typed_password = st.text_input("Senha de acesso", type="password")
        if st.form_submit_button("Entrar"):
            if typed_password == required_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    return False


def initialize_state() -> None:
    if "profile_loaded" not in st.session_state:
        db_profile, err_msg = load_profile_from_supabase()
        if db_profile is not None and db_profile.strip():
            st.session_state["profile_input"] = db_profile
            st.session_state["saved_profile"] = db_profile
            st.session_state["profile_source"] = "supabase"
        else:
            st.session_state["profile_input"] = DEFAULT_PROFILE_PLACEHOLDER
            st.session_state["saved_profile"] = ""
            st.session_state["profile_source"] = "placeholder"

        st.session_state["supabase_load_error"] = err_msg
        st.session_state["profile_loaded"] = True


def main() -> None:
    if not check_access_password():
        return

    initialize_state()

    gemini_api_key = get_secret("GEMINI_API_KEY")
    gemini_model = get_secret("GEMINI_MODEL", default="gemini-3.5-flash-lite")

    memories = get_memories_from_supabase()

    # ------------------------------------------
    # BARRA LATERAL
    # ------------------------------------------
    with st.sidebar:
        st.subheader("Configuração")
        if gemini_api_key:
            st.success("Chave da API carregada dos Secrets.")
        else:
            gemini_api_key = st.text_input("Chave da API do Gemini", type="password").strip()

        if st.session_state.get("supabase_load_error"):
            st.warning(st.session_state["supabase_load_error"])

        st.text_area(
            "Perfil / instruções do EGO",
            key="profile_input",
            height=240,
        )

        if st.button("Salvar perfil", use_container_width=True, type="primary"):
            current_text = st.session_state.get("profile_input", "")
            ok, feedback_msg = save_profile_to_supabase(current_text)
            if ok:
                st.session_state["saved_profile"] = current_text
                st.success(feedback_msg)
            else:
                st.error(feedback_msg)

        st.divider()

        st.subheader("Memórias & Estilo")
        new_mem = st.text_area("Adicionar ideia ou gíria", key="new_mem_input", height=80)
        mem_cat = st.selectbox("Categoria", ["estilo_escrita", "ideia", "pensamento_critico", "conhecimento", "geral"])

        if st.button("Guardar na nuvem", use_container_width=True):
            if add_memory_to_supabase(new_mem, mem_cat):
                st.success("Guardado na nuvem!")
                st.rerun()
            else:
                st.warning("Escreva algo para guardar.")

        st.caption(f"{len(memories)} itens guardados no Supabase")

        if memories:
            with st.expander("Ver / gerenciar itens"):
                for m in memories:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"• **[{m.get('category','geral').upper()}]** {m['content']}")
                    if c2.button("🗑️", key=f"del_mem_{m['id']}"):
                        delete_memory_from_supabase(m["id"])
                        st.rerun()
                if st.button("Apagar tudo", use_container_width=True):
                    clear_all_memories_supabase()
                    st.rerun()

        st.divider()

        if st.button("Apagar histórico de conversa", use_container_width=True):
            clear_chat_history_supabase()
            st.rerun()

    # ------------------------------------------
    # ÁREA PRINCIPAL (CHAT)
    # ------------------------------------------
    st.title("🧠 EGO.exe")
    st.caption("Assistente dinâmico com espelhamento de estilo de escrita na nuvem.")

    chat_history = get_chat_history_supabase()

    for msg in chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Converse com o EGO.exe...")

    if user_prompt:
        if not gemini_api_key:
            st.error("Configure a GEMINI_API_KEY nos Secrets.")
            return

        with st.chat_message("user"):
            st.markdown(user_prompt)
        save_chat_message_supabase("user", user_prompt)
        chat_history.append({"role": "user", "content": user_prompt})

        # Detecção automática de estilo de escrita, gírias ou ideias
        learned_item = auto_detect_and_save_knowledge(gemini_api_key, user_prompt)
        if learned_item:
            content_learned, cat_learned = learned_item
            add_memory_to_supabase(content_learned, cat_learned)
            st.toast(f"✍️ EGO capturou ({cat_learned}): {content_learned}", icon="🧠")
            memories = get_memories_from_supabase()

        active_profile = st.session_state.get("profile_input", "")
        system_instruction = build_system_instruction(active_profile, memories)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                reply = call_gemini_api(
                    api_key=gemini_api_key,
                    preferred_model=gemini_model,
                    system_instruction=system_instruction,
                    chat_history=chat_history,
                )
                st.markdown(reply)

        save_chat_message_supabase("assistant", reply)


if __name__ == "__main__":
    main()
