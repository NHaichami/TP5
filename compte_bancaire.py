import logging

logger = logging.getLogger(__name__)


class TransactionException(Exception):
    """Exception de base pour toutes les erreurs liées aux transactions financières."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class SoldeInsuffisantException(TransactionException):
    """Levée lorsqu'un retrait dépasse le solde disponible."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class MontantNegatifException(TransactionException):
    """Levée lorsqu'un montant est négatif ou nul."""


class CompteBancaire:
    """Compte bancaire identifié par un nom et possédant un solde."""

    def __init__(self, nom: str, solde: float = 0) -> None:
        if solde < 0:
            raise self._journaliser(
                MontantNegatifException("Le solde initial ne peut pas être négatif.")
            )
        self._nom = nom
        self._solde = solde

    @property
    def nom(self) -> str:
        """Nom du titulaire (lecture seule)."""
        return self._nom

    @property
    def solde(self) -> float:
        """Solde actuel du compte (lecture seule)."""
        return self._solde

    @staticmethod
    def _journaliser(erreur: TransactionException) -> TransactionException:
        """Enregistre l'erreur dans le journal et la retourne pour qu'elle soit levée."""
        logger.error("%s : %s", type(erreur).__name__, erreur)
        return erreur

    def _verifier_montant(self, montant: float) -> None:
        """Vérifie qu'un montant est strictement positif."""
        if montant <= 0:
            raise self._journaliser(
                MontantNegatifException("Le montant doit être strictement positif.")
            )

    def deposer(self, montant: float) -> None:
        """Ajoute un montant strictement positif au solde."""
        self._verifier_montant(montant)
        self._solde += montant
        logger.info("Dépôt de %s € sur le compte de %s.", montant, self._nom)

    def retirer(self, montant: float) -> None:
        """Retire un montant du solde, sans jamais le rendre négatif."""
        self._verifier_montant(montant)
        if montant > self._solde:
            raise self._journaliser(
                SoldeInsuffisantException("Solde insuffisant pour ce retrait.")
            )
        self._solde -= montant
        logger.info("Retrait de %s € sur le compte de %s.", montant, self._nom)

    def afficher(self) -> None:
        """Affiche le nom du titulaire et le solde."""
        print(f"Compte: {self._nom}, Solde: {self._solde}€")


def main() -> None:
    logging.basicConfig(
        filename="comptes.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )

    try:
        compte = CompteBancaire("Alice", 100)
        compte.afficher()
        compte.retirer(150)
    except SoldeInsuffisantException as e:
        print("Erreur:", e)

    try:
        compte.deposer(-20)
    except MontantNegatifException as e:
        print("Erreur:", e)


if __name__ == "__main__":
    main()