"""Render paper summaries as HTML email content."""

import html
from datetime import datetime, timezone


def _escape(text: str) -> str:
    """HTML-escape text safely."""
    return html.escape(str(text)) if text else ""


def _render_paper_card(paper: dict, index: int) -> str:
    """Render a single paper as an HTML card."""
    summary = paper.get("summary", {})
    title = _escape(paper.get("title", "N/A"))
    title_cn = _escape(summary.get("title_cn", ""))
    year = paper.get("year", "N/A")
    category = _escape(paper.get("category", paper.get("source_section", "")))
    paper_url = _escape(paper.get("paper_url", ""))
    code_url = _escape(paper.get("code_url", ""))
    abstract = _escape(paper.get("abstract", ""))

    one_sentence = _escape(summary.get("one_sentence_summary", ""))
    research_problem = _escape(summary.get("research_problem", ""))
    method_overview = _escape(summary.get("method_overview", ""))
    experiments = _escape(summary.get("experiments", ""))
    relevance = _escape(summary.get("relevance_to_user", ""))
    reading_priority = summary.get("reading_priority", "中")
    why_read = _escape(summary.get("why_read", ""))

    key_innovations = summary.get("key_innovations", [])
    innovations_html = "".join(f"<li>{_escape(k)}</li>" for k in key_innovations)

    limitations = summary.get("limitations", [])
    limitations_html = "".join(f"<li>{_escape(l)}</li>" for l in limitations)

    priority_color = {"高": "#e74c3c", "中": "#f39c12", "低": "#27ae60"}.get(reading_priority, "#7f8c8d")

    links_html = ""
    if paper_url:
        links_html += f'<a href="{paper_url}" style="color:#3498db;margin-right:16px;">📄 Paper</a>'
    if code_url:
        links_html += f'<a href="{code_url}" style="color:#2ecc71;">💻 Code</a>'

    return f"""
    <div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:20px;margin-bottom:20px;">
      <div style="margin-bottom:12px;">
        <span style="background:{priority_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">
          {_escape(reading_priority)}
        </span>
        <span style="color:#999;font-size:13px;margin-left:8px;">#{index}</span>
      </div>
      <h3 style="margin:0 0 4px;color:#2c3e50;">{title}</h3>
      {"<p style='margin:0 0 8px;color:#555;font-style:italic;'>" + title_cn + "</p>" if title_cn else ""}
      <p style="margin:0 0 12px;color:#777;font-size:13px;">
        {year} &nbsp;|&nbsp; {category if category else "N/A"}
      </p>
      <div style="margin-bottom:12px;">{links_html}</div>

      <div style="background:#f8f9fa;padding:14px;border-radius:6px;margin-bottom:12px;">
        <p style="margin:0 0 8px;"><strong>一句话总结：</strong>{one_sentence}</p>
        <p style="margin:0 0 8px;"><strong>核心问题：</strong>{research_problem}</p>
        <p style="margin:0;"><strong>方法概述：</strong>{method_overview}</p>
      </div>

      {"<div style='margin-bottom:12px;'><strong>创新点：</strong><ul style='margin:4px 0 0;padding-left:20px;'>" + innovations_html + "</ul></div>" if innovations_html else ""}

      <p style="margin:0 0 8px;"><strong>实验与证据：</strong>{experiments}</p>

      {"<div style='margin-bottom:12px;'><strong>可能局限：</strong><ul style='margin:4px 0 0;padding-left:20px;'>" + limitations_html + "</ul></div>" if limitations_html else ""}

      <p style="margin:0 0 8px;"><strong>对我的启发：</strong>{relevance}</p>
      <p style="margin:0;"><strong>推荐阅读理由：</strong>{why_read}</p>

      {"<div style='margin-top:12px;padding:10px;background:#f0f0f0;border-radius:4px;font-size:12px;color:#666;'><strong>摘要原文：</strong><br>" + abstract + "</div>" if abstract and abstract != "摘要中未提供" else ""}
    </div>
    """


def render_email_html(
    papers: list[dict],
    repo_url: str = "https://github.com/983632847/Awesome-Multimodal-Object-Tracking",
    total_sent: int = 0,
) -> str:
    """Render the full email HTML.

    Args:
        papers: List of paper dicts with 'summary' field.
        repo_url: Source repository URL.
        total_sent: Total number of papers sent so far.

    Returns:
        Complete HTML email string.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    paper_count = len(papers)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cards_html = ""
    for i, paper in enumerate(papers, 1):
        cards_html += _render_paper_card(paper, i)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#333;">
  <div style="max-width:700px;margin:0 auto;">
    <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:24px;border-radius:8px 8px 0 0;text-align:center;">
      <h1 style="margin:0;font-size:22px;">📚 多模态目标跟踪论文日报</h1>
      <p style="margin:8px 0 0;opacity:0.9;">{date_str} | 今日 {paper_count} 篇论文</p>
    </div>

    <div style="background:#fafafa;padding:20px;border:1px solid #e0e0e0;border-top:none;">
      {cards_html}

      <div style="border-top:1px solid #e0e0e0;padding-top:16px;margin-top:20px;color:#999;font-size:12px;">
        <p>📦 来源仓库：<a href="{repo_url}" style="color:#3498db;">Awesome-Multimodal-Object-Tracking</a></p>
        <p>🕐 运行时间：{now}</p>
        <p>📊 已推送论文总数：{total_sent}</p>
        <p style="margin-top:12px;color:#bbb;">由 MMOT Paper Pusher 自动生成</p>
      </div>
    </div>
  </div>
</body>
</html>"""


def render_empty_email_html(reason: str = "今日暂无新论文") -> str:
    """Render an email for when there are no new papers."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#333;">
  <div style="max-width:600px;margin:0 auto;">
    <div style="background:#f39c12;color:#fff;padding:24px;border-radius:8px 8px 0 0;text-align:center;">
      <h1 style="margin:0;font-size:20px;">📚 多模态目标跟踪论文日报</h1>
      <p style="margin:8px 0 0;opacity:0.9;">{date_str}</p>
    </div>
    <div style="background:#fff;padding:30px;border:1px solid #e0e0e0;border-top:none;text-align:center;">
      <p style="font-size:16px;color:#666;">{reason}</p>
      <p style="color:#999;font-size:13px;">所有已收录论文均已推送完毕，等待源仓库更新。</p>
    </div>
    <div style="text-align:center;padding:12px;color:#bbb;font-size:11px;">
      🕐 {now} | 由 MMOT Paper Pusher 自动生成
    </div>
  </div>
</body>
</html>"""
