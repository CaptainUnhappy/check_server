
import zipfile
import os

# .docx文件路径
docx_file = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\绍兴文理学院运维巡检记录-20241010.docx'

# 解压到的目录
output_dir = r'word_test\unzipped_docx'

# 检查解压目录是否存在，不存在则创建
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 使用zipfile解压docx文件
with zipfile.ZipFile(docx_file, 'r') as zip_ref:
    zip_ref.extractall(output_dir)

print(f'.docx文件已成功解压到 {output_dir}')
