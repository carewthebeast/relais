from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from pydantic import BaseModel

from catalogue import Compartiment

debut_journee = 6 * 3600
fin_journee = 18 * 3600
secondes_par_arret = 15 * 60
penalite_oubli = 10_000_000
penalite_oubli_urgente = 100_000_000
penalite_retard_urgente = 20


class Livraison(BaseModel):
    commande_id: int
    debut: int
    fin: int
    caisses: dict[Compartiment, int]
    urgente: bool = False


class Camion(BaseModel):
    nom: str
    capacites: dict[Compartiment, int]


class Itineraire(BaseModel):
    camion: str
    commandes: list[int]
    arrivees: list[int]
    depart: int
    retour: int
    metres: int


class Plan(BaseModel):
    itineraires: list[Itineraire]
    oubliees: list[int]


def matrice_des_temps(secondes: list[list[int]]) -> list[list[int]]:
    temps = []
    for depart, ligne in enumerate(secondes):
        arret = 0 if depart == 0 else secondes_par_arret
        temps.append([duree + arret for duree in ligne])
    return temps


def ajouter_compartiments(modele, livraisons: list[Livraison], camions: list[Camion]) -> None:
    for compartiment in Compartiment:
        caisses = [0] + [livraison.caisses.get(compartiment, 0) for livraison in livraisons]
        rappel = modele.RegisterUnaryTransitVector(caisses)
        capacites = [camion.capacites[compartiment] for camion in camions]
        modele.AddDimensionWithVehicleCapacity(rappel, 0, capacites, True, f"caisses_{compartiment}")


def ajouter_horaires(modele, gestionnaire, livraisons: list[Livraison], secondes: list[list[int]]):
    rappel = modele.RegisterTransitMatrix(matrice_des_temps(secondes))
    modele.AddDimension(rappel, fin_journee, fin_journee, False, "temps")
    temps = modele.GetDimensionOrDie("temps")
    for numero, livraison in enumerate(livraisons, start=1):
        index = gestionnaire.NodeToIndex(numero)
        temps.CumulVar(index).SetRange(livraison.debut, livraison.fin)
        if livraison.urgente:
            temps.SetCumulVarSoftUpperBound(index, livraison.debut, penalite_retard_urgente)
        penalite = penalite_oubli_urgente if livraison.urgente else penalite_oubli
        modele.AddDisjunction([index], penalite)
    for camion in range(modele.vehicles()):
        temps.CumulVar(modele.Start(camion)).SetRange(debut_journee, fin_journee)
        modele.AddVariableMinimizedByFinalizer(temps.CumulVar(modele.End(camion)))
        modele.AddVariableMaximizedByFinalizer(temps.CumulVar(modele.Start(camion)))
    return temps


def parametres_de_recherche(millisecondes: int):
    parametres = pywrapcp.DefaultRoutingSearchParameters()
    parametres.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parametres.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    parametres.time_limit.FromMilliseconds(millisecondes)
    return parametres


def suivre_camion(modele, solution, camion: int) -> list[int]:
    index = modele.Start(camion)
    indices = [index]
    while not modele.IsEnd(index):
        index = solution.Value(modele.NextVar(index))
        indices.append(index)
    return indices


def lire_itineraire(modele, gestionnaire, solution, temps, camion: Camion, numero: int, livraisons, metres) -> Itineraire | None:
    indices = suivre_camion(modele, solution, numero)
    lieux = [gestionnaire.IndexToNode(index) for index in indices]
    if len(lieux) == 2:
        return None
    distance = 0
    for depart, arrivee in zip(lieux, lieux[1:]):
        distance += metres[depart][arrivee]
    return Itineraire(
        camion=camion.nom,
        commandes=[livraisons[lieu - 1].commande_id for lieu in lieux[1:-1]],
        arrivees=[solution.Value(temps.CumulVar(index)) for index in indices[1:-1]],
        depart=solution.Value(temps.CumulVar(indices[0])),
        retour=solution.Value(temps.CumulVar(indices[-1])),
        metres=distance,
    )


def rentre(livraison: Livraison, reste: dict[Compartiment, int]) -> bool:
    for compartiment, caisses in livraison.caisses.items():
        if caisses > reste[compartiment]:
            return False
    return True


def repartir_dans_l_ordre(livraisons: list[Livraison], camions: list[Camion]) -> tuple[list[list[int]], list[int]]:
    """Comme sans Relais : on remplit le premier camion dans l'ordre des appels, puis le suivant."""
    tournees = [[] for camion in camions]
    restes = [dict(camion.capacites) for camion in camions]
    oubliees = []
    numero = 0
    for position, livraison in enumerate(livraisons, start=1):
        while numero < len(camions) and not rentre(livraison, restes[numero]):
            numero += 1
        if numero == len(camions):
            oubliees.append(livraison.commande_id)
            continue
        tournees[numero].append(position)
        for compartiment, caisses in livraison.caisses.items():
            restes[numero][compartiment] -= caisses
    return tournees, oubliees


def rouler(camion: Camion, positions: list[int], livraisons: list[Livraison], metres, secondes) -> Itineraire:
    """Calcule les arrivées d'un camion qui suit les arrêts dans l'ordre donné. S'il arrive avant la plage,
    il attend ; s'il arrive après, il livre quand même, en retard."""
    moment = debut_journee
    distance = 0
    lieu = 0
    arrivees = []
    for position in positions:
        moment += secondes[lieu][position]
        distance += metres[lieu][position]
        moment = max(moment, livraisons[position - 1].debut)
        arrivees.append(moment)
        moment += secondes_par_arret
        lieu = position
    return Itineraire(
        camion=camion.nom,
        commandes=[livraisons[position - 1].commande_id for position in positions],
        arrivees=arrivees,
        depart=debut_journee,
        retour=moment + secondes[lieu][0],
        metres=distance + metres[lieu][0],
    )


def suivre_l_ordre_des_appels(livraisons: list[Livraison], camions: list[Camion], metres, secondes) -> Plan:
    tournees, oubliees = repartir_dans_l_ordre(livraisons, camions)
    itineraires = []
    for camion, positions in zip(camions, tournees):
        if positions:
            itineraires.append(rouler(camion, positions, livraisons, metres, secondes))
    return Plan(itineraires=itineraires, oubliees=oubliees)


def optimiser(
    livraisons: list[Livraison],
    camions: list[Camion],
    metres: list[list[int]],
    secondes: list[list[int]],
    millisecondes: int = 500,
) -> Plan:
    if len(metres) != len(livraisons) + 1:
        raise ValueError("La matrice doit avoir une ligne pour l'entrepôt et une par livraison")
    gestionnaire = pywrapcp.RoutingIndexManager(len(metres), len(camions), 0)
    modele = pywrapcp.RoutingModel(gestionnaire)
    modele.SetArcCostEvaluatorOfAllVehicles(modele.RegisterTransitMatrix(metres))
    ajouter_compartiments(modele, livraisons, camions)
    temps = ajouter_horaires(modele, gestionnaire, livraisons, secondes)
    solution = modele.SolveWithParameters(parametres_de_recherche(millisecondes))
    if solution is None:
        return Plan(itineraires=[], oubliees=[livraison.commande_id for livraison in livraisons])
    itineraires = []
    for numero, camion in enumerate(camions):
        itineraire = lire_itineraire(modele, gestionnaire, solution, temps, camion, numero, livraisons, metres)
        if itineraire is not None:
            itineraires.append(itineraire)
    placees = []
    for itineraire in itineraires:
        placees += itineraire.commandes
    oubliees = [livraison.commande_id for livraison in livraisons if livraison.commande_id not in placees]
    return Plan(itineraires=itineraires, oubliees=oubliees)
