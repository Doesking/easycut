#!/usr/bin/env python3
"""
更新web_server.py中的HTML_PAGE为新的UI设计
"""

import re

# 读取新的UI设计文件
with open('ui_redesign/index_v3.html', 'r', encoding='utf-8') as f:
    new_ui_content = f.read()

# 读取web_server.py文件
with open('web_server.py', 'r', encoding='utf-8') as f:
    server_content = f.read()

# 找到HTML_PAGE的开始和结束位置
# HTML_PAGE = r"""..."""
pattern = r'HTML_PAGE = r""".*?"""'
match = re.search(pattern, server_content, re.DOTALL)

if match:
    start_pos = match.start()
    end_pos = match.end()
    
    # 构建新的HTML_PAGE
    new_html_page = f'HTML_PAGE = r"""{new_ui_content}"""'
    
    # 替换内容
    new_server_content = server_content[:start_pos] + new_html_page + server_content[end_pos:]
    
    # 写入新的web_server.py文件
    with open('web_server.py', 'w', encoding='utf-8') as f:
        f.write(new_server_content)
    
    print("✅ UI更新成功！")
    print(f"   原始HTML_PAGE: {end_pos - start_pos} 字符")
    print(f"   新HTML_PAGE: {len(new_html_page)} 字符")
else:
    print("❌ 未找到HTML_PAGE变量")
    print("请检查web_server.py文件格式")