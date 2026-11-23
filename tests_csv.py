import io
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from csv_reader import (
    CsvException,
    FichierIntrouvableException,
    LigneInvalideException,
    PrixNegatifException,
    charger_csv,
)
from main import main


class CsvTestCase(unittest.TestCase):
    """Fournit un dossier temporaire et une méthode pour y écrire des fichiers CSV."""

    def setUp(self) -> None:
        self._dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self._dossier.cleanup)
        self.dossier = Path(self._dossier.name)

    def ecrire(self, contenu: str, nom: str = "articles.csv") -> Path:
        chemin = self.dossier / nom
        chemin.write_text(contenu, encoding="utf-8")
        return chemin


class TestHierarchie(unittest.TestCase):
    def test_hierarchie(self) -> None:
        for classe in (FichierIntrouvableException, LigneInvalideException, PrixNegatifException):
            self.assertTrue(issubclass(classe, CsvException))
        self.assertTrue(issubclass(CsvException, Exception))


class TestChargementValide(CsvTestCase):
    def test_trois_articles(self) -> None:
        chemin = self.ecrire("1;Clavier;29.90\n2;Souris;15.50\n3;Écran;199.99\n")
        self.assertEqual(
            charger_csv(chemin),
            [
                {"id": "1", "nom": "Clavier", "prix": 29.90},
                {"id": "2", "nom": "Souris", "prix": 15.50},
                {"id": "3", "nom": "Écran", "prix": 199.99},
            ],
        )

    def test_lignes_vides_ignorees(self) -> None:
        chemin = self.ecrire("1;Clavier;29.90\n\n   \n2;Souris;15.50\n")
        self.assertEqual(len(charger_csv(chemin)), 2)

    def test_fichier_vide(self) -> None:
        self.assertEqual(charger_csv(self.ecrire("")), [])

    def test_espaces_autour_des_champs(self) -> None:
        chemin = self.ecrire(" 1 ; Clavier ; 29.90 \n")
        self.assertEqual(charger_csv(chemin), [{"id": "1", "nom": "Clavier", "prix": 29.90}])

    def test_aucun_print_dans_charger_csv(self) -> None:
        chemin = self.ecrire("1;Clavier;29.90\n")
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            charger_csv(chemin)
        self.assertEqual(sortie.getvalue(), "")


class TestFichier(CsvTestCase):
    def test_fichier_absent(self) -> None:
        with self.assertRaises(FichierIntrouvableException):
            charger_csv(self.dossier / "absent.csv")

    def test_dossier_au_lieu_dun_fichier(self) -> None:
        with self.assertRaises(FichierIntrouvableException):
            charger_csv(self.dossier)


class TestLignesInvalides(CsvTestCase):
    def test_prix_texte(self) -> None:
        chemin = self.ecrire("1;Clavier;abc\n")
        with self.assertRaises(LigneInvalideException) as contexte:
            charger_csv(chemin)
        self.assertEqual(contexte.exception.numero_ligne, 1)

    def test_prix_nan(self) -> None:
        with self.assertRaises(LigneInvalideException):
            charger_csv(self.ecrire("1;Clavier;nan\n"))

    def test_colonne_manquante(self) -> None:
        with self.assertRaises(LigneInvalideException):
            charger_csv(self.ecrire("1;Clavier\n"))

    def test_colonne_en_trop(self) -> None:
        with self.assertRaises(LigneInvalideException):
            charger_csv(self.ecrire("1;Clavier;29.90;extra\n"))

    def test_nom_vide(self) -> None:
        with self.assertRaises(LigneInvalideException):
            charger_csv(self.ecrire("1;;29.90\n"))

    def test_numero_de_ligne_compte_les_lignes_vides(self) -> None:
        chemin = self.ecrire("1;Clavier;29.90\n\n2;Souris;abc\n")
        with self.assertRaises(LigneInvalideException) as contexte:
            charger_csv(chemin)
        self.assertEqual(contexte.exception.numero_ligne, 3)


class TestPrix(CsvTestCase):
    def test_prix_negatif(self) -> None:
        with self.assertRaises(PrixNegatifException) as contexte:
            charger_csv(self.ecrire("1;Clavier;-5\n"))
        self.assertEqual(contexte.exception.numero_ligne, 1)

    def test_prix_nul(self) -> None:
        with self.assertRaises(PrixNegatifException):
            charger_csv(self.ecrire("1;Clavier;0\n"))

    def test_prix_est_un_float(self) -> None:
        article = charger_csv(self.ecrire("1;Clavier;10\n"))[0]
        self.assertIsInstance(article["prix"], float)
        self.assertTrue(math.isclose(article["prix"], 10.0))

    def test_exceptions_capturables_via_la_base(self) -> None:
        with self.assertRaises(CsvException):
            charger_csv(self.ecrire("1;Clavier;-5\n"))


class TestJournalisation(CsvTestCase):
    def test_fichier_absent_journalise(self) -> None:
        with self.assertLogs("csv_reader", level="ERROR") as journal:
            with self.assertRaises(FichierIntrouvableException):
                charger_csv(self.dossier / "absent.csv")
        self.assertIn("FichierIntrouvableException", journal.output[0])

    def test_ligne_invalide_journalisee(self) -> None:
        with self.assertLogs("csv_reader", level="ERROR") as journal:
            with self.assertRaises(LigneInvalideException):
                charger_csv(self.ecrire("1;Clavier;abc\n"))
        self.assertIn("LigneInvalideException", journal.output[0])


class TestMain(CsvTestCase):
    def executer(self, chemin: Path) -> tuple[int, str]:
        sortie = io.StringIO()
        with redirect_stdout(sortie):
            code = main([str(chemin)])
        return code, sortie.getvalue()

    def test_succes(self) -> None:
        code, texte = self.executer(self.ecrire("1;Clavier;29.90\n2;Souris;15.50\n"))
        self.assertEqual(code, 0)
        self.assertIn("2 article(s) chargé(s)", texte)
        self.assertIn("Clavier : 29.90 €", texte)

    def test_fichier_introuvable(self) -> None:
        code, texte = self.executer(self.dossier / "absent.csv")
        self.assertEqual(code, 1)
        self.assertIn("introuvable", texte)

    def test_ligne_invalide(self) -> None:
        code, texte = self.executer(self.ecrire("1;Clavier;abc\n"))
        self.assertEqual(code, 1)
        self.assertIn("Erreur de format", texte)

    def test_prix_negatif(self) -> None:
        code, texte = self.executer(self.ecrire("1;Clavier;-5\n"))
        self.assertEqual(code, 1)
        self.assertIn("Erreur de prix", texte)


if __name__ == "__main__":
    unittest.main()