# DIMENSIONS.md — Couches de lecture et dimensions du comportement d'une forme

Document de méthode, établi avec l'auteur le 2026-10-19. Il fixe (1) les trois couches qui
séparent la description de l'analyse, (2) les dimensions qui décrivent le comportement
d'une forme. Il peut évoluer ; toute modification est notée dans `QUESTIONS.md`.

Le document de recherche donne la frontière : « لا يوجد تأويل في هذه القواعد بل هي وصف
خالص ». Même l'analyse reste descriptive ; l'interprétation (ce que cela signifie) est
exclue (règle 5 de `CLAUDE.md`).

---

## 1. Les trois couches

| Couche | Ce qu'elle fait | Statut des résultats (SPEC §2.9) |
|---|---|---|
| **وصف** — description | relever ce qui est dans le texte, sans rien en tirer : segments, compagnons, comptages, positions | ملاحظ (observé) |
| **تصنيف وتمثيل** — classement et représentation | ranger les observations avec les catégories de la méthode : codes E, opérations O, types R, familles, matrices, gabarits | موصوف (décrit) |
| **تحليل** — analyse | dégager les régularités et les confronter au hasard ; comparer les formes | مثبت إحصائيا (établi) ; ثابت في كل الروايات (robuste) |
| ~~تأويل~~ — interprétation | dire ce que cela signifie | **exclue** |

Règles :
1. Chaque fiche montre ses trois parties séparément (وصف، تصنيف، تحليل).
2. Un résultat d'analyse porte toujours son statut, son support (nombre de segments), sa
   p-valeur quand elle existe, et ses références (sourate:verset:mot).
3. Sans contrôle aléatoire, un résultat reste « ملاحظ » et est présenté comme une piste.
4. Le rapport d'une étude part des résultats d'analyse et renvoie à leur description.

| Étape | وصف | تصنيف وتمثيل | تحليل |
|---|---|---|---|
| Niveau 0 | formes employées, comptages | catégories du الصرف | employé / possible (dictionnaires) |
| Niveau 1 | les deux segments côte à côte | codes E, opérations O, types R | sous-types de تشابه fréquents |
| Niveaux 2 et 3 | — | familles, matrices, gabarits | colonnes fixes, contraintes, covariations validées |
| Dimensions | valeurs de chaque forme | profils | dimensions qui distinguent les formes |
| Niveau 5 | segments des deux formes | cas أ / ب / ج | ressemblances et différences validées |

---

## 2. Les dimensions

Chaque dimension a une fiche : **question**, **unité d'observation**, **mesure**,
**niveau qui la produit**, **source** dans le document, **contrôle**. ★ = notion du document.
Seules les notions du document servent aux niveaux 1 à 5 : forme, racine, lettre, pronom,
position, ordre, répétition (règle 4). Les catégories du الصرف (nombre, temps…) ne sont
qu'affichées, au niveau 0.

### 2.1 Attributs de la forme (affichés avec elle, hors analyse du comportement)

| Dimension | Question | Mesure |
|---|---|---|
| تواتر — fréquence | Combien de fois, dans combien de segments ? | occurrences, segments |
| الانتشار — dispersion | Où est-elle dans le Coran ? | nombre de sourates, part de la sourate la plus fréquente |
| موقع المقطع في الآية — place du segment dans l'آية | Le segment ouvre-t-il ou ferme-t-il l'آية ? | أول / وسط / آخر / آية كاملة — **détail seulement** |

La dispersion dépend de la taille très inégale des sourates : elle se lit avec prudence.

### 2.2 Le noyau (toujours calculé et affiché)

**موقع الصيغة في المقطع — position dans le segment** ★
- Question : la forme est-elle au début, au milieu, à la fin de son segment ?
- Unité : chaque occurrence. Mesure : répartition في الأول / في الوسط / في الأخير / وحدها.
- Niveau : description des segments. Source : « متغير الموقع ». Contrôle : non (description).

**أنواع الارتباطات — types de compagnons** ★
- Question : avec quels types d'éléments la forme est-elle dans ses segments ?
- Unité : chaque autre case des segments. Mesure : part des trois types (أ) même racine,
  (ب) autres racines, (ج) حروف وضمائر.
- Source : « ترتبط الصيغة المرجعية ب 3 أنواع من العناصر ».
- Contrôle : association de chaque compagnon avec la forme, par mélange des mots entre
  segments (lot E).

**التقديم والتأخير — ordre** ★
- Question : un compagnon est-il toujours avant, toujours après, ou des deux côtés ?
- Unité : chaque compagnon présent dans au moins 2 segments. Mesure : part « toujours
  avant », « toujours après », « variable ».
- Source : « ثبات الترتيب أو تغيره ».

**التكرار — répétition** ★
- Question : les segments de la forme répètent-ils une même formule ?
- Unité : chaque segment. Mesure : part des segments qui partagent un bloc d'au moins 3
  cases avec un autre segment de la forme ; formule la plus fréquente (Q31).
- Source : « نفس المقطع يتكرر ».

**أنواع العلاقة بين المقاطع — types de relations entre segments**
- Question : les segments de la forme sont-ils en تطابق, تشابه ou اختلاف entre eux ?
- Unité : chaque paire de segments. Mesure : répartition R1 / R2 / R3.
- Niveau 1. Source : les trois types du document.

**الجوار — voisinage** (anciennes dimensions 12 et 16)
- Question : les voisins immédiats de la forme sont-ils fixes ? Quand deux segments
  diffèrent, la différence touche-t-elle les voisins ou les parties éloignées ?
- Mesures : (a) voisin dominant avant et après, et sa part ; (b) répartition des opérations
  des paires par distance à la forme : الصيغة نفسها / متصلة / منفصلة.
- Niveaux : description (a), niveau 1 (b).

### 2.3 Dimensions au détail

| Dimension | Question | Mesure | Source |
|---|---|---|---|
| الاتصال والانفصال ★ | Les compagnons sont-ils voisins immédiats ou séparés ? | part des compagnons à distance 1 | « متصلة مباشرة … أو منفصلة عنها » |
| ثبات المجموعات وتغيرها ★ | Une racine compagne apparaît-elle sous une ou plusieurs formes ? | formes par racine compagne | « ثابتة في الإرتباط أو متغيرة » |
| ما يلتصق بالصيغة ★ | Quels lettres et pronoms porte la forme ? | répartition | « الحرف وحده أو الضمير وحده » |
| صيغ الجذر في المقطع ★ | D'autres formes de la racine sont-elles dans le segment ? | fréquence, lesquelles | « قدره تقديرا » |
| أنواع التغيير | Par quelles opérations les segments diffèrent-ils ? | profil O1 à O5 | « إضافة … حذف … الترتيب » |
| أنواع الاستعمال | Une ou plusieurs familles ? des usages isolés ? | familles, isolés, cohésion | « تصنيف المقاطع إلى أنواع إستعمالات » |
| القالب | Quel noyau fixe, quelle part variable ? | colonnes fixes, facultatives | — |
| القيود ★ | Quels éléments vont ensemble, s'excluent, covarient ? | contraintes, covariations | « نظرية القيود » |

### 2.4 Retirées ou transformées
- Longueur des segments : retirée ; elle dépend surtout du découpage choisi.
- Lectures : ce n'est pas une dimension mais un statut de chaque résultat
  (« ثابت في كل الروايات »).

---

## 3. Où servent les dimensions

Elles sont **produites** à différents niveaux, **rassemblées** dans le profil de chaque forme
(SPEC §2.12-b), et **comparées** au niveau 5. Trois échelles : le segment (observation), la
forme (profil), la racine (comparaison des profils de toutes ses formes). Aucune comparaison
entre racines (D-17).

## 4. Contre la complexité
- Le noyau d'abord ; le reste au détail.
- Une dimension qui ne distingue aucune forme de la racine n'apprend rien : elle le dit.
- Un seul jeu de réglages par étude (`config_hash`).
- Contrôle aléatoire et correction pour tests multiples avant tout « مثبت ».
- Peu de racines, étudiées entièrement, avant beaucoup de racines en surface.
