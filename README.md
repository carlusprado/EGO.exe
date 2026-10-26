# EGO.exe — pacote limpo para publicação

Este pacote não contém chave de API, conversas anteriores, banco de memórias ou perfil pessoal.

## Publicar

1. Crie um repositório **privado** no GitHub e envie os arquivos deste ZIP.
2. Abra https://share.streamlit.io/ e conecte sua conta GitHub.
3. Crie um app usando esse repositório e selecione `app.py`.
4. Em **Settings → Secrets**, adicione:

```toml
GEMINI_API_KEY = "SUA_CHAVE_NOVA"
GEMINI_MODEL = "gemini-2.5-flash"
EGO_ACCESS_PASSWORD = "CRIE_UMA_SENHA_FORTE"
```

Não coloque a chave ou a senha em arquivos do repositório. Se a chave antiga foi compartilhada publicamente ou em um chat, revogue-a e gere outra em https://aistudio.google.com/apikey.

## Atenção

- O app precisa de uma chave da API Gemini; a assinatura do Gemini não é necessariamente a mesma coisa que acesso pago à API.
- A senha é uma barreira simples, não um sistema robusto de autenticação.
- O armazenamento local da hospedagem pode ser temporário. Não trate as memórias como backup permanente.
- Mensagens enviadas ao Gemini são processadas pelo Google.
