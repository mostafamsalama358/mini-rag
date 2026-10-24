from fields.madrsty.answers_catalog import (
    build_catalog_from_rows,
    grade_code_for,
    normalize_name,
    subject_code_for,
)


def test_grade_and_subject_codes_match_the_live_names():
    assert grade_code_for("مدارس عربية", "8- ثامن") == "G8"
    assert grade_code_for("مدارس عربية", "حادي عشر أدبي") == "G11_LIT"
    assert grade_code_for("جامعي", "كلية الطب") == "UNI_MED"
    assert grade_code_for("ielts", "British council") is None
    assert subject_code_for("العلوم") == "science"
    assert subject_code_for("التربية البدنية-بنات") == "pe_girls"
    assert subject_code_for("عربي ( نحو وصرف ) - الجزء الأول") == "arabic_grammar"
    assert subject_code_for("حاسوب") == "digital"
    assert subject_code_for("الاجتماعيات") == "social"
    assert subject_code_for("لغة عريبه") == "arabic"
    assert subject_code_for("عربي ( تعبير وقرائة)") == "arabic_expression"
    assert subject_code_for("test") is None
    assert normalize_name("إسلامية") == normalize_name("اسلاميه")


def test_catalog_groups_mapper_rows_and_attaches_skills():
    catalog = build_catalog_from_rows(
        [
            {
                "grade_id": "g-1",
                "grade_code": "G8",
                "grade_name": "8- ثامن",
                "section_name": "مدارس عربية",
                "stage_name": "متوسط",
                "subject_grade_id": "s-1",
                "subject_code": "science",
                "subject_name": "علوم",
            },
            {
                "grade_id": "g-1",
                "grade_code": "G8",
                "grade_name": "8- ثامن",
                "section_name": "مدارس عربية",
                "stage_name": "متوسط",
                "subject_grade_id": "s-2",
                "subject_code": "science",
                "subject_name": "علوم - الجزء الثاني",
            },
        ],
        classes=[{"id": "G8", "label": "الصف الثامن", "section": "arabic_schools", "stage": "middle", "subjects": [{"id": "science", "label": "العلوم"}]}],
        skills=[{"id": "science_explain", "name": "Explain", "subject": "science", "intent": "explain"}],
        semesters=[{"id": "1", "label": "الفصل الدراسي الأول"}],
    )
    assert catalog["source"] == "answers_local"
    assert catalog["grades"][0]["label"] == "الصف الثامن"
    assert catalog["grades"][0]["stage_id"] == "middle"
    assert len(catalog["grades"][0]["subjects"]) == 2
    assert catalog["skills"][0]["id"] == "science_explain"
    assert catalog["grades"][0]["subjects"][0]["skills"][0]["intent"] == "explain"
