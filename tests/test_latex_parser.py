"""Unit tests for parse_latex_resume (moved from the module's former __main__ self-test)."""
from __future__ import annotations

from app.parsers.latex_parser import parse_latex_resume


def test_itemize_bullets_and_empty_education():
    sample = r"""
\section{Experience}
\begin{itemize}
\item Built a pipeline that improved speed by 25\%
\item Deployed a dashboard for 300 users
\end{itemize}

\section{Education}
\textbf{B.Tech}
"""
    parsed = parse_latex_resume(sample)
    assert parsed["Experience"]["bullets"] == [
        r"Built a pipeline that improved speed by 25\%",
        "Deployed a dashboard for 300 users",
    ]
    assert parsed["Education"]["bullets"] == []


def test_resume_item_macro_bullets():
    sample = r"""
\section{Experience}
\resumeItemListStart
  \resumeItem{Shipped a feature used by 1000 users}
  \resumeItem{Reduced latency by 40\%}
\resumeItemListEnd
"""
    parsed = parse_latex_resume(sample)
    assert parsed["Experience"]["bullets"] == [
        "Shipped a feature used by 1000 users",
        r"Reduced latency by 40\%",
    ]


def test_empty_input_returns_empty_dict():
    assert parse_latex_resume("") == {}
    assert parse_latex_resume("   ") == {}
