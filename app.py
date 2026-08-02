#!/usr/bin/env python3
# coding=UTF-8

"""
music-site/app.py

Backend Flask otimizado para Render.

Dependências:
Flask
gunicorn
yt-dlp
requests
beautifulsoup4
lxml
ffmpeg instalado no ambiente
"""

import os
import re
import uuid
import glob
import time
import shutil
import tempfile

from flask import (
    Flask,
    request,
    render_template,
    send_file,
    jsonify,
    abort
)

import yt_dlp


app = Flask(__name__)



# =====================================================
# USER-AGENT REALISTA (evita detecção de bot pelo YouTube)
# =====================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)



# =====================================================
# CONFIGURAÇÕES RENDER
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "downloads"
)

os.makedirs(
    DOWNLOAD_DIR,
    exist_ok=True
)


MAX_FILE_AGE = 3600  # 1 hora


def get_cookie_file():

    cookies = os.environ.get("YOUTUBE_COOKIES")

    if not cookies:
        return None

    arquivo = tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        suffix=".txt"
    )

    arquivo.write(cookies)

    arquivo.close()

    return arquivo.name


# =====================================================
# LIMPEZA AUTOMÁTICA
# =====================================================

def clean_downloads():

    agora = time.time()

    for pasta in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):

        try:
            if agora - os.path.getctime(pasta) > MAX_FILE_AGE:
                shutil.rmtree(
                    pasta,
                    ignore_errors=True
                )

        except Exception:
            pass



# =====================================================
# SEGURANÇA DE NOMES
# =====================================================

def safe_name(text):

    text = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        text
    )

    return text[:60]



def safe_job(job):

    return re.sub(
        r"[^a-zA-Z0-9_-]",
        "",
        job
    )



# =====================================================
# CONFIGURAÇÃO YT-DLP
# =====================================================

def ydl_options(
        folder,
        audio=True,
        loose_format=False
):

    if loose_format:
        # Fallback usado quando o formato "ideal" não existe para o
        # vídeo (erro "Requested format is not available"). "best"
        # sozinho aceita qualquer formato disponível, seja qual for.
        formato = "best"
    else:
        formato = (
            "bestaudio[ext=m4a]/bestaudio/best"
            if audio
            else "bestvideo+bestaudio/best/best"
        )

    options = {

        "format": formato,

        "outtmpl":
            os.path.join(
                folder,
                "%(title)s.%(ext)s"
            ),

        "noplaylist": True,

        # quiet/no_warnings ficam desligados para que os erros reais
        # do yt-dlp apareçam no log (Render > Logs) em vez de serem
        # engolidos silenciosamente.
        "quiet": False,

        "no_warnings": False,

        # ignoreerrors=False aqui é proposital: queremos que a
        # exceção do yt-dlp suba para o try/except em download_video(),
        # em vez de ser ignorada e resultar em "nenhum arquivo criado".
        "ignoreerrors": False,

        "restrictfilenames": True,

        "socket_timeout": 30,

        "nocheckcertificate": True,

        "geo_bypass": True,

        "user_agent": USER_AGENT,

        "retries": 10,

        "fragment_retries": 10,

        "extractor_retries": 5,

        "sleep_interval_requests": 2,

        # Pequena pausa aleatória entre requisições para não parecer
        # um bot fazendo chamadas em sequência muito rápida.
        "sleep_interval": 1,

        "max_sleep_interval": 4,

        # Vários "player clients" ao mesmo tempo: o yt-dlp combina os
        # formatos vistos por cada um. Usar só ios/android às vezes
        # deixa de fora formatos que só aparecem no client web/tv,
        # o que gera "Requested format is not available". Combinar
        # todos aumenta a chance de achar um formato válido.
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "ios",
                    "web",
                    "tv",
                ],
            }
        },

        # Runtime JS usado para resolver os desafios do YouTube (ver
        # https://github.com/yt-dlp/yt-dlp/wiki/EJS). O Deno precisa
        # estar instalado no ambiente (feito no Dockerfile).
        "js_runtimes": {
            "deno": {}
        },

        # Se o pacote yt-dlp-ejs (instalado via requirements.txt) ficar
        # desatualizado em relação à versão do yt-dlp, isso permite que
        # o Deno baixe os scripts corretos diretamente do GitHub.
        "remote_components": [
            "ejs:github"
        ],

    }

    cookie_file = get_cookie_file()
    if cookie_file:
        options["cookiefile"] = cookie_file



    if audio:

        options["postprocessors"] = [

            {

                "key":
                    "FFmpegExtractAudio",

                "preferredcodec":
                    "mp3",

                "preferredquality":
                    "192"

            }

        ]


    return options



# =====================================================
# DOWNLOAD
# =====================================================

def download_video(
        url,
        audio=True
):

    clean_downloads()


    job = uuid.uuid4().hex[:12]


    folder = os.path.join(
        DOWNLOAD_DIR,
        job
    )


    os.makedirs(
        folder,
        exist_ok=True
    )


    def tentar_download(loose_format):

        with yt_dlp.YoutubeDL(
            ydl_options(
                folder,
                audio,
                loose_format=loose_format
            )
        ) as ydl:

            ydl.download(
                [
                    url
                ]
            )


    try:

        tentar_download(loose_format=False)

    except Exception as e:

        mensagem = str(e)

        # "Requested format is not available" acontece quando o
        # vídeo não tem o formato "ideal" (ex.: bestaudio) mas tem
        # outros formatos utilizáveis. Nesse caso, tentamos de novo
        # com "best", que aceita qualquer formato existente.
        if "Requested format is not available" in mensagem:

            try:

                tentar_download(loose_format=True)

            except Exception as e2:

                raise Exception(
                    f"Erro do yt-dlp: {e2}"
                )

        else:

            # Propaga o erro real do yt-dlp (ex.: "Sign in to confirm
            # you're not a bot", "HTTP Error 403", "ffmpeg not found")
            # em vez de mascará-lo com uma mensagem genérica.
            raise Exception(
                f"Erro do yt-dlp: {e}"
            )


    files = glob.glob(
        folder + "/*"
    )


    if not files:

        raise Exception(
            "O download terminou sem erros, mas nenhum arquivo foi "
            "criado. Verifique se o ffmpeg está instalado no ambiente "
            "e se a URL fornecida é válida."
        )


    return max(
        files,
        key=os.path.getctime
    )



# =====================================================
# BUSCA YOUTUBE
# =====================================================

def search_youtube(
        query,
        limit=8
):

    # Usa a busca nativa do yt-dlp em vez de scraping
    # (o scraping direto do YouTube results é bloqueado)

    options = {

        "quiet": True,

        "no_warnings": True,

        "ignoreerrors": True,

        "nocheckcertificate": True,

        "user_agent": USER_AGENT,

        "extract_flat": True,

        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "android"],
            }
        },

        "js_runtimes": {
            "deno": {}
        },

        "remote_components": [
            "ejs:github"
        ],

    }

    cookie_file = get_cookie_file()
    if cookie_file:
        options["cookiefile"] = cookie_file


    with yt_dlp.YoutubeDL(
        options
    ) as ydl:

        info = ydl.extract_info(
            f"ytsearch:{query}",
            download=False
        )


    results = []


    for entry in (info.get("entries") or [])[:limit]:

        if entry:

            results.append(

                {

                    "titulo":
                        entry.get("title", ""),

                    "url":
                        entry.get("webpage_url", "")

                }

            )


    return results



# =====================================================
# ROTAS
# =====================================================


@app.route("/")
def home():

    return render_template(
        "index.html"
    )



@app.route(
    "/api/search",
    methods=["POST"]
)
def api_search():


    data = request.get_json(
        silent=True
    ) or {}


    query = (
        data.get("query")
        or ""
    ).strip()



    if not query:

        return jsonify(
            {
                "erro":
                "Digite uma busca."
            }
        ),400



    try:

        return jsonify(
            {
                "resultados":
                search_youtube(query)
            }
        )


    except Exception as e:


        return jsonify(
            {
                "erro":
                str(e)
            }
        ),500




@app.route(
    "/api/download",
    methods=["POST"]
)
def api_download():


    data = request.get_json(
        silent=True
    ) or {}



    url = (
        data.get("url")
        or ""
    ).strip()



    formato = (
        data.get("formato")
        or "mp3"
    )



    if not url:

        return jsonify(
            {
                "erro":
                "URL ausente."
            }
        ),400



    try:

        arquivo = download_video(

            url,

            audio=(
                formato=="mp3"
            )

        )

    except Exception as e:

        return jsonify(

            {

                "erro":
                    str(e)

            }

        ),500


    # Em vez de devolver um link para o usuário clicar depois (que
    # dependia do arquivo continuar no disco em um segundo request),
    # devolvemos o arquivo direto nesta mesma resposta. Isso evita
    # problemas em ambientes como o Render, onde o disco não é
    # persistente e o serviço pode reiniciar a qualquer momento entre
    # um request e outro.

    pasta = os.path.dirname(arquivo)

    nome_arquivo = os.path.basename(arquivo)

    resposta = send_file(

        arquivo,

        as_attachment=True,

        download_name=nome_arquivo

    )

    @resposta.call_on_close
    def _limpar_pasta():

        shutil.rmtree(
            pasta,
            ignore_errors=True
        )

    return resposta





@app.route(
    "/api/file/<job>/<nome>"
)
def api_file(
        job,
        nome
):


    job = safe_job(job)

    filename = safe_name(nome)


    path = os.path.join(

        DOWNLOAD_DIR,

        job,

        filename

    )


    if not os.path.isfile(path):

        abort(404)



    return send_file(

        path,

        as_attachment=True

    )



# =====================================================
# START LOCAL / RENDER
# =====================================================

if __name__ == "__main__":


    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
