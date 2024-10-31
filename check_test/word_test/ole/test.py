import struct

# 提取 .bin 文件中的嵌入对象
def extract_bin(bin_file_path, output_file_path):
    with open(bin_file_path, 'rb') as bin_file:
        data = bin_file.read()

        # 忽略前6个字节（4字节长度 + 2字节标志）
        data = data[6:]

        # 提取文件名，以\0结尾
        filename_end = data.find(b'\x00')
        if filename_end == -1:
            print("无法找到文件名的结尾，数据格式可能有问题")
            return
        
        # 尝试使用 'latin-1' 解码文件名
        try:
            filename = data[:filename_end].decode('utf-8')
        except UnicodeDecodeError:
            print("UTF-8 解码失败，尝试使用 'latin-1'")
            filename = data[:filename_end].decode('latin-1')

        print(f"嵌入文件名：{filename}")
        
        # 提取剩余部分作为文件内容
        file_content = data[filename_end + 1:]

        # 将嵌入文件保存
        with open(output_file_path, 'wb') as f:
            f.write(file_content)
        print(f"文件成功提取并保存为: {output_file_path}")

# 将嵌入的文件重新打包回 .bin 文件
def pack_bin(input_file_path, bin_output_path, original_file_name="restored_file.html"):
    # 读取要嵌入的文件内容
    with open(input_file_path, 'rb') as f:
        file_content = f.read()

    # OLE10Native 格式：先写入文件名 + \0, 然后写入文件内容
    ole_data = struct.pack("<I", len(file_content) + 2 + len(original_file_name))  # 4字节长度（包括文件名长度+内容长度）
    ole_data += b"\x02\x00"  # 2字节标志
    ole_data += original_file_name.encode('utf-8') + b"\x00"  # 文件名以 \x00 结尾
    ole_data += file_content  # 文件内容

    # 将组合后的内容写入 .bin 文件
    with open(bin_output_path, 'wb') as output_file:
        output_file.write(ole_data)

    print(f"成功将文件打包为 {bin_output_path}")

# 示例使用
base_path = r'C:\Users\EDY\Desktop\巡检记录\test\word_test\ole'

# 提取 bin 文件中的嵌入对象
extract_bin(base_path + r'\oleObject1.bin', base_path + r'\extracted_file.html')

# 重新将嵌入对象打包回 bin 文件
pack_bin(base_path + r'\extracted_file.html', base_path + r'\repacked_oleObject1.bin')
