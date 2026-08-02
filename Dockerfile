FROM python:3.11.9-slim

# Instala o ffmpeg e dependências do sistema necessárias.
# curl/unzip/ca-certificates são necessários só para instalar o Deno logo abaixo.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala o Deno: a partir de 2026 o YouTube exige resolver desafios
# JavaScript, e o yt-dlp precisa de um runtime JS (Deno é o recomendado
# e usado por padrão) para conseguir extrair os formatos de áudio/vídeo.
# Sem isso, o YouTube só libera formatos de imagem/thumbnail e o yt-dlp
# falha com "Requested format is not available".
# Mais detalhes: https://github.com/yt-dlp/yt-dlp/wiki/EJS
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local/deno sh
ENV PATH="/usr/local/deno/bin:${PATH}"

WORKDIR /app

# Copia os arquivos de dependência e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta padrão e roda a aplicação via gunicorn
ENV PORT=5000
EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
