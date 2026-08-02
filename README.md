# Music Downloader (site)

Site simples (Flask) que reaproveita a lógica do projeto
[Music-Downloader](https://github.com/tarcisio-marinho/Music-Downloader),
atualizado para usar `yt-dlp` + `ffmpeg` em vez das dependências antigas
(`youtube-dl` 2017 e `libav-tools`).

## Instalação local

```bash
sudo apt update
sudo apt install ffmpeg

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Executar localmente

```bash
python app.py
```

Acesse http://localhost:5000

## Como funciona

- Cole um **link do YouTube** → baixa direto.
- Digite um **nome/trecho de música** → mostra até 8 resultados para escolher.
- Escolha o formato **MP3** (áudio) ou **MP4** (vídeo).

## Deploy no Render (Docker)

O projeto inclui um `Dockerfile` que instala o `ffmpeg` e todas as dependências
Python automaticamente. No painel do Render:

1. Crie um novo **Web Service**.
2. Conecte o repositório do GitHub.
3. Selecione **Docker** como ambiente de build.
4. O `render.yaml` já está configurado para `runtime: docker`.

### ⚠️ Runtime JS (Deno) exigido pelo YouTube

Desde 2026, o YouTube passou a exigir a resolução de desafios JavaScript
para liberar os formatos reais de áudio/vídeo. Sem isso, o yt-dlp só
enxerga formatos de imagem/thumbnail e falha com:

```
ERROR: [youtube] VIDEO_ID: Requested format is not available.
```

Para resolver, o `Dockerfile` já instala o **Deno** (runtime JS recomendado
pelo yt-dlp) e o `requirements.txt` instala `yt-dlp[default]`, que traz o
pacote `yt-dlp-ejs` com os scripts necessários. Isso é feito automaticamente
no build do Docker — não precisa de nenhuma configuração extra.

Se for rodar localmente (fora do Docker), instale o Deno manualmente:
<https://docs.deno.com/runtime/getting_started/installation/>

Mais detalhes técnicos: <https://github.com/yt-dlp/yt-dlp/wiki/EJS>

### Variáveis de ambiente (opcional, mas recomendado)

| Variável           | Descrição                                                                 |
|--------------------|---------------------------------------------------------------------------|
| `YOUTUBE_COOKIES`  | Conteúdo do arquivo de cookies do YouTube (formato `cookies.txt`).      |
| `PORT`             | Porta que o gunicorn escuta (padrão: `5000`).                             |

#### Como obter cookies do YouTube

Para contornar a detecção de bot do YouTube, exporte os cookies do seu navegador:

```bash
# Usando o yt-dlp para exportar cookies (Chrome/Chromium)
yt-dlp --cookies-from-browser chrome --save-cookies cookies.txt

# Ou manualmente: instale a extensão "Get cookies.txt" no navegador,
# acesse youtube.com, exporte os cookies e cole o conteúdo na variável
# YOUTUBE_COOKIES no painel do Render.
```

## Build Docker local

```bash
docker build -t mp3-site .
docker run -p 5000:5000 -e YOUTUBE_COOKIES="..." mp3-site
```

## ⚠️ Importante — uso responsável

Este projeto é uma ferramenta técnica para baixar conteúdo que você
**tem o direito de baixar** (vídeos próprios, domínio público, Creative
Commons, backup pessoal de algo que você já possui, etc).

Disponibilizar publicamente um site assim para que qualquer pessoa baixe
músicas comerciais de terceiros normalmente:

- viola os Termos de Serviço do YouTube; e
- pode infringir direitos autorais, dependendo do conteúdo e da legislação
  aplicável no seu país.

Recomendado: uso pessoal/local, ou uso restrito a conteúdo licenciado/
autorizado. Evite hospedar isso como um serviço público de "baixar músicas".

## Próximos passos possíveis

- Fila de downloads com barra de progresso (WebSocket/SSE)
- Histórico de downloads por usuário
- Deploy com Docker + Nginx + HTTPS (Let's Encrypt)
- Autenticação simples para limitar quem pode usar o site
