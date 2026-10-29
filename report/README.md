# Report

The project report, written in LaTeX. It uses the
[AAU report template](https://github.com/jkjaer/aauLatexTemplates) (BSD license, see `LICENSE-template`).

## Where things go

```
report/
  chapters/        the report itself, one or more files per chapter
    1.0-introduction.tex
    2.0-prototype.tex, 2.1-imaging-tests.tex, 2.2-control-software.tex
    3.0-conclusion.tex
  appendices/      appendices, A.0-..., B.0-...
  frontmatter/     front page, title pages, colophon, preface
  figures/         images. Write \includegraphics{name}, no folder needed
  references.bib   all references
  setup/           packages and macros (rarely touched)
  main.tex         puts it all together (you do not need to edit it)
```

## Adding text

Every `.tex` file in `chapters/` is included automatically, sorted by the number
at the start of its name. Nobody has to edit `main.tex`, so two people can add files
at the same time without conflicts.

- `1.0-introduction.tex` starts a chapter with `\chapter{Introduction}`.
- `1.1-background.tex` continues it, e.g. with `\section{Background}`.
- `2.0-design.tex` starts the next chapter.
- Need something in between? Use `1.5-...`, or renumber. `1.10` comes after `1.9`.
- Appendices work the same way in `appendices/` with letters: `A.0-...`, `A.1-...`, `B.0-...`.

Rules for file names: start with the number, then `-`, no spaces.
`1.0-introduction.tex` works, `1.0 introduction.tex` does not.

Tip: split a chapter into several files when two people work on it at once.
Each person edits their own file, so there are fewer merge conflicts.

## Placeholders

Red text in the PDF is unfinished. Search the `.tex` files for:

- `\fillin{...}`: something to write or decide now.
- `\future{...}`: something we can only do later (needs new hardware, data or tests).

Both are defined in `setup/macros.tex`.

## Workflow

`main` is protected. All changes go through a pull request.

1. Make a branch: `git switch -c intro-text`
2. Write, commit, push.
3. Open a pull request. GitHub builds the PDF and posts a link to it as a comment.
   Each new push updates the link. Click it to open the PDF.
   The comment also links a second PDF with the changes marked, like the GitHub diff:
   added text is blue and underlined, removed text is red and struck through.
4. The other person reads it (the "changes marked" PDF is quickest), then merge.

If the build fails, the check turns red. Open the check and read the log
(look for the first line with `error`), or download the `latex-log` artifact.

## Sending the report to the supervisor

The branch `supervisor-reviewed` holds the last version the supervisor has read and
given feedback on. Do not push to it directly. It only moves forward through a pull request.

Every week or two:

1. Make a review branch from `main`, named after the date you send it:
   `git switch main && git pull && git switch -c review/2026-11-04 && git push -u origin review/2026-11-04`
   Do not push more to this branch. It is a snapshot of exactly what the supervisor gets.
2. On GitHub, open a pull request from `review/2026-11-04` into `supervisor-reviewed`
   (change the *base* dropdown from `main`). Call it "Supervisor review 2026-11-04".
3. CI posts two PDFs on the pull request:
   - the full report, and
   - the report with **changes since the last review** marked (blue = added, red = removed).
4. Email both PDFs to the supervisor.
5. The supervisor comments in the way that suits them: notes in the PDF (any PDF reader),
   an email, or comments on the pull request on GitHub.
6. Turn the feedback into issues, or fix it straight away in normal pull requests to `main`.
   Write a short summary of the feedback in the review pull request so it is easy to find later.
7. When the feedback is in, merge the review pull request with **Create a merge commit**
   (not squash or rebase, or the next review pull request will show old changes again).
   Now `supervisor-reviewed` is the version they have read.

Keep the `review/...` branches. They show what was sent on which date. To see what changed
between two reviews on your own computer: `cd report && ./diff.sh review/2026-11-04`.

## Building on your own computer (optional)

You need a TeX distribution (MacTeX, TeX Live or MiKTeX). With Nix, `nix develop` in the
repo root (or `direnv allow` once) gives you one, together with Python for the device software.
Then:

```
cd report
latexmk          # builds main.pdf
latexmk -pvc     # rebuilds every time you save
latexmk -c       # removes temporary files
./diff.sh        # diff.pdf: changes since origin/main marked
./diff.sh HEAD~3 # or since any other git version
```

New files in `chapters/` are picked up the next time you run `latexmk`.
VS Code with the LaTeX Workshop extension also works; it uses `latexmk`.
