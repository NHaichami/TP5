import io
import unittest
from unittest.mock import patch

from reservation import (
    CapaciteDepasseeException,
    Evenement,
    NombreInvalideException,
    NomClientInvalideException,
    ReservationException,
    ReservationIntrouvableException,
)


class TestAvecSortie(unittest.TestCase):
    """Capture la sortie standard pour garder la console des tests propre."""

    def setUp(self) -> None:
        self.sortie = io.StringIO()
        patcher = patch("sys.stdout", self.sortie)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestHierarchie(unittest.TestCase):
    def test_hierarchie(self) -> None:
        for classe in (
            CapaciteDepasseeException,
            NombreInvalideException,
            NomClientInvalideException,
            ReservationIntrouvableException,
        ):
            self.assertTrue(issubclass(classe, ReservationException))
        self.assertTrue(issubclass(ReservationException, Exception))

    def test_message_conserve(self) -> None:
        self.assertEqual(str(ReservationException("test")), "test")


class TestCreation(unittest.TestCase):
    def test_creation(self) -> None:
        event = Evenement("Concert", 5)
        self.assertEqual(event.nom, "Concert")
        self.assertEqual(event.capacite, 5)
        self.assertEqual(event.places_reservees, 0)

    def test_capacite_invalide(self) -> None:
        for capacite in (0, -3):
            with self.assertRaises(NombreInvalideException):
                Evenement("Concert", capacite)


class TestValidation(TestAvecSortie):
    def setUp(self) -> None:
        super().setUp()
        self.event = Evenement("Concert", 5)

    def test_nom_vide(self) -> None:
        with self.assertRaises(NomClientInvalideException) as contexte:
            self.event.reserver("", 2)
        self.assertEqual(str(contexte.exception), "Nom du client requis.")

    def test_nom_espaces(self) -> None:
        with self.assertRaises(NomClientInvalideException):
            self.event.reserver("   ", 2)

    def test_nombre_invalide(self) -> None:
        for nb in (0, -1):
            with self.assertRaises(NombreInvalideException):
                self.event.reserver("Alice", nb)

    def test_nom_verifie_avant_nombre(self) -> None:
        with self.assertRaises(NomClientInvalideException):
            self.event.reserver("", 0)

    def test_aucune_place_prise_apres_erreur(self) -> None:
        with self.assertRaises(ReservationException):
            self.event.reserver("", 2)
        self.assertEqual(self.event.places_reservees, 0)


class TestReservation(TestAvecSortie):
    def setUp(self) -> None:
        super().setUp()
        self.event = Evenement("Concert", 5)

    def test_reservation_valide(self) -> None:
        self.event.reserver("Alice", 2)
        self.assertEqual(self.event.places_reservees, 2)
        self.assertEqual(self.event.places_restantes, 3)

    def test_capacite_exacte(self) -> None:
        self.event.reserver("Alice", 5)
        self.assertEqual(self.event.places_reservees, 5)

    def test_capacite_depassee(self) -> None:
        with self.assertRaises(CapaciteDepasseeException) as contexte:
            self.event.reserver("Alice", 6)
        self.assertEqual(str(contexte.exception), "Capacité dépassée.")
        self.assertEqual(self.event.places_reservees, 0)

    def test_capacite_depassee_par_cumul(self) -> None:
        self.event.reserver("Alice", 3)
        with self.assertRaises(CapaciteDepasseeException):
            self.event.reserver("Bob", 3)
        self.assertEqual(self.event.places_reservees, 3)

    def test_message_de_confirmation(self) -> None:
        self.event.reserver("Alice", 2)
        self.assertIn("Réservation confirmée pour Alice (2 places)", self.sortie.getvalue())

    def test_afficher(self) -> None:
        self.event.reserver("Alice", 2)
        self.sortie.truncate(0)
        self.sortie.seek(0)
        self.event.afficher()
        self.assertEqual(
            self.sortie.getvalue().strip(),
            "Événement: Concert — 2/5 places réservées",
        )


class TestIdentifiants(TestAvecSortie):
    def test_identifiants_uniques(self) -> None:
        event = Evenement("Concert", 10)
        premiere = event.reserver("Alice", 1)
        seconde = event.reserver("Bob", 1)
        self.assertEqual(premiere.identifiant, 1)
        self.assertNotEqual(premiere.identifiant, seconde.identifiant)


class TestFileAttente(TestAvecSortie):
    def setUp(self) -> None:
        super().setUp()
        self.event = Evenement("Concert", 5, file_attente_active=True)

    def test_mise_en_file_attente(self) -> None:
        self.event.reserver("Alice", 4)
        with self.assertRaises(CapaciteDepasseeException) as contexte:
            self.event.reserver("Bob", 3)
        self.assertIn("file d'attente", str(contexte.exception))
        self.assertEqual(len(self.event.file_attente), 1)
        self.assertEqual(self.event.places_reservees, 4)

    def test_pas_de_file_si_desactivee(self) -> None:
        event = Evenement("Concert", 2)
        with self.assertRaises(CapaciteDepasseeException):
            event.reserver("Alice", 3)
        self.assertEqual(len(event.file_attente), 0)

    def test_annulation_fait_avancer_la_file(self) -> None:
        alice = self.event.reserver("Alice", 4)
        with self.assertRaises(CapaciteDepasseeException):
            self.event.reserver("Bob", 3)
        self.event.annuler(alice.identifiant)
        self.assertEqual(self.event.places_reservees, 3)
        self.assertEqual(len(self.event.file_attente), 0)

    def test_ordre_darrivee_respecte(self) -> None:
        alice = self.event.reserver("Alice", 4)
        with self.assertRaises(CapaciteDepasseeException):
            self.event.reserver("Bob", 3)
        with self.assertRaises(CapaciteDepasseeException):
            self.event.reserver("Carole", 1)  # rentrerait, mais Bob est avant elle
        self.assertEqual(len(self.event.file_attente), 2)
        self.event.annuler(alice.identifiant)
        self.assertEqual(self.event.places_reservees, 4)

    def test_annulation_dune_reservation_en_attente(self) -> None:
        self.event.reserver("Alice", 4)
        with self.assertRaises(CapaciteDepasseeException):
            self.event.reserver("Bob", 3)
        en_attente = self.event.file_attente[0]
        self.event.annuler(en_attente.identifiant)
        self.assertEqual(len(self.event.file_attente), 0)


class TestAnnulation(TestAvecSortie):
    def test_annuler_libere_les_places(self) -> None:
        event = Evenement("Concert", 5)
        reservation = event.reserver("Alice", 3)
        event.annuler(reservation.identifiant)
        self.assertEqual(event.places_reservees, 0)

    def test_annuler_identifiant_inconnu(self) -> None:
        with self.assertRaises(ReservationIntrouvableException):
            Evenement("Concert", 5).annuler(99)


class TestJournalisation(TestAvecSortie):
    def test_reservation_reussie_tracee(self) -> None:
        event = Evenement("Concert", 5)
        with self.assertLogs("reservation", level="INFO") as journal:
            event.reserver("Alice", 2)
        self.assertIn("confirmée", journal.output[0])

    def test_reservation_refusee_tracee(self) -> None:
        event = Evenement("Concert", 5)
        with self.assertLogs("reservation", level="WARNING") as journal:
            with self.assertRaises(NomClientInvalideException):
                event.reserver("", 2)
        self.assertIn("refusée", journal.output[0])


if __name__ == "__main__":
    unittest.main()