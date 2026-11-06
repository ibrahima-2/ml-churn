const FIELDS = [
  "age",
  "anciennete",
  "revenu",
  "nb_reclamations",
  "montant_mensuel",
  "retards_paiement",
];

const form = document.getElementById("predict-form");
const button = document.getElementById("predict-btn");
const result = document.getElementById("result");
const errorBox = document.getElementById("error");

function showError(message) {
  result.classList.add("hidden");
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function showResult(data) {
  errorBox.classList.add("hidden");
  const isChurn = data.prediction === "CHURN";
  const pct = (data.probability * 100).toFixed(1);

  result.className = "result " + (isChurn ? "churn" : "no-churn");
  document.getElementById("result-label").textContent = data.prediction;
  document.getElementById("result-bar").style.width = pct + "%";
  document.getElementById("result-details").textContent =
    `Probabilité de churn : ${pct} % · modèle v${data.model_version} · ${data.duration_ms} ms`;
}

function formatValidationError(body) {
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((e) => `${e.loc[e.loc.length - 1]} : ${e.msg}`)
      .join(" · ");
  }
  return body.detail || "Erreur inconnue";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {};
  for (const name of FIELDS) {
    const raw = document.getElementById(name).value;
    if (raw === "") {
      showError(`Le champ « ${name} » est obligatoire.`);
      return;
    }
    payload[name] = Number(raw);
  }

  button.disabled = true;
  button.textContent = "Prédiction…";
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      showError(`Erreur ${response.status} : ${formatValidationError(body)}`);
    } else {
      showResult(body);
    }
  } catch (err) {
    showError("API injoignable : " + err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Prédire";
  }
});

fetch("/model/info")
  .then((r) => r.json())
  .then((info) => {
    document.getElementById("model-info").textContent = `${info.model} v${info.version}`;
  })
  .catch(() => {
    document.getElementById("model-info").textContent = "modèle indisponible";
  });
