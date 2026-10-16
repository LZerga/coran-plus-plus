# DECISIONS.md — Questions de méthode et décisions de l'auteur

Fichier de la **conception** (identifiants D-01, D-02…). Claude Code ne le modifie pas ;
ses propres questions vont dans `QUESTIONS.md` (identifiants Q1, Q2…). En cas de
contradiction entre les deux, ce fichier l'emporte.

Chaque question a une **valeur par défaut** : le programme l'applique (paramètre dans
`config.yaml`) tant que l'auteur n'a pas tranché.

Statuts : **ouverte** · **tranchée** (noter la décision et la date).

---

## A. Le texte et la forme

**D-01 — Définition du segment (المقطع)** · ouverte
Décidé (2026-10-12) : les segments sont ceux du **mushaf Hafs** (marques de pause du
texte Tanzil) et servent pour **toutes** les riwāyāt. Reste ouvert : le niveau des marques
(strict ou souple) et le traitement des extraits du document qui ne correspondent à
aucune marque (34:36 mots 1-8 ; 16:75 mots 4-9).
Quelles marques de وقف terminent un segment ?
Défaut : `pause_level = strict` (pauses principales + fin de verset). Le réglage `souple`
(toutes les marques) est disponible pour comparer.

**D-02 — Forme du texte ou forme du mufahras** · **tranchée (2026-10-12)**
Décision de l'auteur : la forme est prise **telle qu'écrite**, pronoms et lettres collés
compris (لقادرون، له، عليه restent un seul mot). On ne retire jamais les pronoms.
**Exception** : la واو de conjonction (وَ العاطفة) est un **mot à part** (ويقدر = و + يقدر).
C'est aussi l'usage du المعجم المفهرس, ce qui accorde les deux phrases du document.
Contrôle attendu : avec cette règle, يقدر (vocalisé يَقْدِرُ) se trouve dans 12 versets
(13:26, 16:75, 16:76, 17:30, 28:82, 29:62, 30:37, 34:36, 34:39, 39:52, 42:12, 90:5) —
à vérifier par Claude Code.
La فاء (فَ) et toutes les autres lettres collées (ل، ب، ك، س…) **ne sont pas séparées** :
fidélité au texte tel qu'il est (confirmé par l'auteur le 2026-10-12).
Au niveau 0 seulement, ces lettres et pronoms collés sont affichés en couleur et ignorés
pour ranger la forme dans les catégories du الصرف (SPEC §2.0).

**D-03 — Niveau de الشكل dans la forme** · ouverte
Défaut : la forme comprend les lettres et le الشكل intérieur (voyelles, شدة) ; les signes de
récitation et de pause en sont exclus. Le squelette sans الشكل est disponible en comparaison
(il montre quelles formes fusionnent quand on retire le الشكل).

**D-04 — La voyelle finale (الإعراب) fait-elle partie de la forme ?** · **tranchée (2026-10-12)**
Décision de l'auteur : la voyelle finale est **séparée** de la forme. Elle est stockée et
affichée (texte des segments ; trait مرفوع/منصوب/مجرور/مجزوم au niveau 0), mais elle n'est
**pas utilisée** pour les codes E ni pour les comparaisons. Réglage pour la réactiver :
`final_vowel_in_form = false`.
Nuance : quand le mode change des **lettres** (ex. يَقْدِرُونَ → يَقْدِرُوا, chute du ن), ce
n'est pas une voyelle finale : la différence fait partie de la forme (code E1).

---

## B. Le système de codes

**D-05 — Un niveau « même fonction » ?** · ouverte
Exemple : لن / لا (deux racines différentes, même rôle de négation). Selon la règle, c'est E4.
Ajouter un niveau reviendrait à une catégorie de النحو.
Défaut : pas de niveau supplémentaire (E4).

**D-06 — L'ordre de proximité E0 → E3** · ouverte
L'alignement (des paires comme des matrices) préfère E0, puis E1, puis E2, puis E3 (SPEC §2.3 et §2.5). Cet ordre suppose que
« même base + pronom changé » (ربي/ربك) est plus proche que « même racine, autre forme »
(يشاء/شيء). Est-ce l'intention de l'auteur ?
Défaut : ordre E0 > E1 > E2 > E3.

**D-07 — Le « تشابه كلي »** · ouverte
Mêmes éléments, ordre totalement différent, aucun bloc commun. Le document n'en a pas trouvé
d'exemple. Défaut : le programme le détecte et le signale s'il existe (inversion pure, sans bloc E0).

---

## C. Les seuils de la matrice

**D-08 — Quand deux segments appartiennent-ils à la même famille ?** · ouverte
La typologie trace les familles : une paire R1 ou R2 relie ses segments, une paire R3 les
sépare (SPEC §2.4). La question porte donc sur le seuil de R2.
Défaut : au moins 2 éléments communs (E0 à E3) hors pivot, comme la définition de تشابه
du document. Un seuil plus haut donne des familles plus petites et plus homogènes.

**D-09 — Seuil de la colonne « relativement fixe » (تطابق نسبي)** · ouverte
Le document note que l'identité peut devenir relative quand on étudie beaucoup de segments.
Défaut : `seuil_relatif = 75 %` des lignes.

**D-10 — Nombre minimal de lignes pour une contrainte (قيد)** · ouverte
Défaut : `support_min = 3`, plus le contrôle aléatoire obligatoire.
Les formes rares (moins de 3 segments) n'ont donc pas de contraintes : on l'affiche
clairement au lieu de forcer un résultat.

**D-15 — Cohésion minimale d'une famille (problème de l'enchaînement)** · ouverte
A peut ressembler à B et B à C sans que A et C se ressemblent. Une famille formée par
enchaînement peut donc être hétérogène.
Défaut : `cohesion_min = 50 %` des paires internes en R1 ou R2 ; sinon on coupe les liens
les plus faibles (SPEC §2.4). Faut-il un critère plus strict (ex. chaque segment lié à la
majorité des autres) ?

**D-11 — Toujours ancrer l'alignement sur la forme de référence ?** · ouverte
Défaut : oui (colonne pivot). C'est cohérent avec le document, où tout est étudié par
rapport à la forme de référence. Un alignement libre (sans pivot) pourrait montrer d'autres
regroupements.

---

**D-16 — Jusqu'où regrouper les formes proches dans les tableaux ?** · **tranchée (2026-10-12)**
Décision de l'auteur : les formes de même base (ربي / ربك ، الرزق / رزقا) sont toujours
regroupées. Les formes de même racine mais de base différente (يشاء / شيء) sont rapprochées
**seulement si elles sont présentes ensemble dans au moins un même segment parmi les
segments de la forme étudiée**. Sinon, groupes séparés. La recherche dans tout le Coran
est écartée (décision de l'auteur, 2026-10-12).

## D. Méthode générale

**D-12 — Sources des variantes des 7 lectures** · ouverte
Claude Code a trouvé et intégré les textes de 8 riwāyāt de 4 lecteurs (Hafs, Shuʿba,
Warsh, Qālūn, al-Dūrī, al-Sūsī, al-Bazzī, Qunbul ; fichiers KFGQPC via GitHub, licence non
déclarée). Il manque Ibn ʿĀmir, Ḥamza et al-Kisāʾī. Détail dans `QUESTIONS.md` (Q6).
Défaut : l'analyse reste sur Hafs ; les autres riwāyāt servent au bloc D (robustesse).
Reste à décider : ces 8 riwāyāt suffisent-elles ?

**D-13 — Relation entre l'étude d'une forme seule et la comparaison entre formes** · ouverte
Le document dit qu'il n'y a pas encore de vision claire. Défaut : les deux analyses sont
calculées séparément ; la comparaison des formes de la racine (SPEC §2.12) les met
côte à côte sans imposer de modèle.

**D-14 — Théorie des catégories et lien avec les transformations morphologiques** · ouverte
Le document les cite comme pistes futures (transformations entre segments ; lien entre
تحويل صرفي d'une forme à l'autre et logique d'association). Défaut : hors du périmètre
actuel ; à reprendre quand les matrices de plusieurs racines seront disponibles.

---

**D-17 — « Toutes les formes » : de quel ensemble parle-t-on ?** · **tranchée (2026-10-12)**
Décision de l'auteur : toutes les formes de la **racine de référence**, telles qu'attestées
dans le Coran. Pas de comparaison entre racines différentes.
Ordre : les formes sont d'abord comparées **par paires**, puis la **matrice globale** de la
racine est construite à partir de ces résultats (SPEC §2.12-c et §2.12-e).

**D-18 — Forme qui n'apparaît qu'une fois** · **tranchée (2026-10-12)**
Décision de l'auteur : la forme n'est pas exclue. Sa fiche décrit son unique segment ; elle
est comparée directement aux segments des autres formes de la racine ; seuls la typologie
interne (pas de paire possible) et le volet statistique sont vides, avec la mention
« occurrence unique » ou « données insuffisantes ». Seuil du volet statistique :
`occ_min_stats = 3` segments.

**D-19 — Comment dire que deux formes « se ressemblent » ?** · **tranchée provisoirement (2026-10-12)**
Décision de l'auteur : on adopte ces critères pour commencer, et on les revoit au vu des
premiers résultats.
- ton analyse : la part des paires de segments en تطابق, تشابه, اختلاف entre les deux formes ;
- la matrice : les blocs et gabarits qu'elles partagent ;
- la statistique : la part de compagnons qu'elles ont en commun.

**D-20 — Que veut dire « possible en arabe » (niveau 0) ?** · **tranchée (2026-10-12)**
Décision de l'auteur : le dictionnaire numérisé suffit (état « attestée ») ; la méthode
théorique (générateur de تصريف) est gardée en complément (état « théorique »).
Si aucun dictionnaire exploitable n'est trouvé : « théorique » seulement, avec mention claire.

**D-21 — Découpage des deux tableaux du niveau 0** · **tranchée (2026-10-12)** — liste complète validée par l'auteur
Liste complète des catégories dans SPEC §2.0 : en-tête de la racine (ثلاثي/رباعي, nature des
lettres) ; verbes = أوزان (مجرد avec باب، مزيد بحرف/بحرفين/بثلاثة، رباعي، ملحقات) × ماضٍ /
مضارع / أمر × معلوم / مجهول, avec au clic الإسناد، حالة المضارع، التوكيد ; noms = مصادر
(صريح، ميمي، مرّة، هيئة، صناعي)، مشتقات (فاعل، مبالغة، صفة مشبهة، مفعول، تفضيل، زمان، مكان،
آلة)، جوامد، تصغير، نسبة, avec au clic العدد (dont جمع التكسير)، الجنس، التعريف، الإعراب.

**D-22 — Catégories du الصرف** · **tranchée (2026-10-12)**
Décision de l'auteur : elles sont permises **seulement** au niveau 0 pour ranger les formes
dans les deux tableaux d'identité. Elles n'entrent jamais dans l'analyse des corrélations.
Affichage décidé : seules les cases employées dans le Coran sont montrées ; un clic donne les
formes du même genre non employées ; une ligne nomme les catégories entièrement absentes.

**D-23 — Formes de classement ambigu (niveau 0)** · **tranchée (2026-10-12)** — case « ambiguë », sans choix automatique ni validation manuelle
Un même وزن peut servir plusieurs types (فَعِيل : مبالغة ou صفة مشبهة ; مَفْعَل : مصدر ميمي،
اسم زمان ou اسم مكان). Défaut : case « ambiguë » qui nomme les types possibles, sans choix
automatique. L'auteur préfère-t-il trancher lui-même ces cas un par un (validation manuelle
enregistrée) ?

**D-24 — Arabe classique ou arabe en général ?** · **tranchée (2026-10-12)**
Décision de l'auteur : **seuls les dictionnaires classiques** comptent pour l'état
« attestée ». Les sources modernes (Qabas, Arramooz…) sont écartées.

**D-25 — Quels dictionnaires classiques ?** · **tranchée (2026-10-12)**
Décision de l'auteur : la liste proposée est retenue (ordre chronologique) :
كتاب العين (الخليل) ، جمهرة اللغة (ابن دريد) ، تهذيب اللغة (الأزهري) ، الصحاح (الجوهري) ،
مقاييس اللغة (ابن فارس) ، المحكم (ابن سيده) ، أساس البلاغة (الزمخشري) ، لسان العرب
(ابن منظور) ، القاموس المحيط (الفيروزآبادي) ، تاج العروس (الزبيدي).
لسان العرب en priorité ; les autres sont utilisés s'ils sont présents dans OpenITI.
Claude Code note dans `QUESTIONS.md` lesquels sont introuvables.

## E. Correspondance avec le journal de développement (QUESTIONS.md)
| Décision | Question du journal | Note |
|---|---|---|
| D-01 Segment | Q1, Q16 | Constat de Claude Code : le réglage **souple** fait coïncider 5 des 7 phrases du document avec un segment ; le réglage strict, une seule. |
| D-02 Forme du texte / mufahras | Q2, Q14 | Réglage « sans clitiques » de Q2 **écarté** (il retire aussi les pronoms). Nouvelle règle : seule la واو de conjonction est séparée. |
| D-03 الشكل, D-04 voyelle finale | Q7, Q12 | Le الشكل intérieur distingue يَقْدِرُ (قَدَرَ) de يُقَدِّرُ (قَدَّرَ) **sans recours au lemme**. |
| D-06 codes E | Q3, Q4 | Le code actuel utilise le lemme (niveaux 0 à 2) : à remplacer par les codes E de SPEC §2.2. |
| D-12 Lectures | Q6 | Données trouvées par Claude Code : 8 riwāyāt de 4 lecteurs (KFGQPC). |
