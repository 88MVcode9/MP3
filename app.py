#!/usr/bin/env python3
# coding=UTF-8
"""
music-site/app.py

Backend Flask que reaproveita a lógica do projeto Music-Downloader
(originalmente de Tarcisio Marinho), porém modernizado:

  - youtube_dl (2017)  ->  yt-dlp (mantido ativamente)
  - libav-tools        ->  ffmpeg
  - execução via CLI   ->  chamada direta da API do yt-dlp (mais rápido e sem subprocess)

Uso previsto: baixar/converter conteúdo que você tem o direito de baixar
(vídeos próprios, domínio público, licenças Creative Commons, etc).
Não distribua isto publicamente para baixar músicas comerciais de terceiros —
isso normalmente viola os Termos de Serviço do YouTube e pode infringir
direitos autorais.
"""

import os
import re
import uuid
import glob

from flask import Flask, request, render_template, send_file, jsonify, abort
import yt_dlp
import requests
import bs4 as bs

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _slug(s: str) -> str:
    """Gera um nome de pasta seguro para cada job de download."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", s)[:32] or uuid.uuid4().hex[:8]


def _ydl_opts(job_dir: str, audio_only: bool = True) -> dict:
    opts = {
        "format": "bestaudio/best" if audio_only else "best",
        "outtmpl": os.path.join(job_dir, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if audio_only:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    return opts


def download_by_link(url: str, audio_only: bool = True) -> str:
    """Baixa uma única URL e devolve o caminho do arquivo final."""
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    with yt_dlp.YoutubeDL(_ydl_opts(job_dir, audio_only)) as ydl:
        ydl.download([url])

    arquivos = glob.glob(os.path.join(job_dir, "*"))
    if not arquivos:
        raise RuntimeError("Nenhum arquivo foi gerado pelo download.")
    return max(arquivos, key=os.path.getctime)


def search_youtube(query: str, limite: int = 8):
    """Busca resultados no YouTube (equivalente à função busca_musica original)."""
    r = requests.get(
        "https://www.youtube.com/results",
        params={"search_query": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    bs_obj = bs.BeautifulSoup(r.text, "lxml")

    resultados = []
    for h3 in bs_obj.find_all("h3"):
        a = h3.find("a")
        if a and a.get("href", "").startswith("/watch"):
            resultados.append({
                "titulo": h3.text.strip(),
                "url": "https://www.youtube.com" + a.get("href"),
            })
        if len(resultados) >= limite:
            break
    return resultados


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"erro": "Informe um termo de busca."}), 400
    try:
        resultados = search_youtube(query)
    except Exception as e:
        return jsonify({"erro": f"Falha na busca: {e}"}), 500
    return jsonify({"resultados": resultados})


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    formato = data.get("formato", "mp3")  # "mp3" ou "mp4"
    if not url:
        return jsonify({"erro": "URL não informada."}), 400

    try:
        arquivo = download_by_link(url, audio_only=(formato == "mp3"))
    except Exception as e:
        return jsonify({"erro": f"Falha no download: {e}"}), 500

    nome = os.path.basename(arquivo)
    return jsonify({"arquivo": nome, "job": os.path.basename(os.path.dirname(arquivo))})


@app.route("/api/file/<job>/<nome>")
def api_file(job, nome):
    caminho = os.path.join(DOWNLOAD_DIR, _slug(job), nome)
    if not os.path.isfile(caminho):
        abort(404)
    return send_file(caminho, as_attachment=True)


if __name__ == "__main__":
    # debug=False em produção; use um servidor WSGI real (gunicorn) atrás de Nginx
    app.run(host="0.0.0.0", port=5000, debug=True)
