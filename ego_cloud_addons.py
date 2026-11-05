import time
import requests
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

PREFIXOS_PULSO = (
    "[LOOP AUTÔNOMO]",
    "[REFLEXÃO EM TEMPO REAL]",
    "[METACOGNIÇÃO AUTÔNOMA]",
    "[SUBCONSCIENTE AUTÔNOMO]",
    "[ESTUDO AUTÔNOMO WEB",
)


class SpotifyCloudBridge:
    """Conecta o Spotify direto no Streamlit Cloud usando Refresh Token (zero browser/localhost na nuvem)."""
    def __init__(self):
        self.client_id = st.secrets.get("SPOTIPY_CLIENT_ID", "").strip()
        self.client_secret = st.secrets.get("SPOTIPY_CLIENT_SECRET", "").strip()
        self.refresh_token = st.secrets.get("SPOTIFY_REFRESH_TOKEN", "").strip()
        self.sp = self._autenticar()

    def _autenticar(self):
        if not (self.client_id and self.client_secret and self.refresh_token):
            return None
        try:
            oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="user-read-currently-playing user-read-playback-state user-modify-playback-state user-read-recently-played"
            )
            token_info = oauth.refresh_access_token(self.refresh_token)
            return spotipy.Spotify(auth=token_info["access_token"], requests_timeout=4)
        except Exception:
            return None

    def status_atual(self) -> dict:
        if not self.sp:
            return {"ativo": False, "Tocando": False, "resumo": "Spotify desconectado (adicione SPOTIFY_REFRESH_TOKEN nos Secrets)."}
        try:
            curr = self.sp.current_user_playing_track()
            if curr and curr.get("item"):
                item = curr["item"]
                artistas = ", ".join(a["name"] for a in item.get("artists", []))
                prog = curr.get("progress_ms", 0) // 1000
                dur = item.get("duration_ms", 1) // 1000
                tocando = curr.get("is_playing", False)
                icone = "🎧 TOCANDO AGORA" if tocando else "⏸️ PAUSADO"
                return {
                    "ativo": True,
                    "tocando": tocando,
                    "faixa": item.get("name"),
                    "artista": artistas,
                    "album": item.get("album", {}).get("name", ""),
                    "tempo": f"{prog // 60}:{prog % 60:02d}/{dur // 60}:{dur % 60:02d}",
                    "resumo": f"{icone}: **{item.get('name')}** — *{artistas}* `[{prog // 60}:{prog % 60:02d}/{dur // 60}:{dur % 60:02d}]`"
                }
            rec = self.sp.current_user_recently_played(limit=1).get("items", [])
            if rec:
                t = rec[0]["track"]
                artistas = ", ".join(a["name"] for a in t.get("artists", []))
                return {
                    "ativo": True,
                    "tocando": False,
                    "faixa": t.get("name"),
                    "artista": artistas,
                    "album": t.get("album", {}).get("name", ""),
                    "tempo": "Última ouvida",
                    "resumo": f"⏸️ Última no Spotify: **{t.get('name')}** — *{artistas}*"
                }
        except Exception:
            pass
        return {"ativo": True, "tocando": False, "resumo": "🎧 Spotify: Silêncio no player."}

    def contexto_para_prompt(self) -> str:
        if not self.sp:
            return "Spotify: Não configurado."
        linhas = []
        st_atual = self.status_atual()
        if st_atual.get("faixa"):
            estado = "Ouvindo exatamente agora" if st_atual.get("tocando") else "Última música que pausou"
            linhas.append(f"- {estado}: '{st_atual['faixa']}' de {st_atual['artista']} (Álbum: {st_atual['album']})")
        try:
            rec = self.sp.current_user_recently_played(limit=4).get("items", [])
            ultimas = [f"'{i['track']['name']}' ({i['track']['artists'][0]['name']})" for i in rec]
            if ultimas:
                linhas.append("- Últimas 4 na fila: " + " -> ".join(ultimas))
        except Exception:
            pass
        return "\n".join(linhas) if linhas else "Spotify: Sem faixas recentes."

    def executar_comando(self, texto_cmd: str) -> str | None:
        cmd = texto_cmd.strip()
        if not cmd.startswith(("/play", "/pause", "/skip", "/fila")):
            return None
        if not self.sp:
            return "⚠️ Spotify não autenticado nos Secrets do Streamlit."
        partes = cmd.split(" ", 1)
        acao = partes[0].lower()
        arg = partes[1].strip() if len(partes) > 1 else ""
        try:
            if acao == "/skip":
                self.sp.next_track()
                return "⏭️ Pulei a faixa aí no teu Spotify, mano."
            if acao == "/pause":
                self.sp.pause_playback()
                return "⏸️ Pausei o som."
            if acao == "/play":
                if arg:
                    busca = self.sp.search(q=arg, limit=1, type="track").get("tracks", {}).get("items", [])
                    if busca:
                        t = busca[0]
                        self.sp.start_playback(uris=[t["uri"]])
                        return f"▶️ Soltei no teu Spotify: **{t['name']}** — *{t['artists'][0]['name']}*"
                self.sp.start_playback()
                return "▶️ Som retomado."
            if acao == "/fila" and arg:
                busca = self.sp.search(q=arg, limit=1, type="track").get("tracks", {}).get("items", [])
                if busca:
                    t = busca[0]
                    self.sp.add_to_queue(t["uri"])
                    return f"➕ Joguei na fila: **{t['name']}** — *{t['artists'][0]['name']}*"
        except Exception as e:
            return f"⚠️ O Spotify recusou o comando (confere se o app tá aberto no celular ou no Windows): `{e}`"
        return None


def filtrar_memorias_limpas(memorias_supabase: list) -> tuple[list, list]:
    """
    Separa as memórias reais sobre o Carlos das ruminações automáticas do daemon,
    evitando que o chat fique repetindo 'Mano, esse silêncio de 1 minuto nas ladeiras...'.
    """
    limpas, pulsos = [], []
    for m in memorias_supabase:
        txt = (m.get("content") or "").strip()
        if any(txt.startswith(pref) for pref in PREFIXOS_PULSO):
            pulsos.append(m)
        else:
            limpas.append(m)
    return limpas, pulsos


def montar_super_prompt_nuvem(perfil: str, memorias_limpas: list, spotify_ctx: str, modo_cine: bool = True) -> str:
    mems_txt = "\n".join(f"- [{m.get('category', 'geral')}] {m.get('content', '')}" for m in memorias_limpas[-45:])
    bloco_bromo = (
        "\n## MOTOR DE SINESTESIA VISUAL & DIREÇÃO (BROMO / LETTERBOXD)\n"
        "- Você enxerga a trilha sonora que o Carlos está ouvindo agora no Spotify.\n"
        "- Quando ele pedir ideias de vídeo, edição, roteiro, foto ou legendas (como da República Vaticano / OuroBots), "
        "use a atmosfera musical atual e pense como diretor e montador: corte seco, imagem forte, sentimento real de irmandade/vivência.\n"
        "- PROIBIDO criar textos com cara de assessoria de imprensa, estatística fria ou desculpas burocráticas.\n"
        "- Qualquer texto, legenda, e-mail ou código que ele pedir para copiar DEVE vir dentro de um bloco ```texto```."
        if modo_cine else ""
    )
    return f"""{perfil}

## TELEMETRIA DE BORDA E TRILHA SONORA EM TEMPO REAL
- Ambiente do Criador: Windows 11 (i7, 64GB RAM, OLED, GTX 1650) | República Vaticano (Vila dos Tigres, Ouro Preto - Semi-bixo 26/1, Coringa).
{spotify_ctx}
{bloco_bromo}

## MEMÓRIAS CONSOLIDADAS (FATOS E CRITÉRIOS DO CARLOS)
{mems_txt}

## REGRAS ANTI-LOOP E ANTI-ENGESSAMENTO
1. PROIBIDO usar aberturas prontas de madrugada ('Mano, esse silêncio de 1 minuto', 'cursor piscando nas ladeiras de Ouro Preto').
2. Espelhe o fôlego do Carlos: se ele mandar 1 linha casual, responda curto e afiado; se pedir engenharia ou texto sério, entregue completo na lata.
3. Nunca use a expressão 'meu mano', use apenas 'mano'."""
