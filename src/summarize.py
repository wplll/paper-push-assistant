"""Generate paper summaries using LLM."""

import json
import logging

from src.llm.deepseek_provider import DeepSeekProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一名多模态目标跟踪、视觉语言模型、计算机视觉方向的论文阅读助手。"
    "请根据论文标题、摘要、年份、方向、论文链接、代码链接生成中文论文解读。"
    "要求具体、严谨，不要编造实验结果。如果摘要中没有提供实验细节，必须说明\"摘要中未提供\"。"
)
USER_PROMPT_TEMPLATE = """请对以下论文进行详细解读分析，并以JSON格式输出。

论文信息：
- 标题：{title}
- 年份：{year}
- 方向/类别：{category}
- 论文链接：{paper_url}
- 代码链接：{code_url}
- 摘要：{abstract}

请严格按照以下JSON格式输出（不要输出其他内容）：
{{
  "title_cn": "中文标题或标题意译",
  "one_sentence_summary": "一句话总结论文贡献",
  "research_problem": "这篇论文要解决的核心问题",
  "method_overview": "方法概述，重点解释模型结构、模态融合、时序建模或训练策略",
  "key_innovations": ["创新点1", "创新点2", "创新点3"],
  "experiments": "实验设置、数据集和对比方法；如果输入没有提供，请说明未提供",
  "limitations": ["可能局限1", "可能局限2"],
  "relevance_to_user": "说明这篇论文对多模态目标跟踪、视觉跟踪模型改进、时序图像分析或多模态特征融合的启发",
  "reading_priority": "高/中/低",
  "why_read": "为什么值得或不值得优先阅读"
}}
"""

# Fallback summary when LLM fails
FALLBACK_SUMMARY = {
    "title_cn": "",
    "one_sentence_summary": "LLM 调用失败，无法生成摘要",
    "research_problem": "信息不足",
    "method_overview": "信息不足",
    "key_innovations": ["信息不足"],
    "experiments": "信息不足",
    "limitations": ["信息不足"],
    "relevance_to_user": "信息不足",
    "reading_priority": "中",
    "why_read": "LLM 调用失败，建议手动查看原文",
}


def _format_user_prompt(paper: dict) -> str:
    """Format the user prompt for a specific paper."""
    return USER_PROMPT_TEMPLATE.format(
        title=paper.get("title", "N/A"),
        year=paper.get("year", "N/A"),
        category=paper.get("category", paper.get("source_section", "N/A")),
        paper_url=paper.get("paper_url", "N/A"),
        code_url=paper.get("code_url", "无"),
        abstract=paper.get("abstract", "摘要中未提供"),
    )


def summarize_paper(paper: dict, provider: DeepSeekProvider | None = None) -> dict:
    """Generate a summary for a single paper.

    Args:
        paper: Paper dict with metadata.
        provider: LLM provider instance. Creates a default one if None.

    Returns:
        Dict with summary fields.
    """
    if provider is None:
        provider = DeepSeekProvider()

    user_prompt = _format_user_prompt(paper)

    try:
        result = provider.chat_json(SYSTEM_PROMPT, user_prompt)
        if result.get("parse_error"):
            logger.warning("LLM returned non-JSON for paper: %s", paper.get("title", ""))
            fallback = FALLBACK_SUMMARY.copy()
            fallback["raw_text"] = result.get("raw_text", "")
            return fallback
        return result
    except Exception as e:
        logger.error("Failed to summarize paper '%s': %s", paper.get("title", ""), e)
        return FALLBACK_SUMMARY.copy()


def summarize_papers(papers: list[dict], provider: DeepSeekProvider | None = None) -> list[dict]:
    """Generate summaries for a list of papers.

    Args:
        papers: List of paper dicts.
        provider: LLM provider instance.

    Returns:
        Same list with 'summary' field added to each paper dict.
    """
    if provider is None:
        provider = DeepSeekProvider()

    for i, paper in enumerate(papers):
        try:
            logger.info("Summarizing paper %d/%d: %s", i + 1, len(papers), paper.get("title", "")[:60])
            summary = summarize_paper(paper, provider)
            paper["summary"] = summary
        except Exception as e:
            logger.error("Error summarizing paper %d: %s", i, e)
            paper["summary"] = FALLBACK_SUMMARY.copy()

    return papers
