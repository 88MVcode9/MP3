# Music Downloader (site)

Site simples (Flask) que reaproveita a lógica do projeto
[Music-Downloader](https://github.com/tarcisio-marinho/Music-Downloader),
atualizado para usar `yt-dlp` + `ffmpeg` em vez das dependências antigas
(`youtube-dl` 2017 e `libav-tools`).

## Instalação

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
