# L'agent de la web: el mateix Agent del terminal, amb un afegit per poder mostrar els avisos a la pantalla.
from agent import Agent


class AgentWeb(Agent):
    """Igual que Agent, però recorda l'últim esborrany d'avís per poder-lo mostrar a la pantalla."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.ultim_avis: dict | None = None

    def executa(self, nom, arguments):
        r = super().executa(nom, arguments)
        if nom == 'esborrany_avis' and isinstance(r, dict) and 'avisos' in r:
            self.ultim_avis = r
        return r
