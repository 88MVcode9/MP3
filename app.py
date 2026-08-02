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

from flask import (
    Flask,
    request,
    render_template,
    send_file,
    jsonify,
    abort
)

import yt_dlp
import requests
import bs4 as bs


app = Flask(__name__)


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
        audio=True
):

    options = {

        "format":
            "bestaudio/best"
            if audio
            else "bestvideo+bestaudio/best",

        "outtmpl":
            os.path.join(
                folder,
                "%(title)s.%(ext)s"
            ),

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        "ignoreerrors": False,

        "restrictfilenames": True,

        "socket_timeout": 30,

    }


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


    with yt_dlp.YoutubeDL(
        ydl_options(
            folder,
            audio
        )
    ) as ydl:

        ydl.download(
            [
                url
            ]
        )


    files = glob.glob(
        folder + "/*"
    )


    if not files:

        raise Exception(
            "Download concluído sem arquivo."
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

    response = requests.get(

        "https://www.youtube.com/results",

        params={
            "search_query": query
        },

        headers={

            "User-Agent":
            "Mozilla/5.0"

        },

        timeout=15

    )


    soup = bs.BeautifulSoup(
        response.text,
        "lxml"
    )


    results = []


    for item in soup.find_all("a"):


        href = item.get(
            "href",
            ""
        )


        title = item.text.strip()


        if (
            href.startswith("/watch")
            and title
        ):

            results.append(

                {

                    "titulo":
                        title,

                    "url":
                        "https://youtube.com"
                        + href

                }

            )


        if len(results) >= limit:

            break


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


        job = os.path.basename(
            os.path.dirname(
                arquivo
            )
        )


        return jsonify(

            {

                "arquivo":
                    os.path.basename(
                        arquivo
                    ),

                "job":
                    job

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
