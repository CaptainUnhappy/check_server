import olefile
import re

def extract_bin_with_metadata(bin_file_path, output_html_path, output_metadata_path):
    # 打开 .bin 文件作为 OLE 文件
    ole = olefile.OleFileIO(bin_file_path)
    
    # 列出所有流 (streams)
    ole_dirs = ole.listdir()
    print("OLE 文件中包含的流:", ole_dirs)

    # 提取 'Ole10Native' 流中的内容
    if ole.exists('\x01Ole10Native'):
        with ole.openstream('\x01Ole10Native') as stream:
            content = stream.read()

            # 转换为字符串处理
            content_str = content.decode(errors='ignore')  # 解码为字符串，忽略乱码

            # 使用正则表达式提取从 <html> 开始到 </html> 结束的部分
            match = re.search(r'(<html.*?>.*?</html>)', content_str, re.DOTALL)

            if match:
                html_content = match.group(1)

                # 保存提取的 HTML 内容到文件
                with open(output_html_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(html_content)
                print(f"成功提取 HTML 内容为 {output_html_path}")

                # 保存 HTML 前后的元数据（即被去除的部分）
                metadata_before_html = content_str[:match.start()]
                metadata_after_html = content_str[match.end():]
                
                with open(output_metadata_path, 'w', encoding='utf-8') as metadata_file:
                    metadata_file.write(metadata_before_html + '\n---元数据结束---\n' + metadata_after_html)
                print(f"成功提取并保存元数据为 {output_metadata_path}")
            else:
                print("未能找到 HTML 内容，可能文件格式不对或提取有误")
    else:
        print("无法找到 'Ole10Native' 流，检查嵌入对象是否正确")
    
    ole.close()

# 示例：将 oleObject1.bin 还原为清理后的 HTML 文件，并保存元数据
base_path = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\ole'
extract_bin_with_metadata(base_path + r'\oleObject1.bin', 
                          base_path + r'\restored.html', 
                          base_path + r'\ole_metadata.txt')
