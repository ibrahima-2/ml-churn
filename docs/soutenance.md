# Questions de soutenance : éléments de réponse

## Data Science

**1. Pourquoi ce problème est-il pertinent ?**
Chaque résiliation fait perdre à l'opérateur un abonnement mensuel. Si l'on sait quels clients
risquent de partir, le service client peut les contacter avant (offre adaptée, réclamation en
attente à régler) au lieu de constater le départ après coup. La probabilité renvoyée par le
modèle sert à décider qui appeler en premier.

**2. Quelle est la variable cible ?**
`churn` : 1 si le client résilie, 0 sinon. Elle représente 43 % de 1 dans le dataset.

**3. Pourquoi s'agit-il d'une classification ?**
La cible est catégorielle et binaire (part / reste), et non une valeur continue. On parle de
classification supervisée, car les exemples d'entraînement sont étiquetés. Le modèle fournit
aussi une probabilité, utile pour prioriser les clients.

**4. Comment avez-vous séparé train et test ?**
Avec `train_test_split`, 80 % pour l'entraînement (1600 lignes) et 20 % pour le test (400),
`random_state=42` pour la reproductibilité et `stratify=y` pour conserver la même proportion de
churn (43 %) dans les deux jeux. Le jeu de test n'est utilisé que pour l'évaluation finale.

**5. Pourquoi avoir choisi Random Forest ?**
C'est la consigne du TP. Le Random Forest a aussi des qualités utiles ici : il capte les
relations non linéaires, tolère le bruit, ne demande pas de mise à l'échelle des variables et
fournit une probabilité ainsi que l'importance de chaque variable.

Sur ces données, il n'est pourtant pas le meilleur : la régression logistique obtient une ROC-AUC
de 0,636 contre 0,625, ce qui est logique puisque le churn a été généré par une fonction
logistique. Le Random Forest, sans limite de profondeur, sur-apprend un peu. L'option
`train.py --model` permet de déployer un autre modèle sans modifier l'API.

## API

**6. Pourquoi transformer le modèle en API ?**
Pour que n'importe quelle application (site web, CRM, traitement par lots) obtienne une
prédiction par une simple requête HTTP, sans embarquer Python ni scikit-learn. Le modèle devient
un service qu'on déploie, surveille et met à jour séparément des applications qui l'utilisent.

**7. Pourquoi utiliser FastAPI ?**
FastAPI valide les entrées à partir des types Pydantic : un âge négatif est rejeté avec une
erreur 422 sans code supplémentaire. Il génère la documentation Swagger à partir du code, il est
rapide et il reste en Python, le langage du modèle. Son `TestClient` permet aussi de tester l'API
sans la lancer.

**8. Quelle différence entre `/health` et `/predict` ?**
`/health` est un endpoint technique, léger et sans paramètre. Il indique si le service est
opérationnel (ici, si le modèle est chargé) et sert au load balancer, à Docker (HEALTHCHECK) et
au monitoring. `/predict` est l'endpoint métier : il reçoit les données d'un client, exécute
le modèle et renvoie une prédiction.

## Tests

**9. Pourquoi Pytest ?**
Pytest est l'outil de test le plus utilisé en Python. Les tests s'écrivent avec de simples
`assert`, un marqueur permet d'écarter les tests E2E (`pytest -m "not e2e"`) et il produit des
rapports JUnit que GitHub Actions archive.

**10. Pourquoi Selenium ?**
Pour tester l'application comme un utilisateur réel, dans un vrai navigateur : affichage,
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
JMeter simule des centaines d'utilisateurs simultanés et mesure les temps de réponse, le débit et
les erreurs. Le plan de test se construit dans une interface graphique puis s'exécute en ligne de
commande, ce qui permet de l'automatiser, et chaque exécution produit un rapport HTML avec les
percentiles.

**13. Quelle différence entre test de charge, de stress et d'endurance ?**
- **Charge** : la charge attendue (par exemple 100 utilisateurs). Vérifie que les temps de
  réponse respectent le SLA en conditions normales.
- **Stress** : on augmente au-delà de la capacité (500, puis 1000 utilisateurs) pour trouver le
  point de rupture et observer comment le système se dégrade et récupère.
- **Endurance** (*soak*) : charge normale pendant une longue durée (plusieurs heures). Détecte
  les fuites mémoire, la saturation des disques ou des logs et la dégradation progressive.

Dans ce projet, le palier de 100 utilisateurs est un test de charge, et ceux de 500 et 1 000
utilisateurs sont des tests de stress : le service sature à ≈ 145 req/s, sans aucune erreur.
Aucun test d'endurance n'a été réalisé.

**14. Que signifie le 95e percentile du temps de réponse ?**
95 % des requêtes ont répondu en un temps inférieur ou égal à cette valeur. Les 5 % restantes
sont plus lentes. C'est plus représentatif de l'expérience réelle que la moyenne, qui masque les
requêtes lentes. Les SLA s'expriment souvent ainsi, par exemple « p95 < 300 ms ».

Mesures du projet : p95 = 11 ms à 100 utilisateurs (sous la capacité), puis 3,5 s à 500 et
7,1 s à 1 000 utilisateurs (les requêtes font la queue).

## DevOps

**15. Pourquoi Git ?**
Git garde l'historique de chaque modification (auteur, date, message) et permet de revenir à
n'importe quelle version. Il permet aussi de travailler à plusieurs en parallèle, et chaque push
sur GitHub déclenche la CI.

**16. Pourquoi utiliser des branches ?**
Pour isoler le travail en cours sans casser la version stable. `main` correspond à la
production, `develop` à l'intégration et `feature/*` à une fonctionnalité. Une fusion n'a lieu
qu'après les tests et la revue.

**17. Pourquoi Docker ?**
Docker emballe l'application avec ses dépendances exactes (Python 3.11, scikit-learn 1.6.1…)
dans une image. La même image tourne sur le poste, dans la CI et sur la VM, ce qui supprime les
écarts d'environnement. Docker Compose lance ensuite les 7 services de la stack en une commande.

**18. Pourquoi la CI/CD ?**
La CI teste et construit automatiquement chaque modification ; la CD la déploie. Une erreur est
repérée au moment du push plutôt qu'au moment de la livraison, et le déploiement ne dépend plus
d'une suite de commandes tapées à la main.

Ici, GitHub Actions enchaîne trois jobs (test → docker → e2e) à chaque push sur `main` ou
`develop`. Le pipeline a réussi dès le premier push, en 2 min 12 s.

## Observabilité

**19. Quelle différence entre logs et métriques ?**
Les logs sont des événements détaillés et horodatés (une prédiction, une erreur avec sa
stack trace). Ils répondent à « que s'est-il passé exactement pour cette requête ? ». Ils sont
volumineux. Les métriques sont des valeurs numériques agrégées dans le temps (requêtes/s,
p95, taux d'erreur). Elles répondent à « comment se porte le système ? ». Elles sont légères et
adaptées aux dashboards et aux alertes.

**20. Pourquoi ELK ?**
Centraliser les logs de tous les conteneurs et serveurs dans un même endroit :
- Logstash collecte et transforme ;
- Elasticsearch indexe, avec une recherche plein texte rapide ;
- Kibana permet de rechercher et de visualiser.

On peut retrouver une requête par son `request_id`, filtrer les erreurs ou analyser les
prédictions par version de modèle.

**21. Pourquoi Prometheus ?**
Prometheus stocke des séries temporelles : il interroge `/metrics` toutes les 5 secondes, garde
l'historique et calcule débit, percentiles ou taux d'erreur avec le langage PromQL. Il évalue aussi
les règles d'alerte. La bibliothèque `prometheus-fastapi-instrumentator` le relie à FastAPI en
quelques lignes.

**22. Pourquoi Grafana ?**
Grafana affiche les métriques de Prometheus dans des tableaux de bord. Ici, le dashboard
« ML Churn API » est créé automatiquement au démarrage et regroupe trafic, latence, erreurs et
indicateurs du modèle sur une seule page.

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
- Commit Git du code, des données et du modèle, avec un tag de version (ici `v1.0.0`).
- Tag de l'image Docker correspondante.
- Pour aller plus loin : un registre de modèles (MLflow) et DVC pour les données volumineuses.

**25. Que faire si un nouveau modèle est moins performant ?**
Ne pas le déployer. La CI doit comparer ses métriques à celles du modèle en production sur le
même jeu de test et bloquer s'il régresse (un garde-fou existe déjà : ROC-AUC > 0,55). S'il
est déjà déployé : rollback immédiat. Ensuite, analyser la cause (données, hyperparamètres) et
valider avec un *shadow deployment* ou un A/B test avant toute promotion.

**26. Comment détecter une dégradation du modèle ?**
- Surveiller la dérive des entrées (tests statistiques KS ou PSI sur les features
  journalisées).
- Surveiller la dérive des sorties (probabilité moyenne, part de CHURN : panneau Grafana et
  alerte `PredictionDrift`).
- Mesurer la performance réelle quand les étiquettes arrivent (precision et recall
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
