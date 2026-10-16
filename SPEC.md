# SPEC.md — Harnais d'étude des corrélations coraniques

## 0. En bref
L'étude part d'une **racine de référence** et travaille en six niveaux, dans cet ordre :
0. **Identité de la racine (هوية الجذر)** : deux tableaux (verbes, noms) montrent les formes
   de la racine employées dans le Coran ; un clic sur une case montre les formes du même
   genre que l'arabe permet mais que le Coran n'emploie pas.

Puis, pour chaque forme de référence, on trouve tous les segments où elle apparaît :
1. **Paires** : chaque paire de segments est comparée **seule**, et la typologie de l'auteur
   la classe en تطابق / تشابه / اختلاف. C'est l'analyse première.
2. **Familles** : la typologie trace les frontières. Les paires en تطابق ou تشابه relient
   leurs segments ; le اختلاف les sépare.
3. **Matrices** : une matrice d'alignement par famille résume ce que la typologie a regroupé
   (gabarit, colonnes fixes et variables, contraintes).
4. **Entre familles** : le اختلاف devient la relation entre familles.
5. **Toutes les formes de la racine** : chaque forme de la racine de référence est analysée
   de la même façon ; les formes sont comparées **deux à deux**, puis une **matrice globale**
   de la racine est construite à partir de ces résultats. Aucune comparaison entre racines.

La couche statistique vérifie ensuite que chaque régularité dépasse le hasard. Le travail
se fait sur le texte Hafs d'abord, puis sur les autres lectures sous forme de variantes.

Les décisions que l'auteur doit encore prendre sont dans `DECISIONS.md`. Tant qu'elles ne
sont pas tranchées, le programme applique la valeur par défaut indiquée, sous forme de
paramètre dans `config.yaml`.

---

## 1. Vocabulaire (défini par le document de recherche)

| Terme | Sens pour l'implémentation |
|---|---|
| **Forme (الصيغة)** | Un mot tel qu'écrit dans le texte, pronoms et lettres collés compris (لقادرون, له, عليه). Une seule case. **Exception (D-02)** : la واو de conjonction est un mot à part (ويقدر → و + يقدر). |
| **Racine (الجذر)** | Fournie par le corpus annoté. Une racine = ensemble (مجموعة) de ses formes attestées. Le lemme du corpus n'est PAS utilisé (notion grammaticale absente du document). |
| **Segment (المقطع)** | Partie de verset terminée par une pause (وقف). Unité d'analyse. |
| **Forme de référence** | La forme étudiée (ex. يقدر). |
| **Associations** | Autres éléments du même segment : (a) formes de la même racine, (b) formes d'autres racines, (c) lettre/pronom seul ou ensemble. |
| **Bloc (جزء)** | Suite d'au moins 2 mots consécutifs, répétée à l'identique dans au moins 2 segments. |
| **Famille** | Groupe de segments assez proches pour partager une même matrice. |

---

## 2. La méthode en six niveaux (0 à 5)

### 2.0 Niveau 0 — Identité de la racine (هوية الجذر)
**But** : voir quelles formes de la racine le Coran emploie, par rapport à ce que la langue
arabe permet (ex. emploi du مضارع seulement, absence du أمر…). Cette étape vient avant
toute analyse de corrélation, et elle fournit la liste des formes de référence du niveau 5.

**Exception limitée aux catégories du الصرف** (décision de l'auteur, D-22) : les catégories
grammaticales (ماضي، مضارع، أمر، معلوم/مجهول، أوزان، اسم فاعل، مصدر…) servent **uniquement**
à ranger les formes dans ces deux tableaux. Elles n'entrent jamais dans l'analyse des
corrélations (niveaux 1 à 5).

**Tableau 1 — الأفعال** · **Tableau 2 — الأسماء**
Principe d'affichage (décidé par l'auteur) :
1. Le tableau ne montre **que les cases utilisées dans le Coran**. Chaque case affiche
   **directement toutes** les formes du Coran qui lui appartiennent (écrites telles qu'elles
   sont), avec leur nombre d'occurrences et leurs traits (personne, mode, nombre…).
   **Aucune forme employée dans le Coran n'est cachée derrière un clic.**
2. **Le clic sert uniquement** à ouvrir les formes **du même genre** (même catégorie, même
   وزن) qui ne sont **pas** employées dans le Coran, chacune avec son état (D-20) :
   - **attestée** dans la langue (source lexicale) mais absente du Coran ;
   - **théorique** seulement (produite par les règles du تصريف, non attestée).
3. **Catégories entièrement absentes** : sous chaque tableau, une ligne compacte les nomme
   (ex. « absents du Coran : أمر ، مجهول ، افتعل »). Un clic montre les formes possibles.
   Ainsi, une absence totale reste visible même si elle n'a pas de case.

**En-tête de la racine (fiche d'identité)**
- Nombre de lettres : ثلاثي / رباعي.
- Nature des lettres : صحيح (سالم، مهموز، مضعّف) / معتل (مثال، أجوف، ناقص، لفيف مقرون،
  لفيف مفروق). Cette nature change la conjugaison ; elle est affichée, pas analysée.
- Nombre total d'occurrences de la racine dans le Coran ; part des verbes et des noms.

**Tableau 1 — الأفعال (catégories complètes, D-21)**
Le tableau principal croise le **وزن** (lignes) et le **زمن / البناء** (colonnes).
Les autres dimensions apparaissent comme traits à côté de chaque forme.

Lignes — الأوزان :
| Groupe | أوزان |
|---|---|
| ثلاثي مجرد (avec son باب) | فَعَلَ يَفْعُلُ ، فَعَلَ يَفْعِلُ ، فَعَلَ يَفْعَلُ ، فَعِلَ يَفْعَلُ ، فَعُلَ يَفْعُلُ ، فَعِلَ يَفْعِلُ |
| مزيد بحرف | أَفْعَلَ ، فَعَّلَ ، فاعَلَ |
| مزيد بحرفين | انْفَعَلَ ، افْتَعَلَ ، افْعَلَّ ، تَفَعَّلَ ، تَفاعَلَ |
| مزيد بثلاثة أحرف | اسْتَفْعَلَ ، افْعَوْعَلَ ، افْعالَّ ، افْعَوَّلَ |
| رباعي مجرد ومزيد | فَعْلَلَ ، تَفَعْلَلَ ، افْعَنْلَلَ ، افْعَلَلَّ |
| ملحقات | فَوْعَلَ ، فَيْعَلَ ، فَعْوَلَ ، فَعْلَى… (regroupées sous « autres ») |

Colonnes : ماضٍ · مضارع · أمر, chacune divisée en مبني للمعلوم / مبني للمجهول (pas de
مجهول pour le أمر).

Dans chaque case, chaque forme du Coran est suivie de ses traits :
- **الإسناد** : la personne (متكلم، مخاطب، غائب × مفرد، مثنى، جمع × مذكر، مؤنث) ;
- **حالة المضارع** : مرفوع ، منصوب ، مجزوم ;
- **التوكيد** : نون التوكيد الثقيلة / الخفيفة, s'il y a lieu.
Au clic sur la case : seulement les formes du même genre **non employées** dans le Coran
(attestées / théoriques), avec les mêmes traits.

Information de ligne (affichée, pas analysée) : لازم / متعدٍّ quand la source lexicale le donne.

**Tableau 2 — الأسماء (catégories complètes, D-21)**
Le tableau principal croise le **type de nom** (lignes) et le **وزن** (colonne : وزن de
dérivation I à X, puis le وزن précis de la forme).

Lignes — أنواع الأسماء :
| Groupe | Types |
|---|---|
| المصادر | مصدر صريح (ثلاثي : سماعي ؛ مزيد : قياسي) ، مصدر ميمي ، مصدر المرّة ، مصدر الهيئة ، مصدر صناعي |
| المشتقات | اسم الفاعل ، صيغ المبالغة (فَعّال ، مِفْعال ، فَعُول ، فَعِيل ، فَعِل) ، الصفة المشبّهة ، اسم المفعول ، اسم التفضيل ، اسم الزمان ، اسم المكان ، اسم الآلة |
| أسماء جامدة من الجذر | اسم ذات / اسم معنى non dérivé, اسم جنس ، اسم جمع |
| صيغ ملحقة | التصغير ، الاسم المنسوب (ياء النسب) |

Dans chaque case, chaque forme du Coran est suivie de ses traits :
- **العدد** : مفرد ، مثنى ، جمع مذكر سالم ، جمع مؤنث سالم ، جمع تكسير (avec son وزن ;
  جمع قلّة / جمع كثرة) ;
- **الجنس** : مذكر / مؤنث ;
- **التعريف** : معرّف بأل ، معرّف بالإضافة ، نكرة ;
- **الإعراب** : مرفوع ، منصوب ، مجرور (affiché comme trait ; jamais utilisé pour comparer, D-04).
Au clic sur la case : seulement les formes du même genre **non employées** dans le Coran
(attestées / théoriques), avec les mêmes traits.

**Classements ambigus** (D-23) : certains أوزان servent plusieurs types (ex. فَعِيل : صيغة
مبالغة ou صفة مشبهة ; مَفْعَل : مصدر ميمي، اسم زمان ou اسم مكان). Si la source ne tranche
pas, la forme va dans une case **« ambiguë »** qui nomme les types possibles ; elle n'est
jamais rangée au hasard.

Exemple de lecture (illustratif, chiffres à calculer) :
| وزن | ماضي معلوم | مضارع معلوم |
|---|---|---|
| فَعَلَ | قَدَرَ … (n) | يَقْدِرُ ، يَقْدِرُونَ … (n) |
| فَعَّلَ | قَدَّرَ … (n) | يُقَدِّرُ … (n) |
Sous le tableau : « absents du Coran : … » (clic → formes possibles).

**Règles de construction**
- Côté Coran : les catégories viennent des annotations du corpus (forme verbale, temps,
  voix, participes, مصدر…), pas d'une comparaison de lettres (l'écriture ʿuthmānī diffère
  parfois de l'écriture courante).
- Côté « possible » : un générateur de تصريف produit les formes théoriques ; une source
  lexicale, si elle est trouvée, marque celles qui sont attestées. Les مصادر de la forme I
  ne sont pas prévisibles : sans source lexicale, ils sont marqués « à vérifier ».
- Aucune forme possible n'est inventée à la main ni de mémoire (règle 2 de CLAUDE.md).
- **Ce que le corpus donne, ce qu'il faut calculer** : le corpus annoté donne le وزن verbal,
  le temps, la voix, le mode, les personnes, et pour les noms les participes et le مصدر.
  Les types plus fins (صيغة مبالغة، صفة مشبهة، مصدر ميمي، اسم زمان/مكان/آلة، تصغير، نسبة,
  جمع تكسير) sont déduits du وزن de la forme ; en cas de doute → case « ambiguë ».
- **Ordre des sources pour les formes non employées** (décision de l'auteur, D-20) :
  le **dictionnaire** d'abord (état « attestée ») ; le **générateur théorique** ensuite, en
  complément (état « théorique »).
  **Seuls les dictionnaires classiques comptent** (décision de l'auteur, D-24). Une forme
  est « attestée » si elle figure dans l'article de sa racine dans au moins un dictionnaire
  classique de la liste D-25 ; le nom du dictionnaire s'affiche à côté
  (ex. « attestée · لسان العرب »).
  **Méthode d'extraction** : les dictionnaires classiques sont des textes, pas des tableaux.
  1. découper le texte en articles, un par racine (les titres d'articles) ;
  2. relever les mots de l'article qui appartiennent à la racine ;
  3. une forme théorique est « attestée » si elle correspond à un de ces mots (comparaison
     à plusieurs niveaux de الشكل, car le texte est souvent partiellement vocalisé) ;
  4. **contrôle manuel** : sur un échantillon de racines (dont قدر), l'auteur vérifie la
     liste obtenue ; le taux d'erreur est noté dans `DECISIONS.md`.
  Si une forme est douteuse (correspondance partielle), elle est marquée « à vérifier »,
  jamais « attestée » d'office. Les formes non prévisibles par règle (مصدر ثلاثي، صفة
  مشبهة، جمع تكسير) ne viennent que du dictionnaire.
- **Validation** : pour une racine de test, chaque forme du Coran tombe dans exactement une
  case (ou dans une case « ambiguë ») ; la somme des cases égale le nombre d'occurrences de
  la racine (étape 3).


### 2.1 Vue d'ensemble : où vit chaque type de la typologie
| Type | Où il vit | Pourquoi |
|---|---|---|
| **تطابق** | Paires, puis colonnes fixes de la matrice | Un bloc identique devient une suite de colonnes égales |
| **تشابه par ajout / retrait / remplacement** (O1, O2) | Paires, puis colonnes variables ou facultatives | Une différence dans une même colonne |
| **تشابه d'ordre** (O3, O4, O5) | Paires et vecteur d'ordre (pas dans les colonnes) | Une colonne fixe un ordre ; ces cas portent justement sur l'ordre |
| **اختلاف** | Entre les familles | Deux segments sans élément commun ne peuvent pas partager une matrice utile |

Principe : **la typologie est première, la matrice est seconde.** La matrice résume ce
que la typologie a regroupé ; elle ne remplace jamais la comparaison directe des paires.

### 2.2 Relation entre deux éléments (codes E)
| Code | Relation | Exemple du document |
|---|---|---|
| **E0** | Forme identique | يقدر = يقدر |
| **E1** | Même base, lettre ou pronom ajouté / retiré | على ~ عليه |
| **E2** | Même base, pronom changé | ربي ~ ربك |
| **E3** | Même racine, forme différente | يشاء ~ شيء ، الغيب ~ الغيوب |
| **E4** | Racine différente | الله ~ ربك |
| **Ø** | Absent dans l'autre segment | من عباده / Ø |

Les codes sont des **étiquettes** (compter, filtrer, comparer), pas des quantités.
Seules les notions du document sont utilisées : forme, racine, lettre, pronom.

### 2.3 Niveau 1 — Comparaison directe de deux segments (analyse première)
Chaque paire est alignée **seule**, sans tenir compte des autres segments.

**Alignement d'une paire**
1. ancrer la forme de référence (pivot) dans les deux segments ;
2. repérer les blocs E0 communs (suites d'au moins 2 mots identiques), où qu'ils soient ;
3. apparier le reste par proximité décroissante : E0, puis E1, E2, E3 (D-06) ;
4. à égalité, préférer l'appariement qui respecte l'ordre des mots.

**Opérations**
| Code | Opération | Exemple du document |
|---|---|---|
| **O1** | Ajout / retrait d'un élément ou d'un bloc | « من عباده » / Ø |
| **O2** | Remplacement (qualifié par E1 à E4) | ربي → ربك (O2-E2) |
| **O3** | Inversion (تقديم وتأخير) | مما كسبوا على شيء / على شيء مما كسبوا |
| **O4** | Séparation : éléments collés d'un côté, séparés de l'autre | bloc coupé par un élément inséré |
| **O5** | Déplacement de la forme de référence (début / milieu / fin) | لا يقدر على شيء / ما يشاء ويقدر |

Chaque opération est notée selon sa **distance au pivot** : le pivot lui-même / voisin
immédiat / éloigné.

**Ordre** : chaque segment reçoit un **vecteur d'ordre** de ses unités (blocs et mots
appariés). O3 = mêmes unités dans un ordre différent ; on compte les paires d'unités inversées.
Exemple : `لا يقدرون | مما كسبوا | على شيء` et `لا يقدرون | على شيء | مما كسبوا` →
ordre (1,2,3) contre (1,3,2) → O3, une paire inversée.

**Signature** d'une paire : liste des blocs E0, liste des opérations, vecteur de comptage
des codes.

**Types du document**, déduits de la signature :
| Type | Règle |
|---|---|
| **R1 — تطابق** | Totale : segments égaux. Partielle : ≥ 1 bloc E0 de longueur ≥ 2. |
| **R2 — تشابه** | Au moins 2 éléments communs (E0 à E3) hors pivot, avec au moins une opération. |
| **R3 — اختلاف** | Aucun élément commun (E0 à E3) hors pivot. |

R1 partiel et R2 peuvent coexister. Les sous-types de تشابه ne sont pas fixés à l'avance :
ils sortent du comptage des combinaisons d'opérations observées.

**Coût** : une forme fréquente (ex. قوم, ~150 segments) donne environ 11 000 paires, ce qui
reste raisonnable. Filtre préalable : deux segments sans aucun élément commun hors pivot
sont classés R3 directement, sans alignement.

### 2.4 Niveau 2 — Familles tracées par la typologie
1. On construit un **graphe** : un nœud par segment, un lien entre deux segments si leur
   paire est R1 ou R2. Le poids du lien = nombre d'éléments communs (E0 à E3) hors pivot.
   Une paire R3 ne crée aucun lien.
2. **Famille** = groupe de segments reliés (composante connexe).
3. **Usage isolé** = segment sans aucun lien (comme l'usage de سورة البلد dans le document).
4. **Contrôle de l'enchaînement** : A peut ressembler à B et B à C sans que A et C se
   ressemblent. Pour chaque famille, on calcule sa **cohésion** = part des paires internes
   qui sont R1 ou R2. Si la cohésion est inférieure à `cohesion_min` (défaut 50 %, D-15),
   on coupe les liens les plus faibles jusqu'à repasser au-dessus du seuil, et on garde
   la trace de chaque coupure.

### 2.5 Niveau 3 — La matrice d'alignement (une par famille)
**Définition**
- **ligne** = un segment de la famille ;
- **colonne** = une position alignée ; les blocs repérés au niveau 1 forment chacun
  **une seule unité** (une colonne) ;
- **case** = la forme telle qu'écrite, ou **Ø** ;
- **colonne pivot** = la forme de référence ; on aligne séparément la partie à droite et
  la partie à gauche du pivot.

Exemple (cinq segments du document ; dans le programme, chaque mot ou bloc a sa colonne) :

| | intro | ذات | يبسط | الرزق | لمن | يشاء | من | عباده | **ويقدر** | له |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Ø | الله | يبسط | الرزق | لمن | يشاء | من | عباده | ويقدر | له |
| 2 | إن | ربك | يبسط | الرزق | لمن | يشاء | Ø | Ø | ويقدر | Ø |
| 3 | قل إن | ربي | يبسط | الرزق | لمن | يشاء | من | عباده | ويقدر | له |
| 4 | أولم يروا أن | الله | يبسط | الرزق | لمن | يشاء | Ø | Ø | ويقدر | Ø |
| 5 | له مقاليد السماوات والأرض | Ø | يبسط | الرزق | لمن | يشاء | Ø | Ø | ويقدر | Ø |

**Règle de choix de l'alignement** (appliquée dans cet ordre)
1. ancrer le pivot ;
2. respecter autant que possible les appariements trouvés au niveau 1 ;
3. maximiser les cases E0, puis E1, E2, E3 ;
4. à égalité, minimiser le nombre de colonnes ;
5. s'il reste plusieurs solutions optimales, les garder toutes et marquer la matrice
   « ambiguë » au lieu d'en choisir une en silence.

**Lecture en colonnes → le gabarit (قالب)**
| Type de colonne | Règle |
|---|---|
| **Fixe** | Même forme (E0) dans 100 % des lignes |
| **Relativement fixe** | Même forme dans au moins `seuil_relatif` des lignes (défaut 75 %, D-09) |
| **Variable** | Formes différentes ; on note les codes E entre remplissages |
| **Facultative** | Contient au moins un Ø |

Le gabarit est l'écriture compacte de la matrice :
`[intro] [ذات] يبسط الرزق لمن يشاء [من عباده] ويقدر [له]`
Pour chaque case variable ou facultative : liste des remplissages et fréquences.

Les opérations d'ordre (O3, O4, O5) ne sont **pas** représentées par les colonnes : elles
restent dans les signatures de paires et les vecteurs d'ordre, affichés à côté de la matrice.

### 2.6 Contrôle de cohérence paires ↔ matrice
L'alignement d'une famille entière peut placer deux segments autrement que leur
comparaison directe. Pour chaque paire d'une famille :
1. on déduit de la matrice une signature « induite » (comparaison des deux lignes) ;
2. on la compare à la signature directe du niveau 1 ;
3. tout écart est enregistré et affiché.

**La signature directe fait foi** pour la typologie. Un taux d'écart élevé signale une
matrice peu fiable (famille trop hétérogène, alignement forcé).

### 2.7 Contraintes entre colonnes (قيود)
Sur les lignes d'une matrice :
| Contrainte | Sens | Exemple observé (5 segments seulement) |
|---|---|---|
| **Équivalence** | A présent ⇔ B présent | من عباده et له présents ou absents ensemble |
| **Implication** | A présent ⇒ B présent (pas l'inverse) | — |
| **Exclusion** | A et B jamais présents ensemble | — |
| **Covariation** | Tel remplissage de A va avec tel remplissage de B | — |

Une contrainte n'est retenue que si elle porte sur au moins `support_min` lignes (défaut 3,
D-10) et passe le contrôle aléatoire (permutation des remplissages entre lignes).

### 2.8 Niveau 4 — Entre familles
- **Matrice des familles** (familles × familles) : pour chaque couple de familles, nombre
  de paires R3 et de liens faibles coupés (§2.4). C'est la place du اختلاف.
- La comparaison entre formes de la racine relève du niveau 5 (§2.12).

### 2.9 Articulation des trois analyses et statut des résultats
| Analyse | Rôle | Question |
|---|---|---|
| Typologie (R, E, O) | **Décrire** | Quel genre de relation ? |
| Matrice | **Représenter** | Où sont les éléments, comment se correspondent-ils ? |
| Statistique | **Valider** | Est-ce plus que le hasard ? |

Circuit : paires (typologie) → familles → matrices → statistique → **retour** (familles
coupées, seuils ajustés, sous-types de تشابه nommés).

Chaque résultat (bloc, colonne fixe, contrainte, type d'opération fréquent) est un objet
unique portant trois marques : **où** (matrice, lignes, colonnes), **quoi** (codes de la
typologie), **solidité** (support, p-valeur). Il reçoit un statut :
| Statut | Condition |
|---|---|
| **Observé** | Visible dans les données |
| **Décrit** | Nommé par la typologie |
| **Établi** | Décrit + validé par la statistique |
| **Robuste** | Établi + présent dans toutes les lectures disponibles (étape 7) |

Seuls les résultats établis ou robustes sont présentés comme corrélations ; les autres
sont affichés comme pistes.

### 2.10 Cas particuliers
- **Forme de référence deux fois dans un segment** : une ligne par occurrence, chacune pivot
  à son tour ; lignes liées et marquées pour ne pas compter le segment deux fois.
- **Bloc qui se coupe ailleurs** (noté dans le document) : les blocs sont recalculés pour
  chaque paire et chaque famille ; la coupure est une opération O4. Un bloc n'est jamais
  figé une fois pour toutes.

### 2.11 Cas de test tirés du document (à reproduire exactement)
Signatures **directes** attendues (niveau 1) :
| Paire | Signature attendue |
|---|---|
| `قل إن ربي يبسط الرزق لمن يشاء من عباده ويقدر له` / `قل إن ربي يبسط الرزق لمن يشاء ويقدر له` | R1 partiel ; O1 (من عباده) |
| `قل إن ربي يبسط الرزق لمن يشاء ويقدر` / `إن ربك يبسط الرزق لمن يشاء ويقدر` | R1 partiel + R2 ; O1 (قل) ; O2-E2 (ربي/ربك) |
| `لا يقدرون مما كسبوا على شيء` / `لا يقدرون على شيء مما كسبوا` | R1 partiel ; O3 (une paire d'unités inversée) |
| `أيحسب أن لن يقدر عليه أحد` / `عبدا مملوكا لا يقدر على شيء` | R2 ; O2-E1 (عليه/على) ; autres E4/Ø |
| `لا يقدر على شيء` / `ما يشاء ويقدر` | R2 ; O2-E3 (شيء/يشاء) ; O5 |

Tests de famille et de matrice :
- les segments du document autour de `يبسط الرزق لمن يشاء … ويقدر` forment une seule famille ;
- son gabarit est `[intro] [ذات] يبسط الرزق لمن يشاء [من عباده] ويقدر [له]` ;
- l'usage de سورة البلد est un usage isolé ;
- aucun écart paires ↔ matrice dans cette famille (§2.6).

### 2.12 Niveau 5 — Toutes les formes d'une racine, puis leur comparaison
**Portée** : uniquement les formes de la **racine de référence**, telles qu'attestées dans le
Coran. Aucune comparaison entre racines différentes (décision de l'auteur, D-17).

**(a) Analyser toutes les formes de référence, une par une**
- Chaque forme passe par les niveaux 1 à 4 avec **les mêmes réglages**. Chaque analyse
  enregistre l'empreinte de ses réglages (`config_hash`) : deux analyses ne sont
  comparables que si leur empreinte est la même. Un changement de réglage relance tout.
- On analyse toutes les formes de la racine de référence ; une autre racine est une
  étude séparée, sans comparaison avec la première.
- **Forme à un seul segment** (elle n'apparaît qu'une fois) : elle n'est **pas exclue**.
  1. Sa fiche décrit entièrement son segment : associations (a, b, c), positions.
  2. Elle n'a pas de paire interne : le volet typologie interne est vide, et c'est indiqué
     (« occurrence unique »), pas caché.
  3. Elle entre pleinement dans la comparaison avec les autres formes de la racine : son
     segment est comparé directement aux segments des autres formes (niveau 1, mêmes codes
     R, E, O). On sait ainsi à quels usages des autres formes elle ressemble, ou si elle est
     isolée dans toute la racine.
  4. Volet statistique : non calculé (« données insuffisantes »), car un seul segment ne
     permet aucun test.
  Seuil réglable : `occ_min_stats` (défaut 3 segments) pour le volet statistique (D-18).

**(b) Le profil d'une forme**
Chaque analyse complète est résumée dans un **profil** standard, en trois volets :
| Volet | Contenu |
|---|---|
| **Typologie** | Part des paires R1 / R2 / R3 ; fréquence de chaque opération (O1–O5) et de chaque code E ; nombre de familles ; part d'usages isolés ; cohésion moyenne |
| **Matrice** | Gabarits des familles ; colonnes fixes (contenu) ; contraintes retenues |
| **Statistique** | Associations établies (§2.9) avec leurs scores |

**(c) Étape 1 de la comparaison : les formes deux à deux**
Ordre décidé par l'auteur (D-17) : on compare d'abord les formes **par paires**, et on ne
construit la matrice globale de la racine **qu'ensuite** (§2.12-e). C'est la même logique
qu'au niveau des segments : la comparaison directe est première, la matrice est seconde.

La comparaison porte d'abord sur les **segments** : chaque segment d'une forme est comparé
directement à chaque segment de l'autre forme (niveau 1, les deux formes étant prises
comme pivots appariés par leur racine, code E3). Les profils viennent ensuite résumer.
| Volet | Ce qu'on compare | Résultat |
|---|---|---|
| **Typologie** | Les types R entre segments des deux formes ; les opérations les plus fréquentes | Description lisible : « يقدر varie surtout par ajout, قدير surtout par remplacement » + part des paires en تطابق / تشابه / اختلاف |
| **Matrice** | Les gabarits et colonnes fixes | Blocs et colonnes communs ; classement selon les trois cas du document : même forme associée / même racine mais formes différentes / rien en commun |
| **Statistique** | Les associations établies | Compagnons communs, compagnons propres, et part des compagnons communs |

Chaque différence ou ressemblance entre deux formes passe le **contrôle aléatoire**
(permutation des segments entre les deux formes) avant d'être déclarée établie.

**Pas de score unique** : les trois volets restent séparés. On regarde en revanche s'ils
**s'accordent** : désignent-ils les mêmes formes comme se ressemblant ? Un accord des trois
est un résultat fort ; un désaccord est montré tel quel, car il est instructif.
Ces critères sont adoptés pour commencer et seront revus au vu des premiers résultats (D-19).

**(d) Portée des comparaisons**
Toutes les paires de formes de la racine de référence sont comparées automatiquement.
C'est la comparaison prévue par le document (ex. يقدر / قدير ، عالم الغيب / علام الغيوب).
Pas de comparaison avec les formes d'autres racines.

**(e) Étape 2 de la comparaison : la matrice globale de la racine**
Construite **après** les comparaisons par paires de formes, à partir de leurs résultats :
1. **Liens** : deux segments (de formes différentes ou de la même forme) sont liés si leur
   comparaison directe est R1 ou R2 (§2.3, §2.12-c).
2. **Familles de la racine** : groupes de segments liés, même règle de cohésion qu'au §2.4.
   Une famille peut donc réunir des segments de يقدر, قدير, قدره… qui partagent un gabarit.
3. **Une matrice par famille de la racine**, alignée sur la colonne pivot (où se trouve, selon
   la ligne, la forme de la racine) ; gabarit et contraintes comme au §2.5 et §2.7.
4. **Contrôle de cohérence** : comme au §2.6, ce que dit la matrice globale est comparé aux
   résultats des paires de formes ; les écarts sont affichés, et les paires font foi.

**(f) Les résultats d'ensemble**
- Trois **matrices formes × formes**, une par volet, pour la racine de référence (issues des
  comparaisons par paires).
- Les **matrices globales de la racine** (§2.12-e) : quelles formes partagent les mêmes
  gabarits, quelles formes restent isolées.
- Regroupement des formes selon chaque volet, et carte de l'accord entre volets.
- Les statuts du §2.9 s'appliquent aussi aux résultats de comparaison.

---

## 3. Données (à télécharger — Étape 1)

Claude Code doit **chercher, télécharger et vérifier** les ressources suivantes dans `data/raw/`.
Pour chacune : vérifier l'URL officielle, la licence, calculer le SHA-256, noter dans `data/SOURCES.md`.
Si un téléchargement exige un formulaire, une inscription ou une acceptation de licence faite à la main,
**s'arrêter et me demander** de le faire.

| Ressource | Usage | Source pressentie |
|---|---|---|
| Texte coranique ʿuthmānī (Hafs, éd. du Caire 1924) | Texte de base, jamais modifié | Tanzil (tanzil.net) |
| Annotation morphologique (racine, segmentation des clitiques) | Racines et codes E (le champ lemme est ignoré) | Quranic Arabic Corpus (corpus.quran.com) — licence à lire, usage non commercial |
| Annotation alternative | Contrôle croisé des racines | MASAQ (Mendeley Data, DOI 10.17632/9yvrzxktmr), licence CC BY 3.0 |
| Variantes des lectures (القراءات) | Table de différences | **Déjà intégré** par Claude Code : 8 riwāyāt de 4 lecteurs (KFGQPC), voir `data/SOURCES.md` et D-12. |
| Générateur de تصريف | Formes théoriques (niveau 0) | Qutrub / libqutrub (github.com/linuxscout/qutrub) ou Camel Morph MSA (LREC 2024) — vérifier licence et couverture |
| Dictionnaires classiques (texte intégral) | État « attestée » (niveau 0) | **OpenITI** (Open Islamicate Texts Initiative, zenodo.org/records/17767721), textes arabes anciens lisibles par machine, licence CC BY-NC-SA 4.0 (usage non commercial). Vérifier dans son fichier de métadonnées la présence des dictionnaires de la liste D-25 (لسان العرب en priorité). |
| Liste des racines de لسان العرب | Contrôle : la racine existe-t-elle dans le dictionnaire classique ? | **lisan345** (github.com/git85hub/lisan345), CSV ; licence non indiquée → demander avant usage |
| **Sources écartées** | Qabas, Arramooz et tout dictionnaire moderne | Décision de l'auteur (D-24) : seuls les dictionnaires classiques comptent pour l'état « attestée ». Qabas n'est utilisable que pour les lemmes qu'il relie explicitement à un dictionnaire classique de la liste D-25, si ce lien est disponible. |
| Mufahras (المعجم المفهرس) | Contrôle externe des comptages | Pas de version numérique connue : le reconstruire (étape 3) |

Remarques :
- Les annotations coupent les clitiques ; le harnais doit **les réassembler en mots entiers**.
- Le texte ʿuthmānī est gardé intact. Fonction de normalisation à niveaux (voir D-03 et D-04) :
  `brut` / `sans signes de récitation` / `sans voyelle finale` / `squelette sans الشكل`.
- Identifiants de mots **stables** : `sourate:verset:position_mot`, avec table de correspondance
  si la numérotation diffère entre traditions.

---

## 4. Modèle de données (SQLite)

```
words(id, sura, aya, pos, text_raw, text_norm_json, root, clitics, segment_id)
segments(id, sura, aya, start_pos, end_pos, pause_level)
root_identity(root, table, category, wazn, tense, voice, quran_forms_json, count,
              unused_forms_json)                                     # §2.0 (états attestée / théorique)
pair_signatures(seg_a, seg_b, ref_form, types, blocks_json, operations_json,
                order_json, code_vector_json)                          # §2.3 (fait foi)
families(id, ref_form, segment_ids_json, isolated, cohesion, cuts_json) # §2.4
matrix_cells(family_id, row_id, col_id, unit_id, form, code_vs_ref)    # §2.5
columns(family_id, col_id, col_type, fillers_json, is_pivot)            # §2.5
templates(family_id, pattern, ambiguous)                                # §2.5
pair_matrix_diff(family_id, seg_a, seg_b, direct_json, induced_json)    # §2.6
constraints(family_id, col_a, col_b, kind, support, p_value)            # §2.7
family_links(family_a, family_b, r3_count, cut_links)                   # §2.8
findings(id, kind, where_json, what_json, support, p_value, status)    # §2.9
form_profiles(ref_form, root, config_hash, n_segments, sufficient,
              typology_json, matrix_json, stats_json)                   # §2.12-b
form_comparisons(form_a, form_b, config_hash, typology_dist, matrix_json,
                 stats_sim, p_values_json, agreement, scope)            # §2.12-c
associations(ref_form, assoc_form, kind, position, count)   # racine non stockée ici (déductible de words)
stats(ref_form, assoc, measure, value, p_value, baseline_info)
variants(word_id, reading, variant_text, variant_type, reciters)       # étape 7
riwayat(id, name, base)
```

---

## 5. Étapes de construction

### Étape 1 — Mise en place et données
- Structure du projet, `pyproject.toml`, `config.yaml` (tous les paramètres de §2 et de
  `DECISIONS.md` avec leur valeur par défaut), `CLAUDE.md`, `DECISIONS.md`.
- Téléchargement et vérification des sources (§3). Remplir `data/SOURCES.md`.
- **Validation** : fichiers présents, hashes notés ; 114 sourates, 6236 versets (numérotation Hafs).

### Étape 2 — Ingestion
- Charger texte + annotations, réassembler les mots, remplir `words`.
- Fonction de normalisation à niveaux.
- **Validation** : aucun mot perdu ni modifié ; le texte reconstruit est égal au texte brut.

### Étape 3 — Index racine/forme + mufahras reconstruit
- Pour chaque racine : formes attestées et occurrences.
- **Validation** : `يقدر` dans 12 versets ; `قوم` environ 150 fois. Si écart, l'écrire dans
  `DECISIONS.md` au lieu de forcer le résultat.
- Comparer QAC et MASAQ ; lister les désaccords de racines.

### Étape 3b — Identité de la racine (niveau 0)
- Installer et tester le générateur de تصريف ; chercher une source lexicale (§3).
- Construire les deux tableaux pour une racine, selon §2.0 (cases utilisées seulement, clic
  vers les formes non employées, ligne des catégories absentes).
- **Validation** : règles de §2.0 ; racine de test قدر.

### Étape 4 — Segmentation
- Découper aux marques de pause et aux fins de verset ; paramètre `pause_level` (D-01).
- **Validation** : chaque mot appartient à exactement un segment.

### Étape 5 — Typologie, familles, matrices (cœur, MVP)
1. Segments de la forme de référence (une ligne par occurrence, §2.10).
2. **Niveau 1** : comparaison directe de toutes les paires, signatures et types R (§2.3).
3. **Niveau 2** : graphe, familles, usages isolés, contrôle de cohésion (§2.4).
4. **Niveau 3** : une matrice par famille, gabarit, types de colonnes (§2.5).
5. Contrôle de cohérence paires ↔ matrice (§2.6).
- **Validation** : cas de test §2.11 ; résultats reproductibles à l'identique.
- Sortie : **fiche blocs A (carte d'identité), B (compagnons), C (familles, gabarits,
  matrices, usages isolés)**.

### Étape 6 — Couche statistique, contraintes et statuts
- Collocations : fréquence, PMI, log-likelihood, pour chaque association.
- Contraintes entre colonnes (§2.7).
- **Contrôle aléatoire obligatoire** : permutations (mots entre segments à taille constante ;
  remplissages entre lignes pour les contraintes), p-valeur empirique, seed fixe.
- Comptage des combinaisons d'opérations → sous-types de تشابه observés.
- Niveau 4 : matrice des familles (§2.8).
- Table `findings` avec statuts observé / décrit / établi (§2.9).
- **Validation** : données jouets à résultat connu ; reproductibilité.

### Étape 6b — Toutes les formes, puis leur comparaison
1. Lancer l'analyse complète (étapes 5 et 6) sur toutes les formes de la racine de
   référence, avec les mêmes réglages (`config_hash`). Formes à un seul segment : fiche
   complète sauf typologie interne et statistique (§2.12-a).
2. Construire le profil de chaque forme (§2.12-b).
3. **D'abord** : comparer toutes les paires de formes de la racine, segment par segment,
   puis selon les trois volets, avec contrôle aléatoire (§2.12-c).
4. **Ensuite** : familles et matrices globales de la racine, construites à partir des
   résultats des paires, avec contrôle de cohérence (§2.12-e).
5. Matrices formes × formes, regroupements, carte d'accord entre volets (§2.12-f).
- **Validation** : la comparaison يقدر / قدير reproduit l'analyse du document ;
  `عالم الغيب` / `علام الغيوب` est classé « même racine, formes différentes » ;
  relancer avec les mêmes réglages donne les mêmes résultats.
- L'analyse de toutes les formes peut être longue : traitement par lots, reprise possible
  après interruption, progression affichée.

### Étape 7 — Les lectures
- Texte de base Hafs + table `variants` ; une lecture = vue complète sur laquelle tout tourne.
- Variantes de mot/lettre (analysées) vs de prononciation (stockées à part).
- Bloc D : chaque résultat est présent dans X lectures sur N ; statut « robuste » si N sur N (§2.9).
- **Validation** : appliquer puis retirer les variantes redonne le texte exact.
- En attente si aucune source de variantes n'est trouvée (D-12).

### Étape 8 — Interface utilisateur
- `cli` : `fiche <forme> --lecture hafs --pause strict`.
- Page d'accueil d'une racine : les deux tableaux du niveau 0 (cases cliquables, ligne des
  catégories absentes), puis accès aux fiches de chaque forme.
- Interface web simple : choisir forme, lecture, réglages ; afficher la matrice (lignes
  dépliables vers le texte arabe et ses références), le gabarit, les contraintes, les blocs A à D ;
  comparer deux formes de la même racine (ex. يقدر / قدير) ; export CSV/PDF.
- **Tableaux allégés** (sauf niveau 0, où toutes les formes employées dans le Coran sont
  visibles sans clic, §2.0) : n'afficher que les colonnes essentielles (forme, fréquence,
  position, statut). Pas de colonne « racine » dans les tableaux d'associations, en
  particulier pour les formes d'autres racines. Les détails (références, codes, racine)
  s'affichent seulement quand l'utilisateur déplie une ligne.
- **Formes proches regroupées** : dans tout tableau qui liste des formes (associations,
  remplissages d'une colonne, gabarits), les formes qui se ressemblent sont placées
  **les unes après les autres** et marquées comme un groupe :
  1. **même base** (E1, E2) : ex. ربي / ربك ، الرزق / رزقا ، على / عليه → groupe serré ;
  2. **même racine, base différente** (E3) : ex. يشاء / شيء → rapprochées **seulement si
     elles sont présentes ensemble dans au moins un même segment** parmi les segments
     de la forme étudiée (pas ailleurs dans le Coran). Elles sont alors rangées côte à
     côte, séparées par un trait plus léger. Deux formes de même racine qui n'apparaissent
     jamais dans un même segment restent dans des groupes séparés (D-16).
     Au déplié, la ligne indique les segments où les deux formes sont ensemble (références).
  Ordre : les groupes sont triés par fréquence totale ; à l'intérieur d'un groupe, les formes
  sont triées par fréquence. Le code E de chaque forme par rapport à la première du groupe
  s'affiche discrètement (ex. « ربك · E2 »). La racine sert au regroupement mais n'est pas
  affichée comme colonne.
  Exemple :
  | Forme | Fréquence | Position |
  |---|---|---|
  | **ربي** | 3 | avant |
  | ↳ ربك · E2 | 2 | avant |
  | **الرزق** | 9 | après |
  | ↳ رزقا · E1 | 1 | après |
- Les matrices ambiguës (§2.5) et les écarts paires ↔ matrice (§2.6) sont signalés visiblement.
- Chaque résultat affiche son statut (observé / décrit / établi / robuste).

### Étape 9 — Aide de l'IA (facultative)
- Résumer une fiche, proposer des formes à comparer.
- L'IA lit uniquement des résultats calculés. Les sorties distinguent : *calculé*,
  *cité d'une source*, *note humaine*.

---

## 6. Questions ouvertes
Toutes dans `DECISIONS.md` (D-01 à D-25). Chaque question indique la valeur par défaut
que le programme applique en attendant la décision de l'auteur.

## 7. Critères de réussite du MVP (étapes 1 à 5, avec 3b)
- Pour la racine قدر : les deux tableaux du niveau 0 sont produits ; chaque occurrence est
  rangée dans une seule case.
- Pour `يقدر` : 12 versets trouvés ; associations avec `يشاء` et `شيء` retrouvées ;
  cas de test §2.11 conformes ; famille et gabarit attendus ; usage isolé détecté.
- Tout est reproductible depuis zéro avec une seule commande.
- Aucun texte coranique modifié ; toutes les données ont une provenance notée.
