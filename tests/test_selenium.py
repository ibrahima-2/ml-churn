"""Tests de bout en bout (E2E) avec Selenium.

Pré-requis : l'API tourne (uvicorn ou docker compose) et Chrome est installé.
    pytest tests/test_selenium.py -v

Variables d'environnement :
    E2E_BASE_URL         URL vue par le navigateur      (défaut http://localhost:8000)
    E2E_HEALTH_URL       URL vue par pytest pour /health (défaut E2E_BASE_URL)
    SELENIUM_REMOTE_URL  Selenium Grid/standalone distant (ex. http://localhost:4444)
    E2E_REQUIRED=1       échoue au lieu d'être ignoré si l'API/Chrome manque (CI)

Corrections par rapport au sujet :
- le titre de /docs est « Churn Prediction API - Swagger UI » (pas « FastAPI ») ;
- Chrome est lancé en mode headless (fonctionne en CI, sans écran) ;
- le scénario complet saisie -> clic « Prédire » -> résultat est testé sur /ui/.
"""
import os
import urllib.request

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000").rstrip("/")
HEALTH_URL = os.getenv("E2E_HEALTH_URL", BASE_URL).rstrip("/")
REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")
REQUIRED = os.getenv("E2E_REQUIRED") == "1"

CLIENT = {
    "age": "35",
    "anciennete": "5",
    "revenu": "450000",
    "nb_reclamations": "2",
    "montant_mensuel": "25000",
    "retards_paiement": "2",
}


def _unavailable(reason: str):
    if REQUIRED:
        pytest.fail(reason)
    pytest.skip(reason)


def _api_is_up() -> bool:
    try:
        with urllib.request.urlopen(f"{HEALTH_URL}/health", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def driver():
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
    except ImportError:
        _unavailable("selenium n'est pas installé (pip install -r requirements-dev.txt)")

    if not _api_is_up():
        _unavailable(f"API non joignable sur {HEALTH_URL} (lancer uvicorn ou docker compose)")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    try:
        drv = webdriver.Remote(REMOTE_URL, options=options) if REMOTE_URL else webdriver.Chrome(options=options)
    except WebDriverException as exc:
        _unavailable(f"Chrome/WebDriver indisponible : {exc.msg}")

    drv.implicitly_wait(2)
    yield drv
    drv.quit()


def _wait(driver):
    from selenium.webdriver.support.ui import WebDriverWait
    return WebDriverWait(driver, 10)


def test_swagger_docs_page(driver):
    driver.get(f"{BASE_URL}/docs")
    assert "Churn Prediction API" in driver.title
    assert "Swagger UI" in driver.title


def test_ui_prediction_scenario(driver):
    """Ouverture -> saisie -> clic Prédire -> appel API -> affichage -> vérification."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    driver.get(f"{BASE_URL}/ui/")
    assert driver.title == "Prédiction du churn"

    for field, value in CLIENT.items():
        element = driver.find_element(By.ID, field)
        element.clear()
        element.send_keys(value)

    driver.find_element(By.ID, "predict-btn").click()

    _wait(driver).until(EC.visibility_of_element_located((By.ID, "result")))
    label = driver.find_element(By.ID, "result-label").text
    details = driver.find_element(By.ID, "result-details").text

    assert label in {"CHURN", "NO_CHURN"}
    assert "Probabilité de churn" in details
    assert "modèle v" in details


def test_ui_shows_validation_error(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    driver.get(f"{BASE_URL}/ui/")
    age = driver.find_element(By.ID, "age")
    age.clear()
    age.send_keys("-5")
    driver.find_element(By.ID, "predict-btn").click()

    _wait(driver).until(EC.visibility_of_element_located((By.ID, "error")))
    assert "422" in driver.find_element(By.ID, "error").text
