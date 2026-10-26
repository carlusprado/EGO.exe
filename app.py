import os
import sqlite3
from pathlib import Path

import requests
import streamlit as st

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "ego_memory.db"

st.set_page_config(page_title="EGO.exe", page_icon="🧠", layout="wide")


def secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )""")


def get_rows(table):
    with sqlite3.connect(DB) as con:
        return con.execute(f"SELECT id, content FROM {table} ORDER BY id").fetchall()


def save_message(role, content):
    with sqlite3.connect(DB) as con:
        con.execute("INSERT INTO messages(role, content) VALUES (?, ?)", (role, content))


def save_memory(content):
    if content.strip():
        with sqlite3.connect(DB) as con:
            con.execute("INSERT INTO memories(content) VALUES (?)", (content.strip(),))


def ask_gemini(messages, api_key, model):
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in messages if m["role"] != "system"
    ]
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2048},
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    answer = "\n".join(part.get("text", "") for part in parts if part.get("text"))
    if not answer:
        raise ValueError("O Gemini não retornou texto. Confira o modelo e a chave da API.")
    return answer


init_db()

# Optional basic password gate. Set EGO_ACCESS_PASSWORD in Streamlit Secrets.
access_password = secret("EGO_ACCESS_PASSWORD")
if access_password and not st.session_state.get("authenticated", False):
    st.title("🧠 EGO.exe")
    typed = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar", type="primary"):
        if typed == access_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

st.title("🧠 EGO.exe")
st.caption("Protótipo de assistente com perfil configurável e memória manual.")
st.info("Versão limpa para publicação: não inclui suas conversas, banco de memórias ou perfil pessoal original.")

api_key = secret("GEMINI_API_KEY")
model = secret("GEMINI_MODEL", "gemini-2.5-flash")

with st.sidebar:
    st.header("Configuração")
    st.caption("O motor online usa a API do Google Gemini.")
    if api_key:
        st.success("Chave da API carregada dos Secrets.")
    else:
        st.warning("Adicione GEMINI_API_KEY em Settings → Secrets na hospedagem.")
    profile = st.text_area(
        "Perfil / instruções do EGO",
        value=st.session_state.get(
            "profile",
            "Fale em português brasileiro natural. Não invente fatos sobre o usuário. "
            "Use as memórias registradas quando forem relevantes. Não afirme ter consciência "
            "ou ser uma cópia literal de uma pessoa."
        ),
        height=180,
    )
    st.session_state["profile"] = profile

    st.divider()
    st.subheader("Memórias")
    new_memory = st.text_area("Adicionar uma memória", key="new_memory")
    if st.button("Guardar memória"):
        save_memory(new_memory)
        st.session_state["new_memory"] = ""
        st.rerun()

    memories = get_rows("memories")
    st.caption(f"{len(memories)} memórias guardadas nesta instância")
    for memory_id, content in memories:
        with st.expander(f"Memória #{memory_id}"):
            st.write(content)
            if st.button("Apagar", key=f"delete_{memory_id}"):
                with sqlite3.connect(DB) as con:
                    con.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                st.rerun()

    if st.button("Apagar histórico de conversa"):
        with sqlite3.connect(DB) as con:
            con.execute("DELETE FROM messages")
        st.rerun()

for role, content in [(r, c) for _, r, c in []]:
    pass

with sqlite3.connect(DB) as con:
    history = con.execute("SELECT role, content FROM messages ORDER BY id").fetchall()

for role, content in history:
    with st.chat_message(role):
        st.markdown(content)

prompt = st.chat_input("Converse com o EGO.exe...")
if prompt:
    save_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    memory_text = "\n".join(f"- {content}" for _, content in get_rows("memories"))
    system_text = profile + "\n\nMemórias registradas:\n" + (memory_text or "- Nenhuma memória registrada.")
    with sqlite3.connect(DB) as con:
        recent = con.execute(
            "SELECT role, content FROM messages ORDER BY id DESC LIMIT 12"
        ).fetchall()
    recent.reverse()
    messages = [{"role": "system", "content": system_text}]
    messages.extend({"role": role, "content": content} for role, content in recent)

    with st.chat_message("assistant"):
        if not api_key:
            answer = "O app ainda não tem chave configurada. Adicione GEMINI_API_KEY em Settings → Secrets."
        else:
            with st.spinner("Pensando..."):
                try:
                    answer = ask_gemini(messages, api_key, model)
                except requests.HTTPError as exc:
                    answer = f"Erro HTTP ao chamar o Gemini: {exc}. Confira a chave, o modelo e os limites da API."
                except Exception as exc:
                    answer = f"Não consegui obter resposta: {type(exc).__name__}: {exc}"
        st.markdown(answer)
    save_message("assistant", answer)
