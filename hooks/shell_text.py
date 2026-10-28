#!/usr/bin/env python3
"""The part of a Bash command the shell will run, for guards that match on words.

A guard that scans the raw command string cannot tell a push that skips the hooks
from a commit whose message mentions the flag: both carry it. Found while porting
graphify's hook, which had the same bug as a nudge (its #3121); here it is a block,
and it fired on a real commit message that named the short flag of a dry run, refused
as a bypass. A config whose types gate runs `tsc` refused `git commit -m "make tsc
pass"` the same way.

`executed` returns the command with what the shell never runs taken out: a quoted
word that holds whitespace (a message, not a flag or a path), the body of a heredoc,
and a comment. The first word of each segment is always kept, quoted or not, so a
quoted program path still reads as the program. What a shell does run from inside a
string is put back as its own segment: `bash -c "..."`, `eval "..."`, a heredoc fed
to a shell, and `$(...)` or backticks inside double quotes. Segments are joined by
newlines, so a guard's `[^;&|\\n]*` still stops at the segment's end.
"""
import os

SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SEPARATORS = ";&|\n()"


def executed(cmd: str) -> str:
    segments = []
    _parse(cmd or "", segments)
    return "\n".join(" ".join(words) for words in segments if words)


def _substitutions(text: str, segments: list) -> None:
    i = 0
    while i < len(text):
        if text.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[j], 0)
                j += 1
            _parse(text[i + 2:j - 1], segments)
            i = j
            continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            end = len(text) if end < 0 else end
            _parse(text[i + 1:end], segments)
            i = end + 1
            continue
        i += 1


def _parse(cmd: str, segments: list) -> None:
    words, heredocs = [], []
    word, prose, started = [], False, False
    i, n = 0, len(cmd)

    def runs_shell() -> bool:
        return bool(words) and os.path.basename(words[0]) in SHELLS

    def end_word() -> None:
        nonlocal word, prose, started
        text = "".join(word)
        inline = runs_shell() and words[-1:] == ["-c"]
        if started and (inline or words[:1] == ["eval"]):
            _parse(text, segments)
        elif started and (not prose or not words):
            words.append(text)
        word, prose, started = [], False, False

    def end_segment() -> None:
        nonlocal words
        end_word()
        segments.append(words)
        words = []

    while i < n:
        c = cmd[i]
        if c == "\\" and i + 1 < n:
            if cmd[i + 1] != "\n":
                word.append(cmd[i + 1])
                started = True
            i += 2
            continue
        if c in "'\"":
            end = i + 1
            while end < n and cmd[end] != c:
                end += 2 if c == '"' and cmd[end] == "\\" else 1
            body = cmd[i + 1:end]
            if c == '"':
                _substitutions(body, segments)
            word.append(body)
            prose = prose or any(ch.isspace() for ch in body)
            started = True
            i = end + 1
            continue
        if c == "#" and not started:
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        if cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            end_word()
            i += 2
            strip_tabs = i < n and cmd[i] == "-"
            i += 1 if strip_tabs else 0
            while i < n and cmd[i] in " \t":
                i += 1
            start = i
            while i < n and not cmd[i].isspace() and cmd[i] not in SEPARATORS:
                i += 1
            heredocs.append((cmd[start:i].strip("'\""), strip_tabs, runs_shell()))
            continue
        if c == "\n" and heredocs:
            end_segment()
            i += 1
            for delimiter, strip_tabs, run in heredocs:
                body = []
                while i < n:
                    eol = cmd.find("\n", i)
                    eol = n if eol < 0 else eol
                    line = cmd[i:eol]
                    i = eol + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                        break
                    body.append(line)
                if run:
                    _parse("\n".join(body), segments)
            heredocs = []
            continue
        if c in SEPARATORS:
            end_segment()
            i += 1
            continue
        if c.isspace():
            end_word()
            i += 1
            continue
        word.append(c)
        started = True
        i += 1
    end_segment()
