"""Map answers_local grades and subjects onto Madrsty class and skill codes.

``RAGGradeMapping.GradeCode`` is the chat grade id.
``RAGSubjectMapping.SubjectCode`` is the skill subject id.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("uvicorn.error")

_LOCAL_CONNECTION = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=localhost\\SQLEXPRESS;"
    "Database=answers_local;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

_GRADE_CODES = {
    ("مدارس عربيه", "zero"): "G0",
    ("مدارس عربيه", "1- اول"): "G1",
    ("مدارس عربيه", "2- ثاني"): "G2",
    ("مدارس عربيه", "3- ثالث"): "G3",
    ("مدارس عربيه", "4- رابع"): "G4",
    ("مدارس عربيه", "5- خامس"): "G5",
    ("مدارس عربيه", "6- سادس"): "G6",
    ("مدارس عربيه", "7- سابع"): "G7",
    ("مدارس عربيه", "8- ثامن"): "G8",
    ("مدارس عربيه", "9- تاسع"): "G9",
    ("مدارس عربيه", "عاشر"): "G10",
    ("مدارس عربيه", "حادي عشر علمي"): "G11_SCI",
    ("مدارس عربيه", "حادي عشر ادبي"): "G11_LIT",
    ("مدارس عربيه", "ثاني عشر علمي"): "G12_SCI",
    ("مدارس عربيه", "ثاني عشر ادبي"): "G12_LIT",
    ("مدارس عربيه", "ثاني عشر تعليم ديني"): "G12_REL",
    ("جامعي", "كليه الطب"): "UNI_MED",
    ("جامعي", "كليه الصيدله"): "UNI_PHARM",
    ("جامعي", "كليه الهندسه"): "UNI_ENG",
    ("جامعي", "اول"): "UNI_INST",
    ("قدرات", "تست صف"): "APT_EN",
}

_SUBJECT_ALIASES = (
    ("علوم", "science"),
    ("العلوم", "science"),
    ("رياضيات", "math"),
    ("رياضيات 2", "math_2"),
    ("عربي", "arabic"),
    ("لغة عربية", "arabic"),
    ("لغة عريبه", "arabic"),
    ("اللغة العربية", "arabic"),
    ("انجليزي", "english"),
    ("إنجليزي", "english"),
    ("تربية إسلامية", "islamic"),
    ("إسلامية", "islamic"),
    ("قرآن كريم", "quran"),
    ("القرآن الكريم", "quran"),
    ("التربية البدنية - بنات", "pe_girls"),
    ("التربية البدنية-بنات", "pe_girls"),
    ("التربية البدنية - بنين", "pe_boys"),
    ("التربية الفنية", "art"),
    ("الخط العربي", "arabic_calligraphy"),
    ("اجتماعيات", "social"),
    ("الاجتماعيات", "social"),
    ("الذكاء الرقمي", "digital"),
    ("عالمنا الرقمي", "digital"),
    ("عالم التقنية", "digital"),
    ("حاسوب", "digital"),
    ("تقنية المعلومات", "digital"),
    ("بلادي الكويت", "my_kuwait"),
    ("اقتصاد منزلي", "home_economics"),
    ("التربية الموسيقية", "music"),
    ("الدراسات العملية / الديكور - بنات", "practical_decor_girls"),
    ("الدراسات العملية / الديكور - بنين", "practical_decor_boys"),
    ("الدراسات العملية / الكهرباء - بنات", "practical_electric_girls"),
    ("الدراسات العملية / الكهرباء - بنين", "practical_electric_boys"),
    ("الكويت والعالم الإسلامي", "kuwait_world"),
    ("فيزياء", "physics"),
    ("كيمياء", "chemistry"),
    ("أحياء", "biology"),
    ("جيولوجيا", "geology"),
    ("فرنسي", "french"),
    ("لغة فرنسية", "french"),
    ("جغرافيا", "geography"),
    ("جغرافيا واقتصاد", "geography"),
    ("احصاء", "statistics"),
    ("إحصاء", "statistics"),
    ("علم نفس واجتماع", "psychology"),
    ("تاريخ الكويت", "kuwait_history"),
    ("عربي (فنون بلاغة)", "arabic_rhetoric"),
    ("عربي (فنون البلاغة)", "arabic_rhetoric"),
    ("عربي (بلاغة)", "arabic_rhetoric"),
    ("عربي (نحو وصرف)", "arabic_grammar"),
    ("التاريخ الإسلامي", "islamic_history"),
    ("دستور", "constitution"),
    ("اختياري حر", "elective"),
    ("تاريخ العالم الحديث المعاصر", "modern_world_history"),
    ("قضايا البيئة والتنمية المعاصرة", "environment"),
    ("فلسفة", "philosophy"),
    ("التفسير", "tafsir"),
    ("الحديث الشريف", "hadith"),
    ("الفقه التحريري", "fiqh"),
    ("المنطق القديم", "classical_logic"),
    ("عربي (تعبير وقراءة)", "arabic_expression"),
    ("عربي (تعبير وقرائة)", "arabic_expression"),
    ("عربي (عروض وأدب)", "arabic_literature"),
    ("عربي (نقد وبلاغة)", "arabic_criticism"),
)


def normalize_name(value: str | None) -> str:
    """Fold Arabic spelling differences so DB names match the seed aliases."""
    text = str(value or "").strip().lower()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    text = text.replace("ئ", "ء")
    text = text.replace("ة", "ه").replace("ـ", "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([/\-()])\s*", r"\1", text)
    text = re.sub(r"-?الجزء\s*(الاول|الثاني)$", "", text).strip("-").strip()
    return text


_GRADE_CODES = {
    (normalize_name(section), normalize_name(grade)): code
    for (section, grade), code in _GRADE_CODES.items()
}
_SUBJECT_BY_NAME = {normalize_name(name): code for name, code in _SUBJECT_ALIASES}


def grade_code_for(section_name: str | None, grade_name: str | None) -> str | None:
    return _GRADE_CODES.get((normalize_name(section_name), normalize_name(grade_name)))


def subject_code_for(subject_name: str | None) -> str | None:
    return _SUBJECT_BY_NAME.get(normalize_name(subject_name))


def _class_index(classes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in classes if item.get("id")}


def _subject_labels(classes: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in classes:
        for subject in item.get("subjects") or []:
            subject_id = str(subject.get("id") or "")
            if subject_id and subject_id not in labels:
                labels[subject_id] = str(subject.get("label") or subject_id)
    return labels


def _skills_for(subject_code: str, skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [skill for skill in skills if skill.get("subject") == subject_code]


def build_catalog_from_rows(
    rows: list[dict[str, Any]],
    *,
    classes: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    semesters: list[dict[str, Any]],
) -> dict[str, Any]:
    """Group mapper rows into the catalog both frontends render."""
    by_grade = _class_index(classes)
    labels = _subject_labels(classes)
    grades: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    seen_subjects: dict[str, set[str]] = {}

    for row in rows:
        code = str(row.get("grade_code") or "").strip()
        if not code:
            continue
        grade = index.get(code)
        if grade is None:
            meta = by_grade.get(code) or {}
            grade = {
                "grade_id": str(row.get("grade_id") or ""),
                "grade_code": code,
                "grade_name": row.get("grade_name") or meta.get("label") or code,
                "label": meta.get("label") or row.get("grade_name") or code,
                "section": row.get("section_name") or "",
                "stage": row.get("stage_name") or "",
                "section_id": meta.get("section") or "",
                "stage_id": meta.get("stage") or "",
                "subjects": [],
            }
            index[code] = grade
            grades.append(grade)
            seen_subjects[code] = set()

        subject_code = str(row.get("subject_code") or "").strip()
        subject_id = str(row.get("subject_grade_id") or "").strip()
        if not subject_code or not subject_id or subject_id in seen_subjects[code]:
            continue
        seen_subjects[code].add(subject_id)
        grade["subjects"].append(
            {
                "subject_grade_id": subject_id,
                "subject_code": subject_code,
                "subject_name": row.get("subject_name") or labels.get(subject_code) or subject_code,
                "label": labels.get(subject_code) or row.get("subject_name") or subject_code,
                "skills": _skills_for(subject_code, skills),
            }
        )

    flat_skills: list[dict[str, Any]] = []
    seen_skill: set[str] = set()
    for grade in grades:
        for subject in grade["subjects"]:
            for skill in subject["skills"]:
                skill_id = str(skill.get("id") or "")
                if not skill_id or skill_id in seen_skill:
                    continue
                seen_skill.add(skill_id)
                flat_skills.append(skill)

    return {
        "source": "answers_local",
        "grades": grades,
        "semesters": semesters,
        "skills": flat_skills,
    }


def build_catalog_from_pack(
    *,
    classes: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    semesters: list[dict[str, Any]],
) -> dict[str, Any]:
    """Same shape when the mapper tables are not reachable."""
    grades = []
    for item in classes:
        code = str(item.get("id") or "")
        subjects = []
        for subject in item.get("subjects") or []:
            subject_code = str(subject.get("id") or "")
            if not subject_code:
                continue
            subjects.append(
                {
                    "subject_grade_id": "",
                    "subject_code": subject_code,
                    "subject_name": subject.get("label") or subject_code,
                    "label": subject.get("label") or subject_code,
                    "skills": _skills_for(subject_code, skills),
                }
            )
        grades.append(
            {
                "grade_id": "",
                "grade_code": code,
                "grade_name": item.get("label") or code,
                "label": item.get("label") or code,
                "section": "",
                "stage": "",
                "section_id": item.get("section") or "",
                "stage_id": item.get("stage") or "",
                "subjects": subjects,
            }
        )
    return {
        "source": "field_pack",
        "grades": grades,
        "semesters": semesters,
        "skills": [skill for skill in skills if skill.get("subject")],
    }


def _connection_string() -> str:
    import os

    configured = os.environ.get("ANSWERS_SQLSERVER_CONNECTION", "").strip()
    if not configured:
        try:
            from helpers.config import get_settings

            configured = (get_settings().ANSWERS_SQLSERVER_CONNECTION or "").strip()
        except Exception:
            configured = ""
    return configured or _LOCAL_CONNECTION


def _semester_from_row(name: str | None, index: int | None) -> dict[str, str] | None:
    label = str(name or "").strip()
    if index == 1:
        return {"id": "1", "label": label or "الفصل الدراسي الأول"}
    if index == 2:
        return {"id": "2", "label": label or "الفصل الدراسي الثاني"}
    folded = normalize_name(label)
    if "صيف" in folded or "summer" in folded:
        return {"id": "summer", "label": label or "summer"}
    return None


def read_answers_catalog_rows() -> tuple[list[dict[str, Any]], list[dict[str, str]]] | None:
    """Return mapper rows, or None when SQL Server cannot be read."""
    try:
        import pyodbc
    except ImportError:
        logger.warning("pyodbc is not installed; Madrsty catalog stays on the field pack")
        return None

    try:
        connection = pyodbc.connect(_connection_string(), timeout=5)
    except Exception:
        logger.warning("answers_local is not reachable; Madrsty catalog stays on the field pack", exc_info=True)
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                CONVERT(varchar(36), g.pk_Grade_Id),
                m.GradeCode,
                g.GradeName,
                sec.SectionName,
                st.StageName,
                CONVERT(varchar(36), sg.pk_SubjectGrade_Id),
                sm.SubjectCode,
                sg.SubjectName
            FROM RAGGradeMapping m
            JOIN tbl_Grade g ON g.pk_Grade_Id = m.GradeId
            LEFT JOIN tbl_Stage st ON st.pk_Stage_Id = g.fk_Stage_Grade_StageId
            LEFT JOIN tbl_Section sec ON sec.pk_Section_Id = st.SectionId
            LEFT JOIN tbl_SubjectGrade sg
                ON sg.fk_Grade_SubjectGrade_GradeId = g.pk_Grade_Id AND sg.Deleted = 0
            LEFT JOIN RAGSubjectMapping sm ON sm.SubjectGradeId = sg.pk_SubjectGrade_Id
            WHERE g.Deleted = 0
            ORDER BY sec.[Index], st.[Index], g.[Index], sg.[Index], sg.SubjectName
            """
        )
        rows = [
            {
                "grade_id": item[0],
                "grade_code": item[1],
                "grade_name": item[2],
                "section_name": item[3],
                "stage_name": item[4],
                "subject_grade_id": item[5],
                "subject_code": item[6],
                "subject_name": item[7],
            }
            for item in cursor.fetchall()
        ]
        cursor.execute(
            "SELECT SemesterName, [Index] FROM tbl_Semester WHERE Deleted = 0 ORDER BY [Index]"
        )
        semesters = []
        for name, index in cursor.fetchall():
            entry = _semester_from_row(name, int(index) if index is not None else None)
            if entry and entry["id"] not in {row["id"] for row in semesters}:
                semesters.append(entry)
        return rows, semesters
    except Exception:
        logger.warning("RAG mapping tables are not ready; Madrsty catalog stays on the field pack", exc_info=True)
        return None
    finally:
        connection.close()


def load_madrsty_catalog(pack) -> dict[str, Any]:
    """Catalog for mobile and web. Mapper rows win when answers_local is seeded."""
    from services.rag.skills import list_skill_catalog
    from services.FieldRegistry import FieldProfile

    profile = FieldProfile(
        domain_key=pack.key,
        chunking=pack.chunking,
        retrieval=pack.retrieval,
        structural=pack.structural,
        metadata=pack.metadata,
        skills=dict(pack.skills),
        skill_profiles=dict(pack.skill_profiles),
    )
    skills = list_skill_catalog(profile)
    classes = list(pack.classes or [])
    fallback_semesters = list((pack.curriculum or {}).get("semesters") or [])
    loaded = read_answers_catalog_rows()
    if not loaded or not loaded[0]:
        return build_catalog_from_pack(
            classes=classes,
            skills=skills,
            semesters=fallback_semesters,
        )
    rows, semesters = loaded
    return build_catalog_from_rows(
        rows,
        classes=classes,
        skills=skills,
        semesters=semesters or fallback_semesters,
    )
