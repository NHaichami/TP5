import logging
from collections import deque
from dataclasses import dataclass
from itertools import count

logger = logging.getLogger(__name__)


class ReservationException(Exception):
    """Exception de base pour toutes les erreurs du système de réservation."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CapaciteDepasseeException(ReservationException):
    """Levée lorsqu'une réservation dépasse la capacité maximale."""


class NombreInvalideException(ReservationException):
    """Levée lorsqu'un nombre de places (ou une capacité) est invalide."""


class NomClientInvalideException(ReservationException):
    """Levée lorsque le nom du client est vide."""


class ReservationIntrouvableException(ReservationException):
    """Levée lorsqu'on annule une réservation dont l'identifiant est inconnu."""


@dataclass(frozen=True)
class Reservation:
    """Réservation identifiée de façon unique."""

    identifiant: int
    nom_client: str
    nb_places: int


class Evenement:
    """Événement à capacité limitée, avec journalisation et file d'attente optionnelle."""

    def __init__(self, nom: str, capacite: int, file_attente_active: bool = False) -> None:
        if capacite <= 0:
            raise NombreInvalideException("La capacité doit être strictement positive.")
        self._nom = nom
        self._capacite = capacite
        self._places_reservees = 0
        self._file_attente_active = file_attente_active
        self._reservations: dict[int, Reservation] = {}
        self._file_attente: deque[Reservation] = deque()
        self._compteur = count(1)

    @property
    def nom(self) -> str:
        return self._nom

    @property
    def capacite(self) -> int:
        return self._capacite

    @property
    def places_reservees(self) -> int:
        return self._places_reservees

    @property
    def places_restantes(self) -> int:
        return self._capacite - self._places_reservees

    @property
    def file_attente(self) -> tuple[Reservation, ...]:
        """Réservations en attente, dans l'ordre d'arrivée (lecture seule)."""
        return tuple(self._file_attente)

    @staticmethod
    def _valider(nom_client: str, nb_places: int) -> None:
        if not nom_client.strip():
            raise NomClientInvalideException("Nom du client requis.")
        if nb_places <= 0:
            raise NombreInvalideException("Nombre de places invalide.")

    def _creer_reservation(self, nom_client: str, nb_places: int) -> Reservation:
        return Reservation(next(self._compteur), nom_client.strip(), nb_places)

    def _confirmer(self, reservation: Reservation) -> None:
        self._reservations[reservation.identifiant] = reservation
        self._places_reservees += reservation.nb_places

    def _traiter_reservation(self, nom_client: str, nb_places: int) -> Reservation:
        self._valider(nom_client, nb_places)
        ne_rentre_pas = nb_places > self.places_restantes
        if ne_rentre_pas and not self._file_attente_active:
            raise CapaciteDepasseeException("Capacité dépassée.")

        reservation = self._creer_reservation(nom_client, nb_places)
        # Si une file existe déjà, on s'y place aussi pour respecter l'ordre d'arrivée.
        if ne_rentre_pas or self._file_attente:
            self._file_attente.append(reservation)
            raise CapaciteDepasseeException(
                "Capacité dépassée. "
                f"Réservation placée en file d'attente (n°{reservation.identifiant})."
            )
        self._confirmer(reservation)
        return reservation

    def reserver(self, nom_client: str, nb_places: int) -> Reservation:
        """Réserve des places et trace la tentative (réussie ou non) dans le journal."""
        try:
            reservation = self._traiter_reservation(nom_client, nb_places)
        except ReservationException as erreur:
            logger.warning(
                "Réservation refusée pour %r (%s places) : %s", nom_client, nb_places, erreur
            )
            raise
        logger.info(
            "Réservation n°%d confirmée pour %s (%d places).",
            reservation.identifiant,
            reservation.nom_client,
            reservation.nb_places,
        )
        print(
            f"Réservation confirmée pour {reservation.nom_client} "
            f"({reservation.nb_places} places) - n°{reservation.identifiant}."
        )
        return reservation

    def annuler(self, identifiant: int) -> None:
        """Annule une réservation (confirmée ou en attente) et fait avancer la file."""
        if identifiant in self._reservations:
            reservation = self._reservations.pop(identifiant)
            self._places_reservees -= reservation.nb_places
            logger.info("Réservation n°%d annulée.", identifiant)
            self._promouvoir_file_attente()
            return

        for en_attente in self._file_attente:
            if en_attente.identifiant == identifiant:
                self._file_attente.remove(en_attente)
                logger.info("Réservation en attente n°%d annulée.", identifiant)
                return

        erreur = ReservationIntrouvableException(f"Réservation n°{identifiant} introuvable.")
        logger.warning("Annulation refusée : %s", erreur)
        raise erreur

    def _promouvoir_file_attente(self) -> None:
        """Confirme, dans l'ordre, les réservations en attente qui rentrent maintenant."""
        while self._file_attente and self._file_attente[0].nb_places <= self.places_restantes:
            reservation = self._file_attente.popleft()
            self._confirmer(reservation)
            logger.info("Réservation n°%d confirmée depuis la file d'attente.", reservation.identifiant)
            print(
                f"Réservation de {reservation.nom_client} ({reservation.nb_places} places) "
                f"confirmée depuis la file d'attente - n°{reservation.identifiant}."
            )

    def afficher(self) -> None:
        print(f"Événement: {self._nom} — {self._places_reservees}/{self._capacite} places réservées")


def main() -> None:
    logging.basicConfig(
        filename="reservations.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )

    try:
        event = Evenement("Concert", 5)
        event.reserver("", 2)
    except ReservationException as e:
        print("Erreur:", e)

    # Démonstration des extensions : file d'attente et identifiants uniques.
    event = Evenement("Concert", 5, file_attente_active=True)
    alice = event.reserver("Alice", 3)
    try:
        event.reserver("Bob", 4)
    except CapaciteDepasseeException as e:
        print("Erreur:", e)
    event.afficher()
    event.annuler(alice.identifiant)
    event.afficher()


if __name__ == "__main__":
    main()