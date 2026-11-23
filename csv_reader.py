import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

SEPARATEUR = ";"
NB_COLONNES = 3


class CsvException(Exception):
    """Exception de base pour toutes les erreurs d'import CSV."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class FichierIntrouvableException(CsvException):
    """Levée lorsque le fichier CSV n'existe pas."""

    def __init__(self, chemin: str | Path) -> None:
        super().__init__(f"Fichier introuvable : {chemin}")
        self.chemin = str(chemin)


class LigneInvalideException(CsvException):
    """Levée lorsqu'une ligne a un mauvais format (colonnes, champs vides, prix non numérique)."""

    def __init__(self, numero_ligne: int, raison: str) -> None:
        super().__init__(f"Ligne {numero_ligne} invalide : {raison}")
        self.numero_ligne = numero_ligne
        self.raison = raison


class PrixNegatifException(CsvException):
    """Levée lorsque le prix n'est pas strictement positif."""

    def __init__(self, numero_ligne: int, prix: str) -> None:
        super().__init__(
            f"Ligne {numero_ligne} : le prix doit être strictement positif (reçu : {prix})."
        )
        self.numero_ligne = numero_ligne
        self.prix = prix


def _journaliser(erreur: CsvException) -> None:
    """Trace une anomalie dans le journal."""
    logger.error("%s : %s", type(erreur).__name__, erreur)


def _analyser_ligne(numero_ligne: int, ligne: str) -> dict:
    """Valide une ligne `id;nom;prix` et la convertit en dictionnaire."""
    colonnes = [colonne.strip() for colonne in ligne.split(SEPARATEUR)]
    if len(colonnes) != NB_COLONNES:
        raise LigneInvalideException(
            numero_ligne, f"{NB_COLONNES} colonnes attendues, {len(colonnes)} trouvées."
        )

    identifiant, nom, texte_prix = colonnes
    if not identifiant or not nom:
        raise LigneInvalideException(numero_ligne, "l'identifiant et le nom sont obligatoires.")

    try:
        prix = float(texte_prix)
    except ValueError:
        raise LigneInvalideException(
            numero_ligne, f"prix non numérique ({texte_prix!r})."
        ) from None
    if not math.isfinite(prix):
        raise LigneInvalideException(numero_ligne, f"prix non numérique ({texte_prix!r}).")
    if prix <= 0:
        raise PrixNegatifException(numero_ligne, texte_prix)

    return {"id": identifiant, "nom": nom, "prix": prix}


def charger_csv(chemin: str | Path) -> list[dict]:
    """Charge un CSV `id;nom;prix` et retourne la liste des articles.

    Les lignes vides sont ignorées. Lève une exception dérivée de `CsvException`
    pour tout fichier introuvable ou toute ligne invalide.
    """
    fichier = Path(chemin)
    if not fichier.is_file():
        erreur = FichierIntrouvableException(chemin)
        _journaliser(erreur)
        raise erreur

    articles = []
    lignes = fichier.read_text(encoding="utf-8-sig").splitlines()
    for numero_ligne, ligne in enumerate(lignes, start=1):
        if not ligne.strip():
            continue
        try:
            articles.append(_analyser_ligne(numero_ligne, ligne))
        except CsvException as erreur:
            _journaliser(erreur)
            raise
    return articles