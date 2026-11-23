import logging
import sys

from csv_reader import (
    CsvException,
    FichierIntrouvableException,
    LigneInvalideException,
    PrixNegatifException,
    charger_csv,
)

CHEMIN_PAR_DEFAUT = "articles.csv"


def configurer_journal() -> None:
    logging.basicConfig(
        filename="erreurs.log",
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


def main(arguments: list[str]) -> int:
    """Charge le CSV, affiche le résultat ou un message clair. Retourne le code de sortie."""
    chemin = arguments[0] if arguments else CHEMIN_PAR_DEFAUT

    try:
        articles = charger_csv(chemin)
    except FichierIntrouvableException:
        print(f"Erreur : le fichier « {chemin} » est introuvable.")
        return 1
    except PrixNegatifException as erreur:
        print(f"Erreur de prix : {erreur}")
        return 1
    except LigneInvalideException as erreur:
        print(f"Erreur de format : {erreur}")
        return 1
    except CsvException as erreur:
        print(f"Erreur d'import : {erreur}")
        return 1

    print(f"{len(articles)} article(s) chargé(s) :")
    for article in articles:
        print(f"  {article['id']} - {article['nom']} : {article['prix']:.2f} €")
    return 0


if __name__ == "__main__":
    configurer_journal()
    sys.exit(main(sys.argv[1:]))