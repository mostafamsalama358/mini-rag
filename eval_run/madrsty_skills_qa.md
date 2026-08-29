# Madrsty — أسئلة اختبار بالأجوبة المتوقعة

مصدر الحقائق: chunks في `project_id=5` بعد رفع كتابي الصف 11 (الكويت):
- فرنسي: *Bon voyage* / كتاب الطالب
- جغرافيا واقتصاد: *مبادئ علم الجغرافيا والاقتصاد*

كيف تختبر:
1. الشات: مشروع **Madrsty** → مادة → مهارة.
2. أو API:

```http
POST http://localhost:8000/api/v1/nlp/index/answer/5
X-User-Id: user123
Content-Type: application/json

{"text": "...", "skill_id": "...", "limit": 8}
```

نجاح الإجابة = ذكر النقاط الذهبية أدناه (مش لازم نفس الصياغة).

---

## ملاحظات قبل الاختبار

- **الفرنسي** نصّه نظيف و`field_name` متعلّم (grammar / vocabulary / dialogue / culture / exercise) — استخدم المهارة المطابقة.
- **الجغرافيا** الفهرس عربي مقروء، لكن جسم الصفحات غالباً encoding تالف. اختبر أسئلة **من الفهرس/العناوين** بـ `geography_explain`. مهارات مثل `geography_exercise` غالباً هترجع فاضي لأن أغلب chunks الجغرافيا من غير `field_name`.
- الكتاب كويتي (وزارة التربية، طبعة 2018/2019) مش سوري.

---

## فرنسي

### ف1. مفردات الطقس — `french_vocabulary`

**السؤال:** ما التعبيرات الفرنسية لحالة الطقس في درس «Il fait un temps superbe»؟

**الإجابة المتوقعة (صفحة 88):**

- Il fait chaud / Il fait soleil / Il fait un temps superbe / Il fait beau temps
- Il fait mauvais temps / Il y a du vent / Il pleut / Il neige / Il gèle
- Il fait frais / Il fait froid / Il fait gris
- La température est haute (45 °C) ≠ basse (3 °C)
- La mer est agitée ≠ calme

---

### ف2. الجنسيات — `french_grammar`

**السؤال:** حسب درس الجنسيات: كيف نقول صفة الجنسية للكويت وفرنسا ومصر؟ وما اسم البلد؟

**الإجابة المتوقعة (صفحة 32):**

| صفة (م/ف) | البلد |
|---|---|
| koweïtien / koweïtienne | Le Koweït |
| français / française | La France |
| égyptien / égyptienne | L’Égypte |

أمثلة الكتاب: *Je suis français et toi? — Je suis Koweïtien.*

أيضاً في الكتاب: saoudien (L’Arabie-Saoudite)، syrien (La Syrie)، libanais (Le Liban)، omanais (Oman)، américain (Les États-Unis)، belge (La Belgique).

---

### ف3. الماضي المركب — `french_grammar`

**السؤال:** اشرح تكوين passé composé: متى avoir ومتى être؟ أعطِ أمثلة من الكتاب.

**الإجابة المتوقعة (صفحة 145):**

- **Avoir + participe passé:** j’ai aimé، tu as dit، il a fait، elle a lu، nous avons eu، vous avez bu، ils ont pris، elles ont mis
- **Être + participe passé:** je suis rentré(e)، tu es allé(e)، il est parti، elle est sortie، nous sommes venus، vous êtes restés، ils sont montés، elles sont descendues
- مؤشرات الزمن: Hier… / La semaine passée… / Le mois dernier…
- أمثلة سياقية: Nous avons fait / visité — Nous sommes allés / rentrés

---

### ف4. حوار التعارف — `french_dialogue`

**السؤال:** لخّص حوار الـ tchatche بين Hassan و Jean-Pierre. من هو Jules Verne؟

**الإجابة المتوقعة (صفحة 30):**

- Jules Verne (1828–1905): كاتب فرنسي.
- Jean-Pierre فرنسي، يسكن باريس، في ثانوية «Jules Verne».
- Hassan كويتي (Koweïtien) وتلميذ ثانوي (lycéen).
- salutations: Bonjour, tu parles français? — Oui, un peu…
- النهاية: Heureux de faire ta connaissance / À demain / au revoir.

---

### ف5. مفردات الحوار — `french_vocabulary`

**السؤال:** ماذا تعني Une tchatche؟ وما أضداد Bonjour و Un peu؟

**الإجابة المتوقعة (صفحة 31):**

- Une tchatche = Une conversation sur Internet
- Bonjour / Le matin ≠ Bonsoir / Le soir
- Heureux = Content
- Un peu ≠ Beaucoup
- مهن: Directeur, Policier, Secrétaire, Docteur, Professeur (+ Retraité, Employé, Femme au foyer للبحث في القاموس)

---

### ف6. أوامر الصف — `french_dialogue` أو `french_explain`

**السؤال:** ماذا يقول الأستاذ في الصف في درس Premier contact؟

**الإجابة المتوقعة (صفحة 24):**

- Ouvrez le livre de français!
- Silence, écoutez bien!
- Ecrivez le mot!
- Regardez l’image!
- Bravo!!! Applaudissez!

---

### ف7. وسائل النقل — `french_exercise`

**السؤال:** كيف نسأل ونقول وسيلة النقل للذهاب إلى المدرسة حسب تمرين Communication؟

**الإجابة المتوقعة (صفحة 146):**

أسئلة: Comment est-ce que tu vas au lycée? / On y va en métro? / On prend la voiture?

أجوبة الكتاب: Non, on va en train. / À vélo. / Je vais en bus. / J’y vais à pied. / Non, on prend un taxi.

---

### ف8. السكن (ثقافة) — `french_culture`

**السؤال:** أين يفضّل الطلاب الأجانب السكن حسب فقرة Culture؟ وما أنواع المساكن المذكورة؟

**الإجابة المتوقعة (صفحة 96):**

- Les étudiants étrangers préfèrent loger dans une chambre d’hôte.
- أنواع: maisons, appartements, studios, villas.

---

## جغرافيا

استخدم **`geography_explain`**. الإجابة الذهبية من **الفهرس** (صفحات 11 و13) وعناوين الخرائط (صفحة 43). لا تعتمد على تعريفات مطوّلة من جسم الفصل — النص هناك غالباً غير مقروء.

### ج1. المجموعة الشمسية — `geography_explain`

**السؤال:** ما موضوعات فصل المجموعة الشمسية في الكتاب؟

**الإجابة المتوقعة (فهرس ص. 11):**

1. الشمس مصدر إشعاع وحرارة
2. الكواكب الصخرية والكواكب الغازية
3. النشاط (الشمسي)

---

### ج2. خصائص الكرة الأرضية — `geography_explain`

**السؤال:** عدد الخصائص العامة للكرة الأرضية كما في فهرس الكتاب.

**الإجابة المتوقعة (فهرس ص. 11):**

1. أبعاد الأرض ومقاييسها
2. دورة الأرض المحورية
3. الشبكة الجغرافية
4. دوران الأرض حول الشمس
5. دورة القمر حول الأرض

---

### ج3. صخور القشرة — `geography_explain`

**السؤال:** ما أقسام صخور القشرة الأرضية في الكتاب؟

**الإجابة المتوقعة (فهرس ص. 11):**

1. الصخور النارية
2. الصخور الرسوبية
3. الصخور المتحولة

وبعدها: القوى التي تؤثر في تشكيل سطح الأرض (داخلية/باطنية، وفجائية سريعة…).

---

### ج4. الغلاف الجوي والطقس — `geography_explain`

**السؤال:** ماذا يدرس فصل الغلاف الجوي؟ وما عناصر الطقس والمناخ المذكورة؟

**الإجابة المتوقعة (فهرس ص. 13):**

- تعريف الغلاف الجوي
- الطبقات الرأسية للغلاف الجوي وخصائصها العامة
- عناصر الطقس والمناخ:
  1. الإشعاع الشمسي
  2. حرارة الهواء
  3. الضغط الجوي
  4. الرياح
  5. الرطوبة والتكاثف والتساقط

---

### ج5. الأقاليم الحيوية — `geography_explain`

**السؤال:** ما أنواع أقاليم الغابات في العالم حسب فهرس الكتاب؟

**الإجابة المتوقعة (فهرس ص. 13):**

- الغابات الحارة الاستوائية
- الغابات الحارة الموسمية
- الغابات المعتدلة الدفيئة (إقليم غابات البحر المتوسط، إقليم غابات الصين)
- الغابات المعتدلة الباردة النفضية والمخروطية (الصنوبرية)
- ثم إقليم الحشائش (السافانا الحارة الطويلة، والحشائش المعتدلة القصيرة)

---

### ج6. أنواع الخرائط — `geography_map` أو `geography_explain`

**السؤال:** ما أنواع الخرائط المذكورة في الكتاب؟

**الإجابة المتوقعة (عناوين إنجليزية نجت في النص، ص. 43 تقريباً):**

- Population Maps
- Settlement Maps
- Political & Administrative maps
- Historical Maps
- Relief Map
- Geological Maps

لو `geography_map` رجّع فاضي (فلتر `field=figure`)، أعد نفس السؤال بـ `geography_explain`.

---

### ج7. بيانات الكتاب — `geography_summary`

**السؤال:** ما اسم الكتاب والمرحلة والجهة الناشرة؟

**الإجابة المتوقعة (صفحات الغلاف 2–3):**

- مبادئ علم الجغرافيا والاقتصاد
- الصف الحادي عشر / الفصل الأول
- وزارة التربية — دولة الكويت
- الطبعة الثانية: 2016/2017 ثم 2018/2019 م (1439 هـ)

---

## حالات سلبية (مهم تختبرها)

| السؤال | skill_id | المتوقع |
|---|---|---|
| اشرح passé composé | `geography_explain` | ما يجيبش من كتاب الفرنسي؛ يعتذر أو سياق جغرافيا فقط |
| ما عناصر الطقس؟ | `french_vocabulary` | ما يجيبش فهرس الجغرافيا |
| جرعة Congestal / أي دواء | أي skill مدرستي | لا إجابة صيدلية؛ خارج الكوربس |

---

## جدول سريع للنسخ في الشات

| # | skill_id | السؤال |
|---|---|---|
| ف1 | french_vocabulary | ما تعبيرات الطقس في درس Il fait un temps superbe؟ |
| ف2 | french_grammar | صفات الجنسية: الكويت، فرنسا، مصر؟ |
| ف3 | french_grammar | متى avoir ومتى être في passé composé؟ أمثلة من الكتاب |
| ف4 | french_dialogue | لخص حوار Hassan و Jean-Pierre. من Jules Verne؟ |
| ف5 | french_vocabulary | معنى Une tchatche وأضداد Bonjour و Un peu |
| ف6 | french_dialogue | أوامر الأستاذ في Premier contact |
| ف7 | french_exercise | كيف تذهب إلى lycée؟ أسئلة وأجوبة الكتاب |
| ف8 | french_culture | أين يفضل الطلاب الأجانب السكن؟ |
| ج1 | geography_explain | موضوعات فصل المجموعة الشمسية |
| ج2 | geography_explain | الخصائص العامة للكرة الأرضية في الفهرس |
| ج3 | geography_explain | أقسام صخور القشرة الأرضية |
| ج4 | geography_explain | عناصر الطقس والمناخ في فصل الغلاف الجوي |
| ج5 | geography_explain | أنواع أقاليم الغابات في الفهرس |
| ج6 | geography_explain | أنواع الخرائط في الكتاب |
| ج7 | geography_summary | اسم الكتاب والمرحلة والناشر |
