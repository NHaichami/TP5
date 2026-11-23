import io
import unittest
from contextlib import redirect_stdout

from compte_bancaire import (
    CompteBancaire,
    MontantNegatifException,
    SoldeInsuffisantException,
    TransactionException,
)


class TestHierarchieExceptions(unittest.TestCase):
    def test_hierarchie(self) -> None:
        self.assertTrue(issubclass(SoldeInsuffisantException, TransactionException))
        self.assertTrue(issubclass(MontantNegatifException, TransactionException))
        self.assertTrue(issubclass(TransactionException, Exception))

    def test_message_conserve(self) -> None:
        erreur = SoldeInsuffisantException("message de test")
        self.assertEqual(str(erreur), "message de test")


class TestCreation(unittest.TestCase):
    def test_solde_par_defaut(self) -> None:
        self.assertEqual(CompteBancaire("Alice").solde, 0)

    def test_solde_initial(self) -> None:
        compte = CompteBancaire("Alice", 100)
        self.assertEqual(compte.nom, "Alice")
        self.assertEqual(compte.solde, 100)

    def test_solde_initial_negatif(self) -> None:
        with self.assertRaises(MontantNegatifException):
            CompteBancaire("Alice", -10)


class TestDepot(unittest.TestCase):
    def setUp(self) -> None:
        self.compte = CompteBancaire("Alice", 100)

    def test_depot_valide(self) -> None:
        self.compte.deposer(50)
        self.assertEqual(self.compte.solde, 150)

    def test_depot_negatif(self) -> None:
        with self.assertRaises(MontantNegatifException):
            self.compte.deposer(-20)
        self.assertEqual(self.compte.solde, 100)

    def test_depot_nul(self) -> None:
        with self.assertRaises(MontantNegatifException):
            self.compte.deposer(0)


class TestRetrait(unittest.TestCase):
    def setUp(self) -> None:
        self.compte = CompteBancaire("Alice", 100)

    def test_retrait_valide(self) -> None:
        self.compte.retirer(40)
        self.assertEqual(self.compte.solde, 60)

    def test_retrait_du_solde_exact(self) -> None:
        self.compte.retirer(100)
        self.assertEqual(self.compte.solde, 0)

    def test_retrait_superieur_au_solde(self) -> None:
        with self.assertRaises(SoldeInsuffisantException) as contexte:
            self.compte.retirer(150)
        self.assertEqual(str(contexte.exception), "Solde insuffisant pour ce retrait.")
        self.assertEqual(self.compte.solde, 100)

    def test_retrait_negatif(self) -> None:
        with self.assertRaises(MontantNegatifException):
            self.compte.retirer(-5)

    def test_exception_capturable_via_la_base(self) -> None:
        with self.assertRaises(TransactionException):
            self.compte.retirer(150)


class TestAffichage(unittest.TestCase):
    def test_afficher(self) -> None:
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            CompteBancaire("Alice", 100).afficher()
        self.assertEqual(sortie.getvalue().strip(), "Compte: Alice, Solde: 100€")


class TestJournalisation(unittest.TestCase):
    def test_erreur_solde_journalisee(self) -> None:
        compte = CompteBancaire("Alice", 100)
        with self.assertLogs("compte_bancaire", level="ERROR") as journal:
            with self.assertRaises(SoldeInsuffisantException):
                compte.retirer(150)
        self.assertIn("SoldeInsuffisantException", journal.output[0])

    def test_erreur_montant_journalisee(self) -> None:
        compte = CompteBancaire("Alice", 100)
        with self.assertLogs("compte_bancaire", level="ERROR") as journal:
            with self.assertRaises(MontantNegatifException):
                compte.deposer(-1)
        self.assertIn("MontantNegatifException", journal.output[0])


if __name__ == "__main__":
    unittest.main()