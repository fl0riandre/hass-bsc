# Brewers Social Club pour Home Assistant

Intégration Home Assistant custom pour exposer l'API BSC sous forme d'entités
faciles à utiliser dans les dashboards et automatisations.

## Fonctions

- configuration entièrement depuis l'interface Home Assistant ;
- authentification par clé API BSC (`Authorization: Bearer …`) ;
- rafraîchissement centralisé et configurable ;
- compteurs membres, partenaires, avantages, commandes groupées et paiements ;
- capteurs dynamiques pour les brassins Brewfather actifs ;
- planning BSC du jour, recalculé à chaque relève selon le fuseau Europe/Paris ;
- température, consigne, gravité et état des contrôleurs RAPT ;
- diagnostic de connexion sans exposer la clé API ;
- modules activables séparément.
- action `brewers_social_club.get_api_data` pour les endpoints GET non encore
  modélisés sous forme d'entités.

Les listes de membres ne sont volontairement pas copiées dans les attributs des
entités : cela évite d'exposer des données personnelles et de gonfler la base
`recorder` de Home Assistant. Les compteurs restent disponibles.

## Prérequis BSC

Créer une clé de lecture dans l'API BSC :

```bash
cd /var/www/api
npm run api-key:create -- home-assistant
```

Ajouter l'entrée générée dans `api/data/api-keys.json`. Conserver le jeton brut
affiché par la commande : il sera demandé une seule fois par Home Assistant.

## Installation avec HACS

1. Publier ce dossier dans un dépôt GitHub.
2. Dans HACS : **Intégrations → Dépôts personnalisés**.
3. Ajouter l'URL du dépôt, catégorie **Integration**.
4. Installer **Brewers Social Club** puis redémarrer Home Assistant.
5. Aller dans **Paramètres → Appareils et services → Ajouter une intégration**.
6. Chercher **Brewers Social Club** et renseigner :
   - URL : `https://bsc.kloud.best`
   - clé API : `bsc_api_…`

Une installation manuelle reste possible en copiant
`custom_components/brewers_social_club` dans le dossier `custom_components` de
Home Assistant.

## Configuration

Les options de l'intégration permettent de choisir les modules interrogés et
l'intervalle de rafraîchissement (60 à 3600 secondes).

Modules disponibles :

- Vue d'ensemble
- Membres
- Partenaires
- Avantages
- Commandes groupées
- Brewfather
- RAPT
- Encaissements
- Stockage
- Planning du jour

Le capteur **Planning aujourd’hui** expose le nombre d'opérations planifiées.
Ses attributs contiennent la fenêtre UTC interrogée, le nombre de réservations,
les allocations de contenants et jusqu'à 50 événements normalisés. Plusieurs
réservations appartenant à la même opération sont regroupées afin d'éviter de
dupliquer un brassage pour chaque ressource mobilisée.

## Lire un endpoint arbitraire

L'action `brewers_social_club.get_api_data` donne accès à tous les endpoints
GET autorisés par la clé. Elle retourne la réponse JSON et peut être utilisée
dans une automatisation :

```yaml
action: brewers_social_club.get_api_data
data:
  path: /api/admin/brewfather/batches?scope=all
response_variable: bsc_batches
```

Le chemin doit commencer par `/api/`. Aucune méthode d'écriture n'est exposée.

## Dashboard

Un exemple minimal est fourni dans
[`examples/dashboard.yaml`](examples/dashboard.yaml).

## Développement

Les tests sans dépendance Home Assistant se lancent avec :

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall custom_components
```

## Sécurité

- La clé API est stockée dans l'entrée de configuration Home Assistant.
- Elle n'est jamais placée dans les états, attributs ou diagnostics.
- L'intégration ne réalise que des requêtes GET.
- Les erreurs HTTP n'incluent jamais le contenu du header d'autorisation.
