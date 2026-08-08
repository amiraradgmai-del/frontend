from app.services.advisor import terms
from app.services.advisor_rules import evaluate_question


def test_knowledge_based_company_questions_are_in_scope():
    result = evaluate_question("معافیت مالیاتی شرکت دانش بنیان چگونه است؟")
    assert result.out_of_scope is False


def test_common_tax_typos_are_detected_and_normalized():
    result = evaluate_question("شرکت دانشبیان چه اعتبار مالیاتی دارد؟")
    assert result.out_of_scope is False
    assert "مالیات" in terms("مالیایت شرکت چطور محاسبه می‌شود؟")
