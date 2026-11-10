import pytest

from optimisation import Camion, Livraison, optimiser

grand_camion = Camion(nom="Camion test", capacites={"congele": 50, "refrigere": 50, "sec": 50})


def carte(nombre_de_livraisons: int) -> tuple[list[list[int]], list[list[int]]]:
    """Petite carte inventée : l'entrepôt (lieu 0) et les livraisons sont alignés,
    avec 1 km et 1 minute entre deux lieux voisins."""
    lieux = range(nombre_de_livraisons + 1)
    metres = [[abs(depart - arrivee) * 1000 for arrivee in lieux] for depart in lieux]
    secondes = [[abs(depart - arrivee) * 60 for arrivee in lieux] for depart in lieux]
    return metres, secondes


def en_secondes(heure: str) -> int:
    heures, minutes = heure.split(":")
    return int(heures) * 3600 + int(minutes) * 60


def livraison(commande_id: int, debut: str = "06:00", fin: str = "18:00", congele: int = 1, urgente: bool = False) -> Livraison:
    return Livraison(
        commande_id=commande_id,
        debut=en_secondes(debut),
        fin=en_secondes(fin),
        caisses={"congele": congele},
        urgente=urgente,
    )


def planifier(livraisons, camions=None, metres=None, secondes=None):
    if metres is None:
        metres, secondes = carte(len(livraisons))
    return optimiser(livraisons, camions or [grand_camion], metres, secondes, millisecondes=300)


def test_visite_les_arrets_dans_le_bon_ordre():
    plan = planifier([livraison(1), livraison(2), livraison(3)])
    assert plan.itineraires[0].commandes in ([1, 2, 3], [3, 2, 1])
    assert plan.itineraires[0].metres == 6000
    assert plan.oubliees == []


def test_respecte_les_plages_de_livraison():
    plan = planifier([livraison(1, debut="10:00", fin="11:00"), livraison(2, debut="06:00", fin="07:00")])
    itineraire = plan.itineraires[0]
    assert itineraire.commandes == [2, 1]
    assert en_secondes("06:00") <= itineraire.arrivees[0] <= en_secondes("07:00")
    assert en_secondes("10:00") <= itineraire.arrivees[1] <= en_secondes("11:00")


def test_un_compartiment_plein_oblige_un_deuxieme_camion():
    petits = [
        Camion(nom="Camion A", capacites={"congele": 5, "refrigere": 50, "sec": 50}),
        Camion(nom="Camion B", capacites={"congele": 5, "refrigere": 50, "sec": 50}),
    ]
    plan = planifier([livraison(1, congele=4), livraison(2, congele=4)], camions=petits)
    assert len(plan.itineraires) == 2
    assert plan.oubliees == []


def test_signale_la_commande_qui_ne_rentre_pas():
    petit = Camion(nom="Camion A", capacites={"congele": 5, "refrigere": 50, "sec": 50})
    plan = planifier([livraison(1, congele=4), livraison(2, congele=4)], camions=[petit])
    assert len(plan.oubliees) == 1
    assert len(plan.itineraires[0].commandes) == 1


def test_signale_une_plage_impossible():
    plan = planifier([livraison(1), livraison(2, debut="04:00", fin="05:00")])
    assert plan.oubliees == [2]


def carte_avec_detour() -> tuple[list[list[int]], list[list[int]]]:
    """Comme carte(3), mais aller de l'entrepôt directement au lieu 3 coûte 5 km au lieu de 3 :
    sans urgence, le camion a intérêt à commencer par le lieu 1."""
    metres, secondes = carte(3)
    metres[0][3] = 5000
    secondes[0][3] = 300
    return metres, secondes


def test_sans_urgence_le_plus_court_d_abord():
    metres, secondes = carte_avec_detour()
    plan = planifier([livraison(1), livraison(2), livraison(3)], metres=metres, secondes=secondes)
    assert plan.itineraires[0].commandes == [1, 2, 3]


def test_la_livraison_urgente_passe_en_premier():
    metres, secondes = carte_avec_detour()
    plan = planifier([livraison(1), livraison(2), livraison(3, urgente=True)], metres=metres, secondes=secondes)
    assert plan.itineraires[0].commandes[0] == 3


def test_refuse_une_matrice_de_la_mauvaise_taille():
    metres, secondes = carte(3)
    with pytest.raises(ValueError):
        optimiser([livraison(1)], [grand_camion], metres, secondes)
