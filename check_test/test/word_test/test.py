#filename为相关文件列表，filename[0]就是需要处理的主word文件，filename[1]-[12]是12个需要插入的附件
import random
import string
import os,zipfile,shutil       #需要用到的包
azip = zipfile.ZipFile(filename[0])          #以压缩格式打开word文件
tempdir=''
while True:
    tempdir= ''.join(random.sample(string.ascii_letters + string.digits, 8))   #生行8位临时文件夹名
    if not os.path.exists(tempdir):
        break
os.mkdir(tempdir)                  #创建临时目录
os.chdir(tempdir)                   #转到临时目录
azip.extractall()                     #解压word文件到临时文件夹
azip.close()                           #关闭word文档，否则后面重新压缩会报错
#把正确文件拷贝覆盖模版文件的空附件
try:
    shutil.copy(filename[1],'word\\embeddings\\Microsoft_Excel____.xlsx')
    shutil.copy(filename[2],'word\\embeddings\\Microsoft_Excel____1.xlsx')
    shutil.copy(filename[3],'word\\embeddings\\Microsoft_Excel____2.xlsx')
    shutil.copy(filename[4],'word\\embeddings\\Microsoft_Excel____3.xlsx')
    shutil.copy(filename[5],'word\\embeddings\\Microsoft_Excel____4.xlsx')
    shutil.copy(filename[6],'word\\embeddings\\Microsoft_Word___.docx')
    shutil.copy(filename[7],'word\\embeddings\\Microsoft_Word___5.docx')
    shutil.copy(filename[8],'word\\embeddings\\Microsoft_Word___6.docx')
    shutil.copy(filename[9],'word\\embeddings\\Microsoft_Word___7.docx')
    shutil.copy(filename[10],'word\\embeddings\\Microsoft_Word___8.docx')
    shutil.copy(filename[11],'word\\embeddings\\Microsoft_Word___9.docx')
    shutil.copy(filename[12],'word\\embeddings\\Microsoft_Word___10.docx')
    azip = zipfile.ZipFile(filename[0], 'w')    #以压缩格式新建word文档
    for i in os.walk('.'):                             #使用os.walk遍历整个目录及子目录，保证原有的目录结构不变
        for j in i[2]:
            azip.write(os.path.join(i[0],j), compress_type=zipfile.ZIP_DEFLATED)     #将文件逐个打包到word文档中，压缩格式指定为ZIP_DEFLATED
    azip.close()                                       #关闭文件
    os.chdir('..')
    shutil.rmtree(tempdir,ignore_errors=True)    #删除临时文件夹
except:
    pass