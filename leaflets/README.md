# Egyptian commercial leaflets (Excel-enriched)

Generated from local Excel sheets + leaflet templates.
Clinical sheet matching uses INN / actives (not brand names).

## Feature 020 — recommend metadata (sole ingest path)

For need-based recommendations, carry `indication_tags`, `product_line`, and safety labels
(`pregnancy_safety` / `breastfeeding_safety` / `safety_labels`) into chunk metadata via the
**existing** ingest/index path (006/017). Do **not** create a second ingest pipeline.
Seed tag vocabulary lives in `src/fields/pharmacy/indication_tags.yaml`.
After enriching leaflets/index metadata, reindex the project before expecting retrieval-backed
recommend evidence (pack seeds can still propose in-corpus candidates).

| File | Brand | INN | Matched SKU | Interactions |
| --- | --- | --- | --- | --- |
| `01_panadol_paracetamol_500.txt` | Panadol Advance | Paracetamol | PANADOL ADVANCE 500 MG 24 TABLETS | 12 |
| `02_panadol_cold_flu_day.txt` | Panadol Cold & Flu Day | Paracetamol * Caffeine * Phenylephrine | PANADOL COLD & FLU DAY 24 F.C. TABS. | 12 |
| `03_panadol_sinus_relief_pe.txt` | Panadol Sinus Relief PE | Paracetamol * Phenylephrine | PANADOL SINUS RELIEF PE 24 TABS. | 12 |
| `51_panadol_extra.txt` | Panadol Extra | Paracetamol * Caffeine | PANADOL EXTRA 24 F.C. TABS. | 12 |
| `52_panadol_joint.txt` | Panadol Joint | Paracetamol | PANADOL JOINT 24 ER TABLETS | 12 |
| `53_panadol_migraine.txt` | Panadol Migraine | Paracetamol * Caffeine | PANADOL MIGRAINE 30 F.C.TABS. | 12 |
| `54_panadol_acute_head_cold.txt` | Panadol Acute Head Cold | Paracetamol * Guaifenesin * Phenylephrine | PANADOL ACUTE HEAD COLD 20 F.C.TABS | 12 |
| `55_panadol_cold_flu_all_in_one.txt` | Panadol Cold & Flu All In One | Paracetamol * Guaifenesin * Phenylephrine | PANADOL COLD & FLU (ALL IN ONE) 24 F.C. TABS.(N/A YET) | 12 |
| `56_panadol_vapour_release.txt` | Panadol Cold & Flu Vapour Release | Paracetamol * Guaifenesin * Phenylephrine | PANADOL COLD & FLU VAPOUR RELEASE 10 SACHETS | 12 |
| `04_cetal_cold_flu_day.txt` | Cetal Cold & Flu Day | Paracetamol * Caffeine * Phenylephrine | CETAL COLD & FLU 20 CAPLETS | 12 |
| `05_flurest_n.txt` | Flurest-N | Paracetamol * Chlorpheniramine Maleate * Phenylephrine | FLUREST N 20 TABS. | 12 |
| `06_congestal.txt` | Congestal | Paracetamol * Pseudoephedrine * Chlorpheniramine Maleate | CONGESTAL 20 TABS. | 12 |
| `07_sine_up.txt` | Sine-Up | Pseudoephedrine * Triprolidine | SINE UP 20 TAB. | 12 |
| `08_bradozen.txt` | Bradozen | Bromelain * Trypsin * Rutoside | BRADOZEN 0.5MG 20 LOZENGES | 0 |
| `09_notussil.txt` | Notussil | Levodropropizine | NOTUSSIL 4MG/ML SUSP. 60ML | 0 |
| `11_daflon_500.txt` | Daflon 500 | Diosmin * Hesperidin | DAFLON 500MG 30 F.C. TABS. | 12 |
| `12_daflon_1000.txt` | Daflon 1000 | Diosmin * Hesperidin | DAFLON 1000MG 30 F.C. TABS. | 12 |
| `13_controloc_20.txt` | Controloc 20 | Pantoprazole | CONTROLOC 20MG 14 GASTRO-RESISTANT TABS. | 12 |
| `14_jeparilon.txt` | Jeparilon | Famotidine * Calcium Carbonate * Magnesium Hydroxide | JEPARILON 10 MG 20 CHEW. TABS. | 12 |
| `15_anaseziago.txt` | Anaseziago | Lidocaine * Prilocaine | ANASEZIAGO CREAM 30 GM | 1 |
| `16_adol_500.txt` | Adol | Paracetamol | ADOL 500MG 24 CAPLETS | 12 |
| `17_cataflam_25.txt` | Cataflam | Diclofenac Potassium * Diclofenac | CATAFLAM 50 MG 20 SUGAR C.TABS. | 12 |
| `18_brufen_400.txt` | Brufen | Ibuprofen | BRUFEN 400 MG 30 TABS. | 12 |
| `19_antinal.txt` | Antinal | Nifuroxazide | ANTINAL 200MG 24 CAPS. | 0 |
| `20_flagyl_500.txt` | Flagyl | Metronidazole | FLAGYL 500MG 20 TAB. | 12 |
| `21_augmentin_1g.txt` | Augmentin | Amoxicillin * Clavulanic Acid | AUGMENTIN 1 GM 14 F.C.TABS. | 12 |
| `22_hibiotic_1g.txt` | Hi-Biotic | Amoxicillin * Clavulanic Acid | HIBIOTIC 1 GM 16 TABS. | 12 |
| `23_zithrokan_500.txt` | Zithrokan | Azithromycin | ZITHROKAN 500 MG 3 CAPS. | 12 |
| `24_ciprobay_500.txt` | Ciprobay | Ciprofloxacin | CIPROBAY 500MG 10 F.C.TAB. | 12 |
| `25_risek_20.txt` | Risek | Omeprazole | RISEK 20 MG 14 CAPS. | 12 |
| `26_gaviscon.txt` | Gaviscon Advance | Sodium Alginate * Potassium Bicarbonate * Alginate | GAVISCON ADVANCE 150 ML | 12 |
| `27_motilium_10.txt` | Motilium | Domperidone | MOTILIUM 10MG 40 F.C.TAB. | 12 |
| `28_buscopan.txt` | Buscopan | Hyoscine Butylbromide * Hyoscine | BUSCOPAN PLUS 20 F.C.TAB. (N/A) | 12 |
| `29_concor_5.txt` | Concor | Bisoprolol | CONCOR 5 MG 30 F.C. TABS | 12 |
| `30_norvasc_5.txt` | Norvasc | Amlodipine | NORVASC 5MG 30 TAB. | 12 |
| `31_glucophage_500.txt` | Glucophage | Metformin | GLUCOPHAGE 500 MG 50 F.C.TABS. | 12 |
| `32_amaryl_2.txt` | Amaryl | Glimepiride | AMARYL 2 MG 30 TABS. | 12 |
| `33_lipitor_20.txt` | Lipitor | Atorvastatin | LIPITOR 20 MG 28 TABS. | 12 |
| `34_plavix_75.txt` | Plavix | Clopidogrel | PLAVIX 75 MG 28 F.C.TABS. | 12 |
| `35_aspocid_75.txt` | Aspocid | Aspirin * Acetylsalicylic Acid | ASPOCID 75MG 20 TAB. | 12 |
| `36_telfast_120.txt` | Telfast | Fexofenadine | TELFAST 120MG 20 F.C. TABS. | 12 |
| `37_claritine_10.txt` | Claritine | Loratadine | CLARITINE 10MG 20 TAB. | 12 |
| `38_otrivin_0_1.txt` | Otrivin | Xylometazoline | OTRIVIN 0.1% ADULT NASAL DROPS 15 ML | 6 |
| `39_ventolin_inhaler.txt` | Ventolin | Salbutamol * Albuterol | VENTOLIN EVOHALER 100MCG/ACTUATION INHALER | 12 |
| `40_singulair_10.txt` | Singulair | Montelukast | SINGULAIR 10MG 14 F.C. TAB. | 12 |
| `41_diflucan_150.txt` | Diflucan | Fluconazole | DIFLUCAN 150 MG 1 CAPS. | 12 |
| `42_lamisil_250.txt` | Lamisil | Terbinafine | LAMISIL 250MG 14 TAB. | 12 |
| `43_duphaston_10.txt` | Duphaston | Dydrogesterone | DUPHASTON 10 MG 60 F.C.TABS. | 12 |
| `44_folic_acid_5.txt` | Folic Acid | Folic Acid | FOLIC ACID (EIPICO) 5 MG 20 TAB. | 10 |
| `45_ferrotron.txt` | Ferrotron | Iron * Ferrous * Folic Acid | FERROTRON 30 CAPS. | 12 |
| `46_milga.txt` | Milga | Benfotiamine * Pyridoxine * Cyanocobalamin | MILGA 40 F.C.TABS. | 12 |
| `47_smecta.txt` | Smecta | Diosmectite | SMECTA 20% SUSPENSION 120 ML | 0 |
| `48_enterogermina.txt` | Enterogermina | Bacillus Clausii | ENTEROGERMINA 2 BILLION/5ML ORAL SUSP. 10 MINI BOTTLES | 0 |
| `49_strepsils.txt` | Strepsils | Amylmetacresol * Dichlorobenzyl | STREPSILS HONEY & LEMON 24 LOZENGES | 0 |
| `50_comtrex.txt` | Comtrex | Paracetamol * Pseudoephedrine * Chlorpheniramine Maleate | COMTREX ACUTE HEAD COLD 20 F.C.TAB. | 12 |
| `10_tussigreen.txt` | Tussigreen | Ivy * Ivy Extract | proxy:TUSSIGLOBE 0.3% SYRUP 120 ML | 0 |
