import sys

with open("aia_canvas/src/qml/Node.qml", "r") as f:
    content = f.read()

failures = []

if "id: intentTimer" not in content or "interval: 250" not in content:
    failures.append("Missing intentTimer with 250ms interval.")

if "id: hoverDwellTimer" not in content or "interval: 1200" not in content:
    failures.append("Missing hoverDwellTimer with 1200ms interval.")

if "isIntentPauseTriggered" not in content:
    failures.append("Missing isIntentPauseTriggered boolean property.")

if "textStreamer.load_file(rootItem.nodeModel.filePath, 500)" not in content:
    failures.append("Missing load_file async logic in dwell timer.")

if "Behavior on width" not in content or "NumberAnimation { duration: 220; easing.type: Easing.OutQuint }" not in content:
    failures.append("Missing width easing OutQuint with 220ms.")

if "Behavior on height" not in content or "NumberAnimation { duration: 220; easing.type: Easing.OutQuint }" not in content:
    failures.append("Missing height easing OutQuint with 220ms.")

if "Behavior on radius" not in content or "NumberAnimation { duration: 220; easing.type: Easing.OutQuint }" not in content:
    failures.append("Missing radius easing OutQuint with 220ms.")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)
else:
    print("PASS: Timer and Animation invariants verified.")
    sys.exit(0)
