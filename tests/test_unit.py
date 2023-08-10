from .cases import Cases

cases = Cases.cases


def test_cases():
    for case in cases:
        case()
