from pathlib import Path


def test_question_sidebar_is_visible_near_reader_viewport():
    source = Path("src/extension/immersive/readingSession.cjs").read_text(encoding="utf-8")

    assert "#question-sidebar {" in source
    sidebar_css = source.split("#question-sidebar {", 1)[1].split("}", 1)[0]

    assert "position: sticky" in sidebar_css or "position: fixed" in sidebar_css
    assert "top:" in sidebar_css
    assert "#question-sidebar.is-active" in source


def test_question_sidebar_supports_mouse_dragging_with_cleanup():
    source = Path("src/extension/immersive/readingSession.cjs").read_text(encoding="utf-8")

    assert "cursor: grab" in source
    assert "cursor: grabbing" in source
    assert "user-select: none" in source
    assert "function setupSidebarDragging" in source
    assert "function clampSidebarPosition" in source
    assert "pointerdown" in source
    assert "pointermove" in source
    assert "pointerup" in source
    assert "pointerType !== 'mouse'" in source
    assert "cleanupSidebarDragging" in source
    assert "removeEventListener('pointermove'" in source


def test_question_cards_are_selectable_and_not_drag_handles():
    source = Path("src/extension/immersive/readingSession.cjs").read_text(encoding="utf-8")

    assert "user-select: text" in source
    assert "cursor: text" in source
    assert "function isSidebarDragBlockedTarget" in source
    assert ".closest('.question-card" in source
    assert "isSidebarDragBlockedTarget(event.target)" in source


def test_question_sidebar_hides_internal_fallback_labels():
    source = Path("src/extension/immersive/readingSession.cjs").read_text(encoding="utf-8")

    assert "function formatQuestionCardText" in source
    assert "function isVisibleQuestionLabel" in source
    assert "uncategorized" in source
    assert "unlabelled" in source
    assert "其他" in source
    assert "formatQuestionCardText(item)" in source
