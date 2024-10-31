def pack_html_with_metadata(html_file_path, metadata_file_path, output_bin_path):
    # 读取 HTML 文件内容
    with open(html_file_path, 'rb') as html_file:
        html_content = html_file.read()

    # 读取元数据内容
    with open(metadata_file_path, 'r', encoding='utf-8') as metadata_file:
        metadata_content = metadata_file.read()

    # 分割元数据为前后部分
    metadata_parts = metadata_content.split('---元数据结束---')
    if len(metadata_parts) != 2:
        print("元数据格式不正确，无法找到分割标记")
        return
    
    metadata_before_html = metadata_parts[0].encode('utf-8')
    metadata_after_html = metadata_parts[1].encode('utf-8')

    # 组合元数据和 HTML 内容
    full_content = metadata_before_html + html_content + metadata_after_html

    # 将组合后的内容写入 .bin 文件
    with open(output_bin_path, 'wb') as output_file:
        output_file.write(full_content)

    print(f"成功将 {html_file_path} 和元数据打包为 {output_bin_path}")

# 示例：将 HTML 和元数据打包为 .bin 文件
base_path = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\ole'
pack_html_with_metadata(base_path + r'\restored.html', 
                               base_path + r'\ole_metadata.txt', 
                               base_path + r'\repacked.bin')
