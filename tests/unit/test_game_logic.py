from app.services.game_logic import decode_result_mask, encode_result_mask, evaluate_guess


def test_evaluate_guess_with_duplicate_letters():
    result = evaluate_guess("allee", "eagle")
    assert result == ["present", "present", "absent", "present", "correct"]


def test_encode_decode_mask_roundtrip():
    states = ["correct", "present", "absent", "correct", "absent"]
    mask = encode_result_mask(states)
    assert mask == "CPACA"
    assert decode_result_mask(mask) == states
