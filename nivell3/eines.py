# Eines (sense IA a dins): funcions que l'agent pot cridar. Cada una es pot provar a mà, retorna dades
# estructurades i les fonts (id_sessio o aules) que demostren la resposta, i diu explícitament quan no troba res.
#
# - consulta_sql: només SELECT, amb límit de files
# - horari_grup: on i quan té classe un grup
# - horari_aula: què passa en una aula
# - aules_lliures: aules prou grans i lliures en una data i hora (avisa de la reserva de 2 aules, regla 8)
# - verifica: crida avalua() del verificador oficial
# - que_passa_si: aplica un canvi en memòria i compara el verificador abans i després
# - resol_imprevist: reutilitza l'eina del 5.3 (nivell2/p53_imprevist)
# - esborrany_avis: redacta (mai no envia) l'avís i l'entrada del registre de canvis
