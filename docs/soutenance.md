# Questions de soutenance — éléments de réponse

## Data Science

**1. Pourquoi ce problème est-il pertinent ?**
Acquérir un nouveau client coûte nettement plus cher que d'en conserver un. Le marché télécom
est saturé et concurrentiel. Prédire le churn permet de cibler les clients à risque avec des
actions de rétention (offre, appel du service client) **avant** leur départ, et de limiter la
perte de revenu récurrent.

**2. Quelle est la variable cible ?**
`churn` : 1 si le client résilie, 0 sinon. Elle représente 43 % de 1 dans le dataset.

**3. Pourquoi s'agit-il d'une classification ?**
La cible est **catégorielle et binaire** (part / reste), et non une valeur continue. On parle de
classification supervisée, car les exemples d'entraînement sont étiquetés. Le modèle fournit
aussi une probabilité, utile pour prioriser les clients.

**4. Comment avez-vous séparé train et test ?**
Avec `train_test_split`, 80 % pour l'entraînement (1600 lignes) et 20 % pour le test (400),
`random_state=42` pour la reproductibilité et `stratify=y` pour conserver la même proportion de
churn (43 %) dans les deux jeux. Le jeu de test n'est utilisé que pour l'évaluation finale.

**5. Pourquoi avoir choisi Random Forest ?**
C'est la consigne du TP, et le modèle a de bonnes propriétés pour la production :
- il capte les relations non linéaires et les interactions ;
- il est robuste au bruit et aux valeurs aberrantes ;
- il ne nécessite pas de normalisation ;
- il fournit des probabilités et l'importance des variables (explicabilité).

Les résultats montrent toutefois que, **sur ces données**, la régression logistique a une
meilleure ROC-AUC (0,636 contre 0,625). C'est logique, car les données sont générées par une
fonction logistique. Le Random Forest non bridé sur-apprend un peu. `train.py --model` permet de
changer de modèle sans toucher l'API.

## API

**6. Pourquoi transformer le modèle en API ?**
Pour découpler le modèle de ses consommateurs (site web, application mobile, CRM, batch). Toute
application peut l'appeler en HTTP/JSON sans connaître Python ni scikit-learn. On peut alors le
déployer, le mettre à l'échelle, le monitorer et le versionner indépendamment.

**7. Pourquoi utiliser FastAPI ?**
- Performant (ASGI, Starlette).
- Validation automatique des entrées avec Pydantic (erreurs 422 explicites).
- Documentation OpenAPI et Swagger générée automatiquement.
- Typage Python natif.
- Écosystème Python identique à celui du modèle.
- Facile à tester avec `TestClient`.

**8. Quelle différence entre `/health` et `/predict` ?**
`/health` est un endpoint **technique**, léger et sans paramètre. Il indique si le service est
opérationnel (ici, si le modèle est chargé) et sert au load balancer, à Docker (HEALTHCHECK) et
au monitoring. `/predict` est l'endpoint **métier** : il reçoit les données d'un client, exécute
le modèle et renvoie une prédiction.

## Tests

**9. Pourquoi Pytest ?**
C'est le standard Python : syntaxe simple (`assert`), fixtures, marqueurs (`e2e`), paramétrage
et rapports JUnit pour la CI. Il s'intègre avec le `TestClient` de FastAPI.

**10. Pourquoi Selenium ?**
Pour tester l'application **comme un utilisateur réel**, dans un vrai navigateur : affichage,
saisie, clic, appel de l'API par le JavaScript, affichage du résultat. Il détecte les régressions
que les tests d'API ne voient pas (front cassé, mauvais identifiant de champ, erreur JS…).

**11. Quelle différence entre test unitaire, d'intégration et E2E ?**

| | Unitaire | Intégration | E2E |
|---|---|---|---|
| Portée | Une fonction isolée | Plusieurs composants ensemble | Tout le système, via l'interface |
| Exemple ici | `generate()`, `evaluate()` | API + modèle via `TestClient` | Navigateur → UI → API → modèle |
| Vitesse | ms | 10–100 ms | secondes |
| Quantité | beaucoup | moyen | peu |

## Performance

**12. Pourquoi JMeter ?**
Outil open source de référence pour simuler de nombreux utilisateurs concurrents. Il dispose
d'une interface graphique pour concevoir les tests et d'un mode CLI pour les automatiser. Il
produit des rapports HTML (percentiles, débit, erreurs) et sait tester HTTP, JDBC et d'autres
protocoles.

**13. Quelle différence entre test de charge, de stress et d'endurance ?**
- **Charge** : la charge attendue (par exemple 100 utilisateurs). Vérifie que les temps de
  réponse respectent le SLA en conditions normales.
- **Stress** : on augmente au-delà de la capacité (500, puis 1000 utilisateurs) pour trouver le
  **point de rupture** et observer comment le système se dégrade et récupère.
- **Endurance** (*soak*) : charge normale pendant une longue durée (plusieurs heures). Détecte
  les fuites mémoire, la saturation des disques ou des logs et la dégradation progressive.

**14. Que signifie le 95e percentile du temps de réponse ?**
95 % des requêtes ont répondu en un temps inférieur ou égal à cette valeur. Les 5 % restantes
sont plus lentes. C'est plus représentatif de l'expérience réelle que la moyenne, qui masque les
requêtes lentes. Les SLA s'expriment souvent ainsi, par exemple « p95 < 300 ms ».

## DevOps

**15. Pourquoi Git ?**
Historique complet et traçable des changements (qui, quoi, quand, pourquoi), retour à n'importe
quelle version, travail collaboratif en parallèle, revue de code par pull request et
déclenchement de la CI/CD.

**16. Pourquoi utiliser des branches ?**
Pour isoler le travail en cours sans casser la version stable. `main` correspond à la
production, `develop` à l'intégration et `feature/*` à une fonctionnalité. Une fusion n'a lieu
qu'après les tests et la revue.

**17. Pourquoi Docker ?**
Docker empaquette l'application avec ses dépendances exactes (Python, scikit-learn 1.6.1…) dans
une image identique en dev, en CI et en production : fini le « ça marche sur ma machine ». Il
apporte aussi l'isolation, un démarrage rapide, le versionnement des images et une base pour
l'orchestration (Compose, Kubernetes).

**18. Pourquoi la CI/CD ?**
Chaque modification est automatiquement testée et construite (CI), puis livrable ou déployée
(CD). Les régressions sont détectées immédiatement, les livraisons sont fréquentes et fiables et
il n'y a plus d'erreur de manipulation manuelle.

## Observabilité

**19. Quelle différence entre logs et métriques ?**
Les **logs** sont des événements détaillés et horodatés (une prédiction, une erreur avec sa
stack trace). Ils répondent à « que s'est-il passé exactement pour cette requête ? ». Ils sont
volumineux. Les **métriques** sont des valeurs numériques agrégées dans le temps (requêtes/s,
p95, taux d'erreur). Elles répondent à « comment se porte le système ? ». Elles sont légères et
idéales pour les dashboards et les alertes.

**20. Pourquoi ELK ?**
Centraliser les logs de tous les conteneurs et serveurs dans un même endroit :
- Logstash collecte et transforme ;
- Elasticsearch indexe, avec une recherche plein texte rapide ;
- Kibana permet de rechercher et de visualiser.

On peut retrouver une requête par son `request_id`, filtrer les erreurs ou analyser les
prédictions par version de modèle.

**21. Pourquoi Prometheus ?**
Base de données de séries temporelles conçue pour le monitoring. Elle fonctionne en mode *pull*
(elle interroge `/metrics`), dispose d'un langage de requête puissant (PromQL) et d'alertes
intégrées. C'est le standard cloud-native, avec des bibliothèques clientes pour FastAPI.

**22. Pourquoi Grafana ?**
Pour visualiser les métriques dans des dashboards temps réel et partageables, à partir de
multiples sources (Prometheus, Elasticsearch…), avec des alertes et des annotations. C'est
l'interface de supervision de l'équipe d'exploitation.

**23. Que surveilleriez-vous sur une API ML en production ?**
- **Technique** : disponibilité, débit, latence (p50, p95, p99), taux d'erreurs 4xx/5xx,
  CPU/RAM, saturation.
- **Modèle** : distribution des probabilités, part de CHURN prédite, durée d'inférence, version
  servie.
- **Données** : *data drift*, c'est-à-dire l'évolution de la distribution des features
  (ancienneté, montant…) par rapport à l'entraînement, ainsi que les valeurs manquantes ou
  aberrantes.
- **Performance réelle** : une fois le vrai churn connu, quelques semaines plus tard, mesurer
  precision et recall en production.

## MLOps

**24. Comment versionner le modèle ?**
- Version SemVer dans `metadata.json` (avec la date, les métriques, l'empreinte des données et
  la version de scikit-learn).
- Commit Git du code, des données et du modèle, avec un tag `model-v1.0.0`.
- Tag de l'image Docker correspondante.
- Pour aller plus loin : un registre de modèles (MLflow) et DVC pour les données volumineuses.

**25. Que faire si un nouveau modèle est moins performant ?**
Ne pas le déployer. La CI doit comparer ses métriques à celles du modèle en production sur le
même jeu de test et **bloquer** s'il régresse (un garde-fou existe déjà : ROC-AUC > 0,55). S'il
est déjà déployé : rollback immédiat. Ensuite, analyser la cause (données, hyperparamètres) et
valider avec un *shadow deployment* ou un A/B test avant toute promotion.

**26. Comment détecter une dégradation du modèle ?**
- Surveiller la **dérive des entrées** (tests statistiques KS ou PSI sur les features
  journalisées).
- Surveiller la **dérive des sorties** (probabilité moyenne, part de CHURN : panneau Grafana et
  alerte `PredictionDrift`).
- Mesurer la **performance réelle** quand les étiquettes arrivent (precision et recall
  glissants).

Si l'écart dépasse un seuil : alerte, puis réentraînement.

**27. Comment gérer plusieurs versions du modèle ?**
- Chaque version est servie dans sa propre image, avec la version dans `/model/info`, les
  métriques et les logs.
- On peut faire tourner plusieurs versions en parallèle (canary : 10 % du trafic sur v2 ;
  A/B test ; shadow : v2 calcule sans répondre) derrière un reverse proxy.
- On compare ensuite les métriques par label `model_version` dans Grafana et Kibana.

**28. Comment revenir à une ancienne version ?**
- Redéployer l'image Docker taguée précédente (par exemple `ml-churn-api:1.0`) :
  `docker compose up -d` avec l'ancien tag. C'est immédiat, aucune reconstruction n'est
  nécessaire.
- Ou faire un `git revert` / un checkout du tag du modèle précédent, que la CI reconstruit et
  redéploie.

C'est pour cela qu'on ne réécrit jamais une image ou une version existante.
