import olefile
import re

# OLE 文件路径
file_path = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\unzipped_docx\word\embeddings\oleObject1.bin'  # 修改为实际文件路径

# 尝试打开并读取 OLE 文件中的 Ole10Native 流
try:
    ole = olefile.OleFileIO(file_path)
    if ole.exists(['\x01Ole10Native']):
        with ole.openstream(['\x01Ole10Native']) as stream:
            data = stream.read()
            
            # 尝试用 GBK 编码解码数据（或其他编码）
            try:
                decoded_data = data.decode('gbk')
            except UnicodeDecodeError:
                decoded_data = data.decode('utf-8', errors='ignore')  # 尝试 UTF-8

            # 使用正则表达式找到 HTML 部分
            html_match = re.search(r"(<html.*</html>)", decoded_data, re.DOTALL)
            if html_match:
                html_content = html_match.group(1)
            else:
                html_content = decoded_data  # 如果没有匹配到，保留原内容
            
            # 保存处理后的 HTML 内容
            output_html_path = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\1.html'  # 修改为输出路径
            with open(output_html_path, "w", encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Processed content and saved as {output_html_path}")
    else:
        print("No 'Ole10Native' stream found in the OLE file.")
    
    ole.close()
except Exception as e:
    print(f"Error processing the OLE file: {str(e)}")
