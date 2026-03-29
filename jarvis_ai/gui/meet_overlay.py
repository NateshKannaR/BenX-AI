"""
Meet Answer Overlay — floating always-on-top panel that shows AI answers
to questions detected from system audio (Google Meet, calls, etc.)
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, GLib, Pango
import threading
import logging

logger = logging.getLogger(__name__)

_QUESTION_KEYWORDS = (
    "what", "how", "why", "when", "where", "who", "which",
    "explain", "describe", "tell me", "can you", "could you",
    "do you", "are you", "is it", "define", "difference between",
)

AUTO_DISMISS_MS = 30_000   # 30 s auto-dismiss


def is_question(text: str) -> bool:
    t = text.strip().lower()
    return t.endswith("?") or any(t.startswith(kw) for kw in _QUESTION_KEYWORDS)


_CSS = b"""
.mo-root {
    background: linear-gradient(160deg, #0a0f1a 0%, #060b12 100%);
    border: 1px solid rgba(99,179,237,0.28);
    border-radius: 20px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.85), 0 0 0 1px rgba(99,179,237,0.08);
}
.mo-header {
    background: transparent;
    padding: 12px 16px 6px 16px;
}
.mo-badge {
    font-size: 9pt;
    font-family: 'Share Tech Mono', monospace;
    letter-spacing: 0.18em;
    color: #63b3ed;
    text-transform: uppercase;
}
.mo-close-btn {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 0;
    min-width: 24px;
    min-height: 24px;
    color: #718096;
}
.mo-close-btn:hover {
    background: rgba(239,68,68,0.18);
    border-color: rgba(239,68,68,0.4);
    color: #fc8181;
}
.mo-sep {
    background-color: rgba(99,179,237,0.12);
    min-height: 1px;
    margin: 0 14px;
}
.mo-q-label {
    font-size: 9pt;
    font-family: 'Share Tech Mono', monospace;
    color: #f6ad55;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.mo-question {
    font-family: 'Rajdhani', sans-serif;
    font-size: 11pt;
    color: #e2e8f0;
    font-style: italic;
}
.mo-a-label {
    font-size: 9pt;
    font-family: 'Share Tech Mono', monospace;
    color: #68d391;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.mo-answer {
    font-family: 'Rajdhani', sans-serif;
    font-size: 12pt;
    color: #f0fff4;
    line-height: 1.6;
}
.mo-thinking {
    font-family: 'Share Tech Mono', monospace;
    font-size: 10pt;
    color: #4a5568;
}
.mo-copy-btn {
    background: rgba(99,179,237,0.08);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 8px;
    padding: 0;
    min-width: 28px;
    min-height: 28px;
    color: #63b3ed;
}
.mo-copy-btn:hover {
    background: rgba(99,179,237,0.18);
    border-color: rgba(99,179,237,0.4);
}
.mo-timer-bar trough {
    min-height: 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 999px;
}
.mo-timer-bar progress {
    min-height: 3px;
    border-radius: 999px;
    background: linear-gradient(90deg, #3182ce, #63b3ed);
}
"""


class MeetAnswerOverlay(Gtk.Window):
    """
    Floating overlay that shows a detected question + BenX answer.
    Call show_answer(question, answer) to display.
    """

    def __init__(self, application):
        super().__init__()
        self.set_application(application)
        self.set_title("BenX-MeetOverlay")
        self.set_default_size(480, -1)
        self.set_decorated(False)
        self.set_deletable(False)
        self.set_modal(False)
        self._dismiss_timer_id = None
        self._timer_step = 0

        self._apply_css()
        self._build_ui()

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("mo-root")
        self.set_child(root)

        # ── Draggable title bar ───────────────────────────────────────────
        handle = Gtk.WindowHandle()
        root.append(handle)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("mo-header")
        handle.set_child(header)

        badge = Gtk.Label(label="⬤  BenX · Meet Assistant", xalign=0)
        badge.add_css_class("mo-badge")
        badge.set_hexpand(True)
        header.append(badge)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("mo-close-btn")
        close_btn.connect("clicked", lambda _: self.hide())
        header.append(close_btn)

        sep1 = Gtk.Separator()
        sep1.add_css_class("mo-sep")
        root.append(sep1)

        # ── Body ─────────────────────────────────────────────────────────
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_start(16)
        body.set_margin_end(16)
        body.set_margin_top(10)
        body.set_margin_bottom(10)
        root.append(body)

        # Question section
        q_lbl = Gtk.Label(label="Question detected", xalign=0)
        q_lbl.add_css_class("mo-q-label")
        body.append(q_lbl)

        self._question_lbl = Gtk.Label(label="", xalign=0, wrap=True)
        self._question_lbl.add_css_class("mo-question")
        self._question_lbl.set_max_width_chars(55)
        self._question_lbl.set_selectable(True)
        body.append(self._question_lbl)

        sep2 = Gtk.Separator()
        sep2.add_css_class("mo-sep")
        body.append(sep2)

        # Answer section header row
        ans_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        a_lbl = Gtk.Label(label="BenX Answer", xalign=0)
        a_lbl.add_css_class("mo-a-label")
        a_lbl.set_hexpand(True)
        ans_header.append(a_lbl)

        self._copy_btn = Gtk.Button()
        copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
        copy_icon.set_pixel_size(14)
        self._copy_btn.set_child(copy_icon)
        self._copy_btn.add_css_class("mo-copy-btn")
        self._copy_btn.set_tooltip_text("Copy answer")
        self._copy_btn.connect("clicked", self._on_copy)
        ans_header.append(self._copy_btn)
        body.append(ans_header)

        # Scrollable answer area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(320)
        scroll.set_propagate_natural_height(True)
        body.append(scroll)

        self._answer_lbl = Gtk.Label(label="", xalign=0, wrap=True)
        self._answer_lbl.add_css_class("mo-answer")
        self._answer_lbl.set_max_width_chars(55)
        self._answer_lbl.set_selectable(True)
        self._answer_lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        scroll.set_child(self._answer_lbl)

        # Auto-dismiss progress bar
        self._timer_bar = Gtk.ProgressBar()
        self._timer_bar.add_css_class("mo-timer-bar")
        self._timer_bar.set_fraction(1.0)
        self._timer_bar.set_show_text(False)
        root.append(self._timer_bar)

    # ── Public API ────────────────────────────────────────────────────────

    def show_thinking(self, question: str):
        """Show overlay immediately with a 'thinking' placeholder."""
        GLib.idle_add(self._do_show_thinking, question)

    def show_answer(self, question: str, answer: str):
        """Update overlay with the final answer."""
        GLib.idle_add(self._do_show_answer, question, answer)

    # ── Internal ──────────────────────────────────────────────────────────

    def _do_show_thinking(self, question: str):
        self._question_lbl.set_text(f'"{question}"')
        self._answer_lbl.set_markup(
            "<span foreground='#4a5568' font_family='Share Tech Mono' size='small'>"
            "⟳  Thinking…</span>"
        )
        self._copy_btn.set_sensitive(False)
        self._cancel_timer()
        self._timer_bar.set_fraction(1.0)
        self.present()
        GLib.idle_add(self._set_keep_above)

    def _do_show_answer(self, question: str, answer: str):
        self._question_lbl.set_text(f'"{question}"')
        # Render markdown-lite: bold **text**, bullet points
        self._answer_lbl.set_text(answer)
        self._copy_btn.set_sensitive(True)
        self._copy_btn.set_tooltip_text("Copy answer")
        self._start_dismiss_timer()
        self.present()
        GLib.idle_add(self._set_keep_above)

    def _set_keep_above(self):
        surface = self.get_surface()
        if surface:
            try:
                surface.set_keep_above(True)
            except AttributeError:
                pass
        return False

    def _on_copy(self, _widget):
        text = self._answer_lbl.get_text()
        if text:
            Gdk.Display.get_default().get_clipboard().set(text)
            self._copy_btn.set_tooltip_text("Copied ✓")

    def _start_dismiss_timer(self):
        self._cancel_timer()
        self._timer_step = 0
        total_steps = AUTO_DISMISS_MS // 200
        self._total_steps = total_steps

        def _tick():
            self._timer_step += 1
            fraction = max(0.0, 1.0 - self._timer_step / self._total_steps)
            self._timer_bar.set_fraction(fraction)
            if self._timer_step >= self._total_steps:
                self.hide()
                return False
            return True

        self._dismiss_timer_id = GLib.timeout_add(200, _tick)

    def _cancel_timer(self):
        if self._dismiss_timer_id is not None:
            GLib.source_remove(self._dismiss_timer_id)
            self._dismiss_timer_id = None
