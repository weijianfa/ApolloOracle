"""
长消息分段发送工具
Telegram消息最大4096字符，需要智能分段
"""
import re
from typing import List
from bot.utils.logger import logger


def split_message(text: str, max_length: int = 4000) -> List[str]:
    """
    智能分段消息
    
    Args:
        text: 原始文本
        max_length: 每段最大长度（默认4000，留出缓冲）
        
    Returns:
        分段后的消息列表
    """
    if len(text) <= max_length:
        return [text]
    
    segments = []
    current_segment = ""
    
    # 按段落分割（双换行）
    paragraphs = text.split("\n\n")
    
    for paragraph in paragraphs:
        # 如果当前段落本身就很长，需要进一步分割
        if len(paragraph) > max_length:
            # 先保存当前段（如果有内容）
            if current_segment:
                segments.append(current_segment.strip())
                current_segment = ""
            
            # 按句子分割长段落
            sentences = paragraph.split("。") if "。" in paragraph else paragraph.split(".")
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # 如果加上这个句子会超过长度，先保存当前段
                if current_segment and len(current_segment) + len(sentence) + 2 > max_length:
                    segments.append(current_segment.strip())
                    current_segment = ""
                
                # 如果单个句子就超过长度，按字符强制分割
                if len(sentence) > max_length:
                    if current_segment:
                        segments.append(current_segment.strip())
                        current_segment = ""
                    
                    # 强制分割
                    for i in range(0, len(sentence), max_length):
                        segments.append(sentence[i:i + max_length])
                else:
                    # 添加到当前段
                    if current_segment:
                        current_segment += "\n\n" + sentence
                    else:
                        current_segment = sentence
        else:
            # 检查加上这个段落是否会超过长度
            if current_segment and len(current_segment) + len(paragraph) + 2 > max_length:
                segments.append(current_segment.strip())
                current_segment = paragraph
            else:
                if current_segment:
                    current_segment += "\n\n" + paragraph
                else:
                    current_segment = paragraph
    
    # 添加最后一段
    if current_segment:
        segments.append(current_segment.strip())
    
    return segments


def format_markdown(text: str) -> str:
    """
    格式化Markdown文本为Telegram支持的格式，并进行排版优化
    
    将AI生成的Markdown格式转换为Telegram Markdown格式，并优化排版：
    - 转义特殊字符（避免格式错误）
    - 优化标题层级和格式
    - 统一列表格式
    - 优化段落间距和视觉节奏
    - 减少不必要的分隔线
    - 突出重要信息
    
    Args:
        text: 原始Markdown文本
        
    Returns:
        格式化后的Telegram Markdown文本
    """
    if not text:
        return text
    
    # 先保存代码块，避免被后续处理影响
    code_blocks = []
    code_block_pattern = r'```[\s\S]*?```'
    
    def replace_code_block(match):
        placeholder = f"PLACEHOLDERCODEBLOCK{len(code_blocks)}PLACEHOLDER"
        code_blocks.append(match.group(0))
        return placeholder
    
    # 临时替换代码块
    text = re.sub(code_block_pattern, replace_code_block, text)
    
    # 保存行内代码，避免被后续处理影响
    inline_codes = []
    inline_code_pattern = r'`[^`]+`'
    
    def replace_inline_code(match):
        placeholder = f"PLACEHOLDERINLINECODE{len(inline_codes)}PLACEHOLDER"
        inline_codes.append(match.group(0))
        return placeholder
    
    # 临时替换行内代码
    text = re.sub(inline_code_pattern, replace_inline_code, text)
    
    # 移除所有分隔线
    text = re.sub(r'━+', '', text)  # 移除所有分隔线字符
    text = re.sub(r'[-*]{3,}', '', text)  # 移除其他类型的分隔线（--- 或 ***）
    
    # 处理标题层级（优化视觉层次，移除Markdown标记）
    text = re.sub(r'^#\s+(.+)$', r'\n\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'\n\1\n', text, flags=re.MULTILINE)
    text = re.sub(r'^#{3,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    
    # 处理粗体（**text** 或 __text__ -> 去除Markdown标记）
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # 优化列表格式（统一使用 •，并优化间距）
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    prev_empty = False
    
    for i, line in enumerate(lines):
        is_empty = not line.strip()
        
        # 检查是否是列表项
        list_match = re.match(r'^[\s]*[-*•]\s+(.+)$', line)
        numbered_match = re.match(r'^[\s]*\d+[\.、]\s+(.+)$', line)
        
        if list_match or numbered_match:
            content = list_match.group(1) if list_match else numbered_match.group(1)
            
            # 如果之前不是列表，添加一个空行（除非前面已经是空行）
            if not in_list and not prev_empty:
                formatted_lines.append('')
            
            # 统一使用 • 符号
            formatted_lines.append(f"  • {content}")
            in_list = True
            prev_empty = False
        else:
            # 如果之前是列表，且当前行不是空行，添加一个空行
            if in_list and not is_empty:
                formatted_lines.append('')
                in_list = False
            
            formatted_lines.append(line)
            prev_empty = is_empty
    
    text = '\n'.join(formatted_lines)
    
    # 处理引用块（> 开头）-> 使用中文引号包裹
    text = re.sub(r'^>\s+(.+)$', r'「\1」', text, flags=re.MULTILINE)
    
    # 优化段落间距：确保段落之间有适当的空行
    # 移除连续3个以上的空行
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # 优化emoji和文本之间的间距
    # 确保emoji后有一个空格（如果紧跟着文字）
    text = re.sub(r'([🎴🃏🌙🕊️🌉💫🔥🌄🧭🌊🌠✨✦]+)([^\s\n])', r'\1 \2', text)
    
    # 转义Telegram Markdown特殊字符（在非代码块和格式标记中）
    # Telegram Markdown特殊字符：_ * [ ] ( ) ~ ` > # + - = | { } . !
    
    # 第一步：保护已经正确格式化的Markdown标记
    # 使用不包含特殊字符的占位符，避免被后续转义影响
    # 保护粗体标记 *text*（确保是成对的 *）
    bold_pattern = r'\*([^*\n]+?)\*'
    bold_matches = []
    def replace_bold(match):
        placeholder = f"PLACEHOLDERBOLD{len(bold_matches)}PLACEHOLDER"
        bold_matches.append(match.group(0))
        return placeholder
    
    text = re.sub(bold_pattern, replace_bold, text)
    
    # 保护斜体标记 _text_（确保是成对的 _，且不是粗体的一部分）
    italic_pattern = r'(?<!\*)_([^_\n]+?)_(?!\*)'
    italic_matches = []
    def replace_italic(match):
        placeholder = f"PLACEHOLDERITALIC{len(italic_matches)}PLACEHOLDER"
        italic_matches.append(match.group(0))
        return placeholder
    
    text = re.sub(italic_pattern, replace_italic, text)
    
    # 保护链接格式
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    links = []
    def replace_link(match):
        placeholder = f"PLACEHOLDERLINK{len(links)}PLACEHOLDER"
        links.append(match.group(0))
        return placeholder
    
    text = re.sub(link_pattern, replace_link, text)
    
    # 第二步：恢复被保护的格式标记
    # 恢复粗体（恢复时不需要转义，因为它们已经被保护）
    for i, bold in enumerate(bold_matches):
        text = text.replace(f"PLACEHOLDERBOLD{i}PLACEHOLDER", bold)
    
    # 恢复斜体
    for i, italic in enumerate(italic_matches):
        text = text.replace(f"PLACEHOLDERITALIC{i}PLACEHOLDER", italic)
    
    # 恢复链接
    for i, link in enumerate(links):
        text = text.replace(f"PLACEHOLDERLINK{i}PLACEHOLDER", link)
    
    # 恢复行内代码
    for i, inline_code in enumerate(inline_codes):
        text = text.replace(f"PLACEHOLDERINLINECODE{i}PLACEHOLDER", inline_code)
    
    # 恢复代码块
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"PLACEHOLDERCODEBLOCK{i}PLACEHOLDER", code_block)
    
    # 如果仍有未恢复的占位符，使用正则兜底替换，防止残留
    def restore_remaining_placeholders(pattern_prefix: str, values: list, content: str) -> str:
        pattern = re.compile(rf"{pattern_prefix}(\d+)PLACEHOLDER")
        
        def replacement(match):
            idx = int(match.group(1))
            if 0 <= idx < len(values):
                return values[idx]
            # 如果索引超出范围，则返回空字符串避免占位符泄漏
            logger.warning(
                f"Placeholder index {idx} out of range for prefix {pattern_prefix}"
            )
            return ""
        
        return pattern.sub(replacement, content)
    
    text = restore_remaining_placeholders("PLACEHOLDERBOLD", bold_matches, text)
    text = restore_remaining_placeholders("PLACEHOLDERITALIC", italic_matches, text)
    text = restore_remaining_placeholders("PLACEHOLDERLINK", links, text)
    text = restore_remaining_placeholders("PLACEHOLDERINLINECODE", inline_codes, text)
    text = restore_remaining_placeholders("PLACEHOLDERCODEBLOCK", code_blocks, text)
    
    # 第三步：去除残余Markdown强调标记与转义字符
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    markdown_specials = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for ch in markdown_specials:
        text = text.replace(f"\\{ch}", ch)
    
    # 最终清理：统一空行数量
    # 段落之间：1个空行
    # 章节之间：2个空行
    # 移除开头和结尾的多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)  # 最多2个连续空行
    text = text.strip()
    
    return text

