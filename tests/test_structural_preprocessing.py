from training.robust_features import clean_text, RobustText


def test_reference_masking_preserves_issue_and_unicode():
    text='මගේ order SIMQ-A3BCD45 late 😢'
    assert clean_text(text,mask_references=True)=='මගේ order [REFERENCE] late 😢'


def test_explicitly_resolved_quote_removed():
    text='My app crashes.\nOn an earlier date, support wrote:\n> The unrelated case is resolved.\n> Driver threatened me.'
    assert clean_text(text,resolved_quotes=True).strip()=='My app crashes.'


def test_active_quote_preserved():
    text='Please read this message:\n> The driver threatened me just now.'
    assert clean_text(text,resolved_quotes=True)==text


def test_normalizer_does_not_remove_current_resolved_word():
    text='The old case was resolved but the driver is currently threatening me.'
    assert clean_text(text,resolved_quotes=True)==text


def test_metadata_ignored_in_new_features():
    transformer=RobustText(mask_references=True,resolved_quotes=True)
    row={'channel':'chat','text':'என் உணவு வரவில்லை','subject':''}
    assert transformer.transform([row])==transformer.transform([{**row,'category':'spam_irrelevant','ticket_id':'wrong','language':'en'}])
