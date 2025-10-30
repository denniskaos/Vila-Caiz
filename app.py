"""Entry point da aplicação quando executada com ``python app.py``.

Este ficheiro passa a arrancar o servidor web Flask por omissão para que a
aplicação mostre o painel visual quando é publicada em plataformas como o
Render. A interface de linha de comandos continua disponível através de
``python -m app``.
"""

from app.web import main as run_web


if __name__ == "__main__":
    run_web()
