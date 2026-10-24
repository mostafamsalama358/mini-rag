"""Create and seed RAG grade, subject, and skill rows on answers_local.

Run from src: python -m fields.madrsty.seed_answers_mapping
"""

from __future__ import annotations

from pathlib import Path

import pyodbc
import yaml

from fields.madrsty.answers_catalog import _connection_string, grade_code_for, subject_code_for

_SKILL_NAMES = {
    "explain": "شرح",
    "summary": "ملخص",
    "example": "مثال",
    "exercise": "تمرين",
    "formula": "قانون",
    "map": "خريطة",
    "grammar": "قواعد",
    "vocabulary": "مفردات",
    "dialogue": "حوار",
    "culture": "ثقافة",
}

_DDL = """
IF OBJECT_ID(N'dbo.RAGGradeMapping', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RAGGradeMapping (
        GradeId uniqueidentifier NOT NULL,
        GradeCode nvarchar(32) NOT NULL,
        CONSTRAINT PK_RAGGradeMapping PRIMARY KEY (GradeId),
        CONSTRAINT FK_RAGGradeMapping_tbl_Grade_GradeId
            FOREIGN KEY (GradeId) REFERENCES dbo.tbl_Grade (pk_Grade_Id)
    );
END

IF OBJECT_ID(N'dbo.RAGSubjectMapping', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RAGSubjectMapping (
        SubjectGradeId uniqueidentifier NOT NULL,
        SubjectCode nvarchar(64) NOT NULL,
        CONSTRAINT PK_RAGSubjectMapping PRIMARY KEY (SubjectGradeId),
        CONSTRAINT FK_RAGSubjectMapping_tbl_SubjectGrade_SubjectGradeId
            FOREIGN KEY (SubjectGradeId) REFERENCES dbo.tbl_SubjectGrade (pk_SubjectGrade_Id)
    );
END

IF OBJECT_ID(N'dbo.RAGIngestOutbox', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RAGIngestOutbox (
        Id uniqueidentifier NOT NULL,
        ContentId nvarchar(256) NOT NULL,
        AttachmentId uniqueidentifier NOT NULL,
        ChecksumSha256 nvarchar(64) NULL,
        ContentVersion int NOT NULL,
        Operation nvarchar(16) NOT NULL,
        Status nvarchar(32) NOT NULL,
        MiniRAGJobId nvarchar(128) NULL,
        LastError nvarchar(2000) NULL,
        CreateDate datetime2 NOT NULL,
        LastModifyDate datetime2 NOT NULL,
        CONSTRAINT PK_RAGIngestOutbox PRIMARY KEY (Id)
    );
    CREATE INDEX IX_RAGIngestOutbox_AttachmentId ON dbo.RAGIngestOutbox (AttachmentId);
    CREATE INDEX IX_RAGIngestOutbox_Status_CreateDate ON dbo.RAGIngestOutbox (Status, CreateDate);
END

IF OBJECT_ID(N'dbo.RAGSkill', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RAGSkill (
        SkillId nvarchar(128) NOT NULL,
        SubjectCode nvarchar(64) NOT NULL,
        Intent nvarchar(32) NOT NULL,
        SkillName nvarchar(64) NOT NULL,
        SortOrder int NOT NULL,
        CONSTRAINT PK_RAGSkill PRIMARY KEY (SkillId)
    );
    CREATE INDEX IX_RAGSkill_SubjectCode ON dbo.RAGSkill (SubjectCode);
END

IF NOT EXISTS (
    SELECT 1 FROM dbo.__EFMigrationsHistory
    WHERE MigrationId = N'20261019131005_AddRagMappingAndOutbox'
)
BEGIN
    INSERT INTO dbo.__EFMigrationsHistory (MigrationId, ProductVersion)
    VALUES (N'20261019131005_AddRagMappingAndOutbox', N'3.1.8');
END

IF NOT EXISTS (
    SELECT 1 FROM dbo.__EFMigrationsHistory
    WHERE MigrationId = N'20261021103600_AddRagSkill'
)
BEGIN
    INSERT INTO dbo.__EFMigrationsHistory (MigrationId, ProductVersion)
    VALUES (N'20261021103600_AddRagSkill', N'3.1.8');
END
"""

_GRADE_SQL = """
SELECT
    CONVERT(varchar(36), g.pk_Grade_Id),
    g.GradeName,
    sec.SectionName
FROM tbl_Grade g
JOIN tbl_Stage st ON st.pk_Stage_Id = g.fk_Stage_Grade_StageId
LEFT JOIN tbl_Section sec ON sec.pk_Section_Id = st.SectionId
WHERE g.Deleted = 0
"""

_SUBJECT_SQL = """
SELECT CONVERT(varchar(36), sg.pk_SubjectGrade_Id), sg.SubjectName
FROM tbl_SubjectGrade sg
WHERE sg.Deleted = 0
"""


def seed() -> None:
    connection = pyodbc.connect(_connection_string(), autocommit=True)
    cursor = connection.cursor()
    cursor.execute(_DDL)
    while cursor.nextset():
        pass

    cursor.execute(_GRADE_SQL)
    grade_rows = cursor.fetchall()
    grades = 0
    skipped_grades: list[str] = []
    for grade_id, grade_name, section_name in grade_rows:
        code = grade_code_for(section_name, grade_name)
        if not code:
            skipped_grades.append(f"{section_name} / {grade_name}")
            continue
        cursor.execute(
            """
            MERGE dbo.RAGGradeMapping AS target
            USING (SELECT CONVERT(uniqueidentifier, ?) AS GradeId, ? AS GradeCode) AS source
            ON target.GradeId = source.GradeId
            WHEN MATCHED THEN UPDATE SET GradeCode = source.GradeCode
            WHEN NOT MATCHED THEN INSERT (GradeId, GradeCode) VALUES (source.GradeId, source.GradeCode);
            """,
            grade_id,
            code,
        )
        grades += 1

    cursor.execute(_SUBJECT_SQL)
    subject_rows = cursor.fetchall()
    subjects = 0
    skipped_subjects: set[str] = set()
    for subject_id, subject_name in subject_rows:
        code = subject_code_for(subject_name)
        if not code:
            skipped_subjects.add(str(subject_name))
            continue
        cursor.execute(
            """
            MERGE dbo.RAGSubjectMapping AS target
            USING (SELECT CONVERT(uniqueidentifier, ?) AS SubjectGradeId, ? AS SubjectCode) AS source
            ON target.SubjectGradeId = source.SubjectGradeId
            WHEN MATCHED THEN UPDATE SET SubjectCode = source.SubjectCode
            WHEN NOT MATCHED THEN INSERT (SubjectGradeId, SubjectCode) VALUES (source.SubjectGradeId, source.SubjectCode);
            """,
            subject_id,
            code,
        )
        subjects += 1

    skills = _seed_skills(cursor)
    connection.close()
    print(f"grades={grades} subjects={subjects} skills={skills}")
    if skipped_grades:
        print("unmapped grades:")
        for name in skipped_grades:
            print("  " + name.encode("unicode_escape").decode())
    if skipped_subjects:
        print("unmapped subjects:")
        for name in sorted(skipped_subjects):
            print("  " + name.encode("unicode_escape").decode())


def _seed_skills(cursor) -> int:
    skills_dir = Path(__file__).resolve().parent / "skills"
    count = 0
    for path in sorted(skills_dir.glob("*.yaml")):
        skill = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        skill_id = str(skill.get("id") or "").strip()
        subject_code = str(skill.get("subject") or "").strip()
        intent = str(skill.get("intent") or "").strip()
        if not skill_id or not subject_code or not intent:
            continue
        cursor.execute(
            """
            MERGE dbo.RAGSkill AS target
            USING (SELECT ? AS SkillId, ? AS SubjectCode, ? AS Intent, ? AS SkillName, ? AS SortOrder) AS source
            ON target.SkillId = source.SkillId
            WHEN MATCHED THEN UPDATE SET
                SubjectCode = source.SubjectCode,
                Intent = source.Intent,
                SkillName = source.SkillName,
                SortOrder = source.SortOrder
            WHEN NOT MATCHED THEN INSERT (SkillId, SubjectCode, Intent, SkillName, SortOrder)
                VALUES (source.SkillId, source.SubjectCode, source.Intent, source.SkillName, source.SortOrder);
            """,
            skill_id,
            subject_code,
            intent,
            _SKILL_NAMES.get(intent, str(skill.get("name") or intent)),
            int(skill.get("order") or 0),
        )
        count += 1
    return count


if __name__ == "__main__":
    seed()
