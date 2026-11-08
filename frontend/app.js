const FIELDS = [
  "age",
  "anciennete",
  "revenu",
  "nb_reclamations",
  "montant_mensuel",
  "retards_paiement",
];

const PRESETS = {
  // Client du sujet (parties 9 et 10)
  recent: { age: 35, anciennete: 5, revenu: 450000, nb_reclamations: 2, montant_mensuel: 25000, retards_paiement: 2 },
  fidele: { age: 52, anciennete: 110, revenu: 600000, nb_reclamations: 0, montant_mensuel: 15000, retards_paiement: 0 },
};

const THRESHOLD = 0.5;
const HISTORY_SIZE = 6;
const history = [];

const $ = (id) => document.getElementById(id);
const form = $("predict-form");
const button = $("predict-btn");
const result = $("result");
const errorBox = $("error");

const fmtInt = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const fmtPct = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

// ---------------------------------------------------------------- erreurs
function clearFieldErrors() {
  for (const name of FIELDS) {
    $(name).closest(".field").classList.remove("invalid");
    $(name).removeAttribute("aria-invalid");
    $(`${name}-error`).textContent = "";
  }
}

function setFieldError(name, message) {
  if (!FIELDS.includes(name)) return;
  $(name).closest(".field").classList.add("invalid");
  $(name).setAttribute("aria-invalid", "true");
  $(`${name}-error`).textContent = message;
}

function translate(msg) {
  return msg
    .replace(/^Input should be greater than or equal to (\S+)$/, "doit être supérieur ou égal à $1")
    .replace(/^Input should be less than or equal to (\S+)$/, "doit être inférieur ou égal à $1")
    .replace(/^Input should be a valid integer.*$/, "doit être un nombre entier")
    .replace(/^Input should be a valid number.*$/, "doit être un nombre")
    .replace(/^Field required$/, "champ obligatoire");
}

function showError(message) {
  result.classList.add("hidden");
  $("empty-state").classList.add("hidden");
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

// ---------------------------------------------------------------- résultat
function showResult(data, payload, requestId) {
  errorBox.classList.add("hidden");
  $("empty-state").classList.add("hidden");

  const isChurn = data.prediction === "CHURN";
  const pct = data.probability * 100;

  result.className = "result " + (isChurn ? "churn" : "no-churn");
  $("result-proba").textContent = `${fmtPct.format(pct)} %`;
  $("result-label").textContent = data.prediction;
  $("result-verdict").textContent = isChurn
    ? "Risque de départ au-dessus du seuil : client à contacter en priorité."
    : "Risque de départ sous le seuil.";
  $("result-bar").style.width = `${pct}%`;
  $("result-details").textContent =
    `Probabilité de churn : ${fmtPct.format(pct)} % · modèle v${data.model_version} · calcul en ${data.duration_ms} ms`;

  const ref = $("result-ref");
  ref.textContent = requestId ? requestId.slice(0, 8) : "–";
  ref.title = requestId || "";

  addToHistory(data, payload);
}

function addToHistory(data, payload) {
  history.unshift({
    time: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    anciennete: payload.anciennete,
    montant: payload.montant_mensuel,
    incidents: payload.nb_reclamations + payload.retards_paiement,
    probability: data.probability,
    churn: data.prediction === "CHURN",
  });
  history.length = Math.min(history.length, HISTORY_SIZE);

  const body = $("history-body");
  body.replaceChildren(
    ...history.map((h) => {
      const tr = document.createElement("tr");
      const cells = [
        h.time,
        `${h.anciennete} mois`,
        `${fmtInt.format(h.montant)} FCFA`,
        String(h.incidents),
        `${fmtPct.format(h.probability * 100)} %`,
      ];
      cells.forEach((text, i) => {
        const td = document.createElement("td");
        td.textContent = text;
        if (i === cells.length - 1 && h.churn) td.className = "risk";
        tr.appendChild(td);
      });
      return tr;
    })
  );
}

// ---------------------------------------------------------------- envoi
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFieldErrors();

  const payload = {};
  const missing = [];
  for (const name of FIELDS) {
    const raw = $(name).value.trim();
    if (raw === "") missing.push(name);
    else payload[name] = Number(raw);
  }
  if (missing.length) {
    missing.forEach((name) => setFieldError(name, "champ obligatoire"));
    showError("Complétez les champs signalés.");
    $(missing[0]).focus();
    return;
  }

  button.disabled = true;
  button.textContent = "Calcul…";
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (response.ok) {
      showResult(body, payload, response.headers.get("X-Request-ID"));
    } else if (response.status === 422 && Array.isArray(body.detail)) {
      const parts = body.detail.map((e) => {
        const field = e.loc[e.loc.length - 1];
        const msg = translate(e.msg);
        setFieldError(field, msg);
        return `${$(field)?.labels?.[0]?.textContent ?? field} ${msg}`;
      });
      showError(`Erreur 422 : ${parts.join(" ; ")}.`);
    } else {
      showError(`Erreur ${response.status} : ${body.detail || "réponse inattendue de l’API"}.`);
    }
  } catch (err) {
    showError(`API injoignable (${err.message}).`);
  } finally {
    button.disabled = false;
    button.textContent = "Prédire";
  }
});

// ---------------------------------------------------------------- boutons annexes
document.querySelectorAll("[data-preset]").forEach((btn) =>
  btn.addEventListener("click", () => {
    const preset = PRESETS[btn.dataset.preset];
    for (const name of FIELDS) $(name).value = preset[name];
    clearFieldErrors();
    $("age").focus();
  })
);

$("reset-btn").addEventListener("click", () => {
  for (const name of FIELDS) $(name).value = "";
  clearFieldErrors();
  $("age").focus();
});

// ---------------------------------------------------------------- état de l'API
fetch("/model/info")
  .then((r) => r.json())
  .then((info) => {
    $("model-info").textContent = `Modèle : ${info.model} v${info.version}`;
  })
  .catch(() => {
    $("model-info").textContent = "Modèle : indisponible";
  });

fetch("/health")
  .then((r) => {
    const el = $("api-status");
    el.dataset.state = r.ok ? "up" : "down";
    el.textContent = r.ok ? "API disponible" : "API dégradée (modèle absent)";
  })
  .catch(() => {
    const el = $("api-status");
    el.dataset.state = "down";
    el.textContent = "API injoignable";
  });
