# Punt d'entrada de l'assistent de nivell 3: un xat al terminal.
#
#   python nivell3/main.py                      xat interactiu (escriviu «sortir» per acabar)
#   python nivell3/main.py -p "pregunta"        una sola pregunta
#   python nivell3/main.py --detall             mostra també les eines cridades (per depurar)
#
# Cal haver creat nivell3/.env a partir de nivell3/.env.example (adreça, model i clau del LLM de l'event).
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from agent import Agent  # noqa: E402


def mostra(r: dict, detall: bool = False) -> None:
    """Resposta i fonts (els id_sessio que la demostren). Les eines cridades només es mostren amb --detall."""
    print('\n' + r['resposta'])
    if r['fonts']:
        print(f"\nFonts ({len(r['fonts'])}): {', '.join(r['fonts'][:25])}" + (' …' if len(r['fonts']) > 25 else ''))
    if detall and r['eines']:
        print('Eines: ' + '; '.join(f"{e['eina']}({e['arguments']})" for e in r['eines']))


def main() -> None:
    ap = argparse.ArgumentParser(description="Assistent d'horaris (nivell 3)")
    ap.add_argument('-p', '--pregunta', help='fes una sola pregunta i surt')
    ap.add_argument('--detall', action='store_true', help='mostra també les eines i els arguments (per depurar)')
    a = ap.parse_args()
    falten = config.comprova()
    if falten:
        sys.exit(f"Falta configurar {', '.join(falten)}: copieu nivell3/.env.example com a nivell3/.env i ompliu-lo.")
    agent = Agent()
    if a.pregunta:
        mostra(agent.respon(a.pregunta), a.detall)
        return
    print("Assistent d'horaris de l'Escola d'Enginyeria (1r i 2n semestre). Escriviu «sortir» per acabar.")
    while True:
        try:
            q = input('\n> ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ('sortir', 'exit', 'quit'):
            break
        if q:
            mostra(agent.respon(q), a.detall)


if __name__ == '__main__':
    main()
