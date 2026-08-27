import sys

with open("aia_canvas/src/qml/Node.qml", "r") as f:
    content = f.read()

failures = []

if "id: intentTimer" not in content or "Theme.dwellIntentMs" not in content:
    failures.append("Missing intentTimer bound to Theme.dwellIntentMs.")

if "id: hoverDwellTimer" not in content or "Theme.dwellHoverMs" not in content:
    failures.append("Missing hoverDwellTimer bound to Theme.dwellHoverMs.")

if "Behavior on opacity" not in content:
    failures.append("Missing opacity Behavior on Node.qml.")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)
else:
    print("PASS: Timer and Animation invariants verified.")
    sys.exit(0)
