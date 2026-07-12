from src.notifier import build_alert_actions


def test_build_alert_actions_high():
    actions = build_alert_actions("HIGH")
    assert len(actions) == 2
    assert actions[0].type == "slack"
    assert actions[1].type == "ticket"


def test_build_alert_actions_low():
    actions = build_alert_actions("LOW")
    assert len(actions) == 1
    assert actions[0].type == "dashboard"
