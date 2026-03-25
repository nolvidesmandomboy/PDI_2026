# 1. Description du fonctionnement de la toolbox
Outil : Lissage adaptatif de MNT LiDAR HD 

Cette toolbox Arcgis contient deux outils de traitement : l'outil **Lissage adaptatif de MNT (Modèle Numérique de Terrain) LiDAR HD** et l'outil de **génération des courbes de niveau de l'IGN**

Cet outil permet de lisser automatiquement et de manière différencielle **un MNT LiDAR HD** à partir d’un **MNT LiDAR HD**, puis d'afficher les **courbes de niveaux correctes** géométriquement.

Le traitement comprend les étapes suivantes :

- Ré-échantillonage du MNT en entrée
- Production d'un raster intermédiaire avec les valeurs d'écarts-types
- Production d'un raster intermédiaire de ces valeurs normalisées via une fonction sigmoide  
- Lissage général du MNT d'origine comme couche intermédiaire
- Calcul final du MNT lissé différenciellement par combinaison pondérée du raster lissé et non lissé
- Calcul des courbes de niveau (outil séparé intégré dans ce code pour la démonstration)

---

# 2. Paramètres de l’outil

| Paramètre | Description |
|---|---|
| MNT en entrée | Raster représentant le modèle numérique de terrain à lisser |
| MNT rééchantilloné | MNT rééchantilloné à une taille donnée selon la méthode "plus proches voisins" |
| Taille de rééchantillonage (en mètres) | Taille des nouvelles cellules (carrées, en mètre) |
| MNT calculé de l'écart-type en sortie | Raster avec les valeurs d'écart type pour chaque pixel : différence avec la valeur moyenne des cellules dans un voisinage défini |
| Rayon pour l'écart type | Définit la taille du voisinage circulaire (en pixel) utilisé autour de chaque pixel pour calculer l'écart-type |
| Raster avec valeurs d'écart-type normalisées par une fonction sigmoïde en sortie | Raster des valeurs d'écarts-types normalisées entre 0 et 1 |
| Coefficiant de pente de la sigmoïde (a) | Etendue de la zone de transition (valeurs supérieures à 0 et inférieures à 1) |
| Paramètre de décalage de la sigmoïde (k) | Valeur d'écart type autour de laquelle la sigmoïde bascule de 0 vers 1 (transition de zone plane en zone de montagne) |
| MNT lissé global en sortie | MNT lissé uniformément pour la combinaison finale|
| Type de statistique de lissage | Statistique sur la base de laquelle le lissage va être effectué |
| Rayon pour le lissage global | Définit la taille du voisinage circulaire (en pixel) utilisé autour de chaque pixel pour calculer la moyenne (ou autre statistique sélectionnée)  |
| Emplacement du MNT final en sortie | Emplacement du MNT final en sortie  |
---


# 3. Description détaillée du traitement

Le processus de lissage différencié du MNT est composé de plusieurs étapes.

---

## 3.1 Rééchantillonage 

La première étape consiste à **Rééchantillonnage du Raster en entrée**.

Outil utilisé :  **Rééchantillonnage**

<img width="694" height="416" alt="image" src="https://github.com/user-attachments/assets/ba4823e6-90c3-4ed9-91fb-6208d504fff7" />


Objectifs :

- Changer la taille des pixels du raster de 0,5m à 2,5m.
- Attribuer une nouvelle valeur à tous les nouveaux pixels en fonction des pixels voisins avec la méthode "NEAREST".

Paramètres :
- Taille de rééchantillonage : côtés X & Y de la cellule, une seule valeur est choisie car c'est un carré
- Méthode de rééchantillonage : **Plus proches voisins (nearest)**

Raster en sortie : **Raster rééchantillonné**

## 3.2 Calcul des valeurs d'écart-type

La deuxième étape consiste à **calculer les valeurs d'écart-type**.

Outil utilisé :  **Statistiques focales**
<img width="1276" height="432" alt="image" src="https://github.com/user-attachments/assets/af722304-cbf5-4ab8-aca1-8f93ff206949" />

Objectifs :

- Calculer pour chaque cellule du MNT rééchantilloné la différence avec les valeurs moyennes des cellules dans un voisinage défini (cellules comprises dans un disque de rayon R prédéfini : 100 cellules soit 25 m)

- Dégage les grands ensembles : les zones à haute valeur d'écart-type correspondent aux montagnes, celles à faibles valeurs aux zones planes 

Paramètres :
- Type de voisinage : **CERCLE**
- Rayon : **100** (valeur modifiable)
- Type d'unité : **cellule**
- Type de statistiques : **Ecart-type**

Raster en sortie : **Raster de valeurs d'écart-type ($\text{Raster}_{\text{ET}}$)**

<img width="500" height="860" alt="image" src="https://github.com/user-attachments/assets/81d6266a-ffd4-4178-be01-fa034f17b838" />


---

## 3.3 Normalisation des valeurs d'écart type par une fonction sigmoïde

Les valeurs d'écart type sont normalisées entre 0 et 1. La sigmoïde transforme les valeurs d'écart type en un gradient continu entre 0 et 1.

Outil utilisé : **Calculatrice Raster**

$$C(\text{Raster}_{\text{ET}}) = \frac{1}{1 + e^{-a \cdot (x - k)}}$$

Avec :

- $\text{Raster}_{\text{ET}}$ : le raster en sortie des valeurs d'écart-type ([voir 3.1](#31-calcul-des-valeurs-décart-type))
- $a = 6$ : le coefficient de pente de la sigmoïde.
Le paramètre par défaut **a = 6** détermine la brutalité de la transition ; plus a est grand, plus la transition est abrupte, plus les zones de transition sont petites. **6** a été choisi pour obtenir un lissage très différencié.
- $k = 4$ : la valeur d'écart-type dans les zones de transition.
Le paramètre par défaut **k** correspond au seuil autour duquel la sigmoïde bascule de 0 vers 1, c'est-à-dire, où la transition entre le lissage fort et l'absence de lissage commence.

Raster en sortie : **Raster normalisé ($\text{Raster}_{\text{normalisé}}$) entre 0 et 1**

<img width="500" height="856" alt="image" src="https://github.com/user-attachments/assets/d5a55f77-3e6e-4751-9586-d808a01cdb67" />


Il sera ensuite utilisé comme **coefficient de pondération** dans l'étape finale de la combinaison.

---

## 3.4 Lissage général du MNT

Lissage du MNT, qui sera utilisé pour la combinaison finale

Outil utilisé : **Statistiques focales**

- lisser uniformément le MNT 

Paramètres :
- Type de voisinage : **CERCLE**
- Rayon : **20** (valeur modifiable)
- Type d'unité : **cellule**
- Type de statistiques : **Moyenne**

Sortie : **$\text{MNT}_{\text{lissé}}$**

---

## 3.5 Pondération adaptative des MNT lissé et non lissé et combinaison

Outil utilisé : **Calculatrice Raster**

Principe : 
Applique un lissage différencié sur l'entièreté du MNT choisi en entrée, selon le relief ; les zones plates sont fortement lissées tandis que les zones montagneuses ne le sont pas.

Méthode : 
La combinaison finale repose sur la pondération suivante : 

$$\text{MNT}_{\text{final}} = A \cdot C + (1 - C) \cdot B$$

Avec :
- A : **$\text{MNT}_{\text{origine}}$**  
- B : **$\text{MNT}_{\text{lissé}}$** ([voir 3.3](#33-lissage-général-du-mnt))
- C : **$\text{Raster}_{\text{normalisé}}$** (valeurs entre 0 et 1) ([voir 3.2](#32-normalisation-des-valeurs-décart-type-par-une-fonction-sigmoïde))

Interprétation :

- Lorsque $C \approx 1$ (fort relief) → le MNT non lissé domine
- Lorsque $C \approx 0$ (faible relief) → le MNT lissé domine
- Entre les deux → transition progressive contrôlée par la sigmoïde

Raster en sortie : **$\text{MNT}_{\text{lissé de manière différencielle}}$**

AVANT

<img width="500" height="892" alt="image" src="https://github.com/user-attachments/assets/5f3705da-0647-4140-b09b-2f13ea5d63f7" />

APRES 

<img width="500" height="892" alt="image" src="https://github.com/user-attachments/assets/46f3fbef-8e07-4389-87df-8983ee87c3d0" />


## 3.6 Calcul des courbes de niveau 
**Paramètres**
simplify_tolerance = 0.5,
smooth_tolerance = 15,
simplify_tolerance_bis = 0.5
equidistance = 5
longueur_min = 60


<img width="976" height="552" alt="Capture d&#39;écran 2026-03-25 213114" src="https://github.com/user-attachments/assets/c5da6ca7-a1ce-4873-bcc8-dd9bc2085a49" />

<img width="960" height="692" alt="Capture d&#39;écran 2026-03-25 213249" src="https://github.com/user-attachments/assets/cc07753e-7551-44f3-837c-9c21272dd388" />

