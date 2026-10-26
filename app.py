import os
import sqlite3
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

DB_PATH = "ego_local.db"
PROFILE_ROW_KEY = "default"
DEFAULT_PROFILE_PLACEHOLDER = (
    "# Perfil do EGO\n\n"
    "Cole aqui suas instruções completas de perfil e clique em 'Salvar perfil'."
)


# ==========================================
# LEITURA SEGURA DE SECRETS / VARIÁVEIS
# ==========================================
def get_secret(key_name: str, default: str = "") -> str:
    """Obtém uma configuração do st.secrets ou variáveis de ambiente de forma segura."""
    try:
        if key_name in st.secrets and st.secrets[key_name] is not None:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, default).strip()


def get_supabase_credentials() -> Tuple[str, str]:
    """
    Obtém a URL e a chave de servidor do Supabase.
    Aceita SUPABASE_SERVICE_ROLE_KEY (solicitado) ou SUPABASE_SECRET_KEY (novo padrão sb_secret_).
    Bloqueia o uso acidental de chaves públicas (sb_publishable_).
    """
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY") or get_secret("SUPABASE_SECRET_KEY")
    return url, key


# ==========================================
# CLIENTE SUPABASE E PERSISTÊNCIA DO PERFIL
# ==========================================
@st.cache_resource(show_spinner=False)
def init_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    """Inicializa e mantém em cache o cliente do Supabase."""
    return create_client(supabase_url, supabase_key)


def load_profile_from_supabase() -> Tuple[Optional[str], Optional[str]]:
    """
    Carrega o perfil salvo no Supabase.
    Retorna (texto_do_perfil, mensagem_de_erro).
    """
    url, key = get_supabase_credentials()
    if not url or not key:
        return None, (
            "Credenciais do Supabase ausentes nos Secrets "
            "(configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY)."
        )

    if key.startswith("sb_publishable_"):
        return None, (
            "A chave configurada é pública (sb_publishable_...). "
            "Use uma chave privada de servidor (service_role ou sb_secret_...) nos Secrets."
        )

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
        return None, None  # Tabela acessível, mas nenhum perfil salvo ainda
    except Exception:
        return None, (
            "Não foi possível carregar o perfil do Supabase. "
            "Verifique se a tabela 'ego_settings' foi criada e se as credenciais estão corretas."
        )


def save_profile_to_supabase(profile_text: str) -> Tuple[bool, str]:
    """
    Salva o perfil no Supabase sem sobrescrever com texto vazio.
    Retorna (sucesso, mensagem).
    """
    if not profile_text or not profile_text.strip():
        return False, "O perfil está vazio. Digite suas instruções antes de salvar."

    url, key = get_supabase_credentials()
    if not url or not key:
        return False, (
            "Configuração incompleta: defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY nos Secrets."
        )

    if key.startswith("sb_publishable_"):
        return False, (
            "Operação bloqueada: você configurou uma chave pública (sb_publishable_...). "
            "Substitua pela chave de servidor (service_role ou sb_secret_...)."
        )

    try:
        client = init_supabase_client(url, key)
        payload = {
            "profile_key": PROFILE_ROW_KEY,
            "profile_text": profile_text,  # Preserva exatamente quebras de linha, acentos e Markdown
        }
        response = (
            client.table("ego_settings")
            .upsert(payload, on_conflict="profile_key")
            .execute()
        )
        saved_rows = getattr(response, "data", None)
        if saved_rows and len(saved_rows) > 0:
            return True, "Perfil salvo com sucesso no Supabase!"
        return False, "O Supabase não confirmou a gravação do perfil. Verifique as permissões da tabela."
    except Exception:
        return False, (
            "Erro de conexão ou permissão ao salvar no Supabase. "
            "Verifique se a tabela 'ego_settings' existe e se a chave de servidor é válida."
        )


# ==========================================
# BANCO SQLITE LOCAL (HISTÓRICO E MEMÓRIAS)
# ==========================================
def init_local_db() -> None:
    """Inicializa as tabelas locais de memórias e histórico de conversa."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def get_memories() -> List[Tuple[int, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM memories ORDER BY id ASC")
        return cursor.fetchall()


def add_memory(content: str) -> None:
    cleaned = content.strip()
    if not cleaned:
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memories (content) VALUES (?)", (cleaned,))
        conn.commit()


def delete_memory(memory_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()


def clear_all_memories() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()


def get_chat_history() -> List[Dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM messages ORDER BY id ASC")
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


def save_chat_message(role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content),
        )
        conn.commit()


def clear_chat_history() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()


# ==========================================
# INTEGRAÇÃO COM GOOGLE GEMINI API
# ==========================================
def build_system_instruction(profile_text: str, memories: List[Tuple[int, str]]) -> str:
    """Combina o perfil/instruções do EGO com as memórias ativas."""
    parts = []
    if profile_text and profile_text.strip():
        parts.append(profile_text.strip())

    if memories:
        mem_lines = "\n".join(f"- {m[1]}" for m in memories)
        parts.append(f"## Memórias Registradas\nConsidere estas memórias relevantes:\n{mem_lines}")

    return "\n\n".join(parts)


def call_gemini_api(
    api_key: str,
    preferred_model: str,
    system_instruction: str,
    chat_history: List[Dict[str, str]],
) -> str:
    """
    Envia o histórico e a system_instruction ao Gemini com retry e fallback
    para contornar erros HTTP 404 (modelo restrito) e 503 (sobrecarga temporária).
    """
    clean_model = preferred_model.replace("models/", "").strip() or "gemini-3.5-flash-lite"

    # Ordem de tentativa: modelo configurado nos Secrets -> fallbacks estáveis
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
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key.strip(),
    }

    last_status = None
    last_model = clean_model

    for model_name in candidate_models:
        last_model = model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                last_status = response.status_code

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        texts = [p.get("text", "") for p in parts if "text" in p]
                        if texts:
                            return "".join(texts)
                    return "O modelo respondeu sem texto gerado."

                # Sobrecarga temporária (503) ou rate-limit (429): aguarda na 1ª tentativa
                if response.status_code in (429, 503) and attempt == 0:
                    time.sleep(2)
                    continue

                # Se for 404 (modelo indisponível para a chave) ou persistir 503, tenta o próximo modelo
                if response.status_code in (404, 429, 500, 503):
                    break

                # Outros erros (ex: 400, 401, 403) interrompem imediatamente sem expor chaves
                return (
                    f"Erro HTTP {response.status_code} ao chamar o Gemini (modelo '{model_name}'). "
                    "Confira a validade da chave e as permissões da API."
                )
            except requests.exceptions.Timeout:
                if attempt == 0:
                    continue
            except requests.exceptions.RequestException:
                return "Falha de conexão de rede ao comunicar com a API do Google Gemini."

    return (
        f"Erro HTTP {last_status} ao chamar o Gemini (último modelo tentado: '{last_model}'). "
        "Os servidores podem estar temporariamente indisponíveis ou no limite de requisições."
    )


# ==========================================
# CONTROLE DE ACESSO OPCIONAL POR SENHA
# ==========================================
def check_access_password() -> bool:
    """Se EGO_ACCESS_PASSWORD estiver configurado nos Secrets, exige autenticação."""
    required_password = get_secret("EGO_ACCESS_PASSWORD")
    if not required_password:
        return True

    if st.session_state.get("authenticated", False):
        return True

    st.title("🔒 Acesso Restrito — EGO.exe")
    st.caption("Digite a senha configurada em EGO_ACCESS_PASSWORD para acessar o assistente.")

    with st.form("login_form"):
        typed_password = st.text_input("Senha de acesso", type="password")
        submit = st.form_submit_button("Entrar")
        if submit:
            if typed_password == required_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    return False


# ==========================================
# INICIALIZAÇÃO DE ESTADO E APLICAÇÃO
# ==========================================
def initialize_state() -> None:
    """Inicializa o banco SQLite local e carrega o perfil do Supabase uma única vez por sessão."""
    init_local_db()

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

    # ------------------------------------------
    # BARRA LATERAL (SIDEBAR)
    # ------------------------------------------
    with st.sidebar:
        st.subheader("Configuração")
        st.caption("O motor online usa a API do Google Gemini.")

        if gemini_api_key:
            st.success("Chave da API carregada dos Secrets.")
        else:
            gemini_api_key = st.text_input(
                "Chave da API do Gemini",
                type="password",
                help="Configure GEMINI_API_KEY nos Secrets para não precisar digitar aqui.",
            ).strip()

        if st.session_state.get("supabase_load_error"):
            st.warning(st.session_state["supabase_load_error"])

        # Campo de Perfil / Instruções vinculado ao session_state
        st.text_area(
            "Perfil / instruções do EGO",
            key="profile_input",
            height=260,
            help="Este texto é enviado como instrução de sistema ao Gemini em todas as mensagens.",
        )

        # Aviso visual se houver alterações ainda não salvas na nuvem
        if st.session_state.get("profile_input", "") != st.session_state.get("saved_profile", ""):
            st.caption("⚠️ Você tem edições no perfil ainda não salvas no Supabase.")

        if st.button("Salvar perfil", use_container_width=True, type="primary"):
            current_text = st.session_state.get("profile_input", "")
            ok, feedback_msg = save_profile_to_supabase(current_text)
            if ok:
                st.session_state["saved_profile"] = current_text
                st.session_state["profile_source"] = "supabase"
                st.session_state["supabase_load_error"] = None
                st.success(feedback_msg)
            else:
                st.error(feedback_msg)

        st.divider()

        # Seção de Memórias (SQLite local)
        st.subheader("Memórias")
        new_memory_text = st.text_area(
            "Adicionar uma memória",
            key="new_memory_input",
            height=100,
        )

        if st.button("Guardar memória", use_container_width=True):
            if new_memory_text and new_memory_text.strip():
                add_memory(new_memory_text)
                st.success("Memória guardada nesta instância.")
                st.rerun()
            else:
                st.warning("Escreva uma memória antes de guardar.")

        memories = get_memories()
        st.caption(f"{len(memories)} memórias guardadas nesta instância")

        if memories:
            with st.expander("Ver / apagar memórias"):
                for mem_id, mem_content in memories:
                    col_text, col_del = st.columns([4, 1])
                    col_text.write(f"• {mem_content}")
                    if col_del.button("🗑️", key=f"del_mem_{mem_id}", help="Apagar memória"):
                        delete_memory(mem_id)
                        st.rerun()
                if st.button("Apagar todas as memórias", use_container_width=True):
                    clear_all_memories()
                    st.rerun()

        st.divider()

        if st.button("Apagar histórico de conversa", use_container_width=True):
            clear_chat_history()
            st.rerun()

    # ------------------------------------------
    # ÁREA PRINCIPAL (CHAT)
    # ------------------------------------------
    st.title("🧠 EGO.exe")
    st.caption("Protótipo de assistente com perfil configurável e memória manual.")

    if st.session_state.get("profile_source") == "supabase":
        st.info("Perfil carregado com sucesso da nuvem (Supabase) e ativo nas instruções do sistema.")
    else:
        st.info("Versão limpa para publicação: cole seu perfil na barra lateral e clique em 'Salvar perfil'.")

    chat_history = get_chat_history()

    for message in chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input("Converse com o EGO.exe...")

    if user_prompt:
        if not gemini_api_key:
            st.error("Configure a GEMINI_API_KEY nos Secrets antes de enviar mensagens.")
            return

        # 1. Exibe e salva a mensagem do usuário
        with st.chat_message("user"):
            st.markdown(user_prompt)
        save_chat_message("user", user_prompt)
        chat_history.append({"role": "user", "content": user_prompt})

        # 2. Prepara a instrução de sistema usando o perfil ativo + memórias
        active_profile = st.session_state.get("profile_input", "")
        system_instruction = build_system_instruction(active_profile, memories)

        # 3. Chama o Gemini e exibe a resposta
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                reply = call_gemini_api(
                    api_key=gemini_api_key,
                    preferred_model=gemini_model,
                    system_instruction=system_instruction,
                    chat_history=chat_history,
                )
                st.markdown(reply)

        save_chat_message("assistant", reply)


if __name__ == "__main__":
    main()
